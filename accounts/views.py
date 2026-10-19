from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.db import transaction
import logging

from .forms import UserRegistrationForm, UserProfileForm, CustomAuthenticationForm

logger = logging.getLogger(__name__)


from django.utils.decorators import method_decorator


def get_role_landing(user):
    """Module landing page per account type.

    - Admin   -> Django admin site (platform configuration)
    - Ranger  -> Forest/ranger dashboard (falls back to citizen module for now;
                dedicated ranger console will be built separately)
    - Citizen -> Sightings module
    """
    if not user.is_authenticated:
        return reverse('dashboard:home')
    profile = getattr(user, 'profile', None)
    if profile is None:
        return reverse('reports:list')
    if profile.is_admin:
        return reverse('accounts:admin_dashboard')
    if profile.is_ranger:
        return reverse('ranger:dashboard')
    if profile.is_authority_officer:
        # Authority module landing = Authority Map primary screen (/authority/map/)
        return reverse('dashboard:authority_map_alias')
    return reverse('reports:list')


@method_decorator(never_cache, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm
    # IMPORTANT: do NOT auto-redirect already-authenticated visitors.
    # The login page must always require fresh credentials so a second
    # browser tab can sign in as a different user (ranger/citizen/authority)
    # independently of the session in the first tab.
    redirect_authenticated_user = False

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(
                request,
                "You are already signed in as {}. To log in as a different "
                "user, use the Logout button first.".format(request.user.username))
            return redirect(get_role_landing(request.user))
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        messages.success(self.request, f"Welcome back, {user.username}! Signed in as {user.profile.get_role_display()}.")
        # Honour an explicit ?next= only when it is a safe internal URL.
        nxt = self.request.GET.get('next') or self.request.POST.get('next')
        from django.utils.http import url_has_allowed_host_and_scheme
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={self.request.get_host()}, require_secure=self.request.is_secure()):
            return nxt
        return get_role_landing(user)


@never_cache
def register_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_landing(request.user))

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            profile = user.profile
            if profile.is_citizen:
                login(request, user)
                messages.success(request, f"Account created successfully! You are signed in as {user.username} ({user.profile.get_role_display()}).")
                return redirect(get_role_landing(user))
            else:
                role_label = profile.get_role_display()
                messages.success(
                    request,
                    f"Your application for an official {role_label} account has been submitted for review. "
                    "A platform administrator will inspect your supporting document and credentials. "
                    "You will be able to sign in once your application is approved."
                )
                return redirect('accounts:login')
        else:
            messages.error(request, "Please correct the errors below and try again.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@never_cache
def logout_view(request):
    """Properly terminate the user's Django session."""
    if request.user.is_authenticated:
        logger.info(f"Logging out user: {request.user.username}")

    logout(request)

    # Flush the session to remove all session data
    if hasattr(request, 'session'):
        request.session.flush()
        logger.info("Session flushed successfully")

    return redirect('accounts:login')


@login_required
@never_cache
def profile_view(request):
    profile = request.user.profile
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    profile_form = UserProfileForm(instance=profile)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')

        if action == 'change_password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was changed successfully.")
                return redirect('accounts:profile')
            else:
                messages.error(request, "Failed to change password. Please correct the errors below.")
        else:
            profile_form = UserProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been updated.")
                return redirect('accounts:profile')
            else:
                messages.error(request, "Please correct the profile errors below.")

    return render(request, 'accounts/profile.html', {
        'form': profile_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile
    })


@login_required
@never_cache
def admin_provision_account_view(request):
    """Platform Admin Console: Provision official Authority Officer and Ranger accounts,
    review registration applications, inspect supporting documents, manage account status, and audit history."""
    # Enforce admin permission (superuser or admin role)
    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404
    from django.db.models import Q
    from django.utils import timezone
    from .forms import AdminAuthorityProvisionForm, AdminRangerProvisionForm, AdminAccountProvisionForm
    from .models import UserProfile, AccountApplication, Notification, AuditLog

    authority_form = AdminAuthorityProvisionForm()
    ranger_form = AdminRangerProvisionForm()
    form = AdminAccountProvisionForm()
    active_tab = request.GET.get('tab', 'applications').strip().lower()
    if active_tab not in ['applications', 'authority', 'ranger', 'roster']:
        active_tab = 'applications'

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        # --- 1. Approve Application ---
        if action == 'approve_application':
            app_id = request.POST.get('application_id') or request.POST.get('app_id')
            if not app_id:
                messages.error(request, "Missing application identifier.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            app = get_object_or_404(AccountApplication, pk=app_id)

            # Prevent duplicate approval or reviewing already finalized application
            if app.status == AccountApplication.STATUS_APPROVED:
                messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been approved.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")
            elif app.status == AccountApplication.STATUS_REJECTED:
                messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been rejected and cannot be directly approved.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            with transaction.atomic():
                app.status = AccountApplication.STATUS_APPROVED
                app.reviewed_by = request.user
                app.reviewed_at = timezone.now()
                app.save()

                target_user = app.user
                target_user.is_active = True
                target_user.save(update_fields=['is_active'])

                target_prof, _ = UserProfile.objects.get_or_create(user=target_user)
                # Assign role stored in the database application record, not arbitrary POST data
                target_prof.role = app.requested_role
                if app.organization:
                    target_prof.organization = app.organization
                if app.assigned_region:
                    target_prof.assigned_region = app.assigned_region
                if app.registered_location:
                    target_prof.registered_location = app.registered_location
                if app.latitude is not None:
                    target_prof.latitude = app.latitude
                if app.longitude is not None:
                    target_prof.longitude = app.longitude
                target_prof.account_status = UserProfile.ACCOUNT_ACTIVE
                target_prof.save()

                AuditLog.record(
                    actor=request.user,
                    action='APPLICATION_APPROVED',
                    target_type='AccountApplication',
                    target_id=app.pk,
                    target_repr=f"Application #{app.pk} ({target_user.username})",
                    details=f"Approved and activated {app.get_requested_role_display()} account."
                )
                Notification.send(
                    recipient=target_user,
                    actor=request.user,
                    title="Application Approved",
                    message=f"Your application for an official {app.get_requested_role_display()} account has been approved. You may now sign in.",
                    notification_type=Notification.TYPE_SUCCESS,
                    link=reverse('accounts:login')
                )

            messages.success(request, f"Application #{app.pk} ({target_user.username}) approved. Account is now active.")
            return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

        # --- 2. Reject Application ---
        elif action == 'reject_application':
            app_id = request.POST.get('application_id') or request.POST.get('app_id')
            if not app_id:
                messages.error(request, "Missing application identifier.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            app = get_object_or_404(AccountApplication, pk=app_id)

            if app.status in [AccountApplication.STATUS_APPROVED, AccountApplication.STATUS_REJECTED]:
                messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been reviewed ({app.get_status_display()}).")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, "A documented rejection reason is required to reject an application.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            with transaction.atomic():
                app.status = AccountApplication.STATUS_REJECTED
                app.rejection_reason = reason
                app.reviewed_by = request.user
                app.reviewed_at = timezone.now()
                app.save()

                target_user = app.user
                target_user.is_active = False
                target_user.save(update_fields=['is_active'])

                AuditLog.record(
                    actor=request.user,
                    action='APPLICATION_REJECTED',
                    target_type='AccountApplication',
                    target_id=app.pk,
                    target_repr=f"Application #{app.pk} ({target_user.username})",
                    details=f"Rejected. Rationale: {app.rejection_reason}"
                )
                Notification.send(
                    recipient=target_user,
                    actor=request.user,
                    title="Application Not Approved",
                    message=f"Your application for an official account was not approved. Reason: {app.rejection_reason}",
                    notification_type=Notification.TYPE_DANGER
                )

            messages.warning(request, f"Application #{app.pk} ({target_user.username}) rejected.")
            return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

        # --- 3. Request Additional Information ---
        elif action == 'request_info_application':
            app_id = request.POST.get('application_id') or request.POST.get('app_id')
            if not app_id:
                messages.error(request, "Missing application identifier.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            app = get_object_or_404(AccountApplication, pk=app_id)

            if app.status in [AccountApplication.STATUS_APPROVED, AccountApplication.STATUS_REJECTED]:
                messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been reviewed ({app.get_status_display()}).")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            notes = (request.POST.get('info_notes') or request.POST.get('rejection_reason') or '').strip()
            if not notes:
                messages.error(request, "Please specify the additional information required.")
                return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

            with transaction.atomic():
                app.status = AccountApplication.STATUS_NEEDS_INFO
                app.rejection_reason = notes
                app.reviewed_by = request.user
                app.reviewed_at = timezone.now()
                app.save()

                AuditLog.record(
                    actor=request.user,
                    action='APPLICATION_NEEDS_INFO',
                    target_type='AccountApplication',
                    target_id=app.pk,
                    target_repr=f"Application #{app.pk} ({app.user.username})",
                    details=f"Requested additional info: {notes}"
                )
                Notification.send(
                    recipient=app.user,
                    actor=request.user,
                    title="Additional Information Required",
                    message=f"Additional information requested for your application: {notes}",
                    notification_type=Notification.TYPE_WARNING
                )

            messages.info(request, f"Additional information requested for Application #{app.pk}.")
            return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

        # --- 4. Suspend or Ban Account ---
        elif action in ['suspend_account', 'ban_account']:
            target_user_id = request.POST.get('user_id')
            reason = request.POST.get('reason', '').strip()
            new_status = UserProfile.ACCOUNT_BANNED if action == 'ban_account' else UserProfile.ACCOUNT_SUSPENDED

            target_user = get_object_or_404(User, pk=target_user_id)
            if target_user.pk == request.user.pk:
                messages.error(request, "Security Policy Violation: You cannot suspend or ban your own account.")
                return redirect('accounts:admin_provision')

            # Prevent removing last active admin
            if target_user.is_superuser or (hasattr(target_user, 'profile') and target_user.profile.is_admin):
                active_admins_count = User.objects.filter(is_active=True).filter(
                    Q(is_superuser=True) | Q(profile__role=UserProfile.ROLE_ADMIN)
                ).filter(profile__account_status=UserProfile.ACCOUNT_ACTIVE).distinct().count()
                if active_admins_count <= 1:
                    messages.error(request, "Security Policy Violation: Cannot suspend or ban the last remaining active platform administrator.")
                    return redirect('accounts:admin_provision')

            target_prof = target_user.profile
            target_prof.account_status = new_status
            target_prof.suspension_reason = reason or ("Account suspended by administrator." if new_status == UserProfile.ACCOUNT_SUSPENDED else "Account banned by administrator.")
            target_prof.suspended_by = request.user
            target_prof.suspended_at = timezone.now()
            target_prof.save()

            target_user.is_active = False
            target_user.save(update_fields=['is_active'])

            action_name = 'ACCOUNT_BANNED' if new_status == UserProfile.ACCOUNT_BANNED else 'ACCOUNT_SUSPENDED'
            AuditLog.record(
                actor=request.user,
                action=action_name,
                target_type='UserProfile',
                target_id=target_prof.pk,
                target_repr=f"User {target_user.username} ({target_prof.get_role_display()})",
                details=f"{new_status.title()} applied. Rationale: {target_prof.suspension_reason}"
            )
            Notification.send(
                recipient=target_user,
                actor=request.user,
                title=f"Account {new_status.title()}",
                message=f"Your VenomWatch account has been {new_status.lower()}. Reason: {target_prof.suspension_reason}",
                notification_type=Notification.TYPE_DANGER
            )
            messages.warning(request, f"Account '{target_user.username}' has been {new_status.lower()}.")
            return redirect('accounts:admin_provision')

        # --- 5. Reinstate Account ---
        elif action == 'reinstate_account':
            target_user_id = request.POST.get('user_id')
            target_user = get_object_or_404(User, pk=target_user_id)
            target_prof = target_user.profile
            target_prof.account_status = UserProfile.ACCOUNT_ACTIVE
            target_prof.suspension_reason = None
            target_prof.suspended_by = None
            target_prof.suspended_at = None
            target_prof.save()

            target_user.is_active = True
            target_user.save(update_fields=['is_active'])

            AuditLog.record(
                actor=request.user,
                action='ACCOUNT_REINSTATED',
                target_type='UserProfile',
                target_id=target_prof.pk,
                target_repr=f"User {target_user.username} ({target_prof.get_role_display()})",
                details="Account operational status reinstated to ACTIVE."
            )
            Notification.send(
                recipient=target_user,
                actor=request.user,
                title="Account Reinstated",
                message="Your VenomWatch operational account has been reinstated. You may now resume operational duties.",
                notification_type=Notification.TYPE_SUCCESS,
                link=reverse('accounts:login')
            )
            messages.success(request, f"Account '{target_user.username}' has been reinstated to ACTIVE status.")
            return redirect('accounts:admin_provision')

        # --- 6. Account Deactivation / Reactivation (legacy toggle) ---
        elif action == 'toggle_status':
            target_user_id = request.POST.get('user_id')
            target_user = get_object_or_404(User, pk=target_user_id)

            if target_user.pk == request.user.pk:
                messages.error(request, "Security Policy Violation: You cannot deactivate your own active administrative account.")
                return redirect('accounts:admin_provision')

            target_prof = getattr(target_user, 'profile', None)
            if target_user.is_superuser or (target_prof and target_prof.is_admin):
                active_admins_count = User.objects.filter(is_active=True).filter(
                    Q(is_superuser=True) | Q(profile__role=UserProfile.ROLE_ADMIN)
                ).distinct().count()
                if active_admins_count <= 1 and target_user.is_active:
                    messages.error(request, "Security Policy Violation: Cannot deactivate the last remaining active administrative account.")
                    return redirect('accounts:admin_provision')

            target_user.is_active = not target_user.is_active
            target_user.save()

            if target_user.is_active:
                messages.success(request, f"Account '{target_user.username}' has been successfully reactivated.")
            else:
                messages.warning(
                    request,
                    f"Account '{target_user.username}' has been deactivated. "
                    "Login access is disabled while all historical sightings, assignments, and audit logs remain preserved."
                )
            return redirect('accounts:admin_provision')

        # --- 7. Direct Provisioning: Add Authority Officer ---
        elif action == 'add_authority' or (request.POST.get('role') == UserProfile.ROLE_AUTHORITY and action != 'add_ranger'):
            active_tab = 'authority'
            authority_form = AdminAuthorityProvisionForm(request.POST)
            if authority_form.is_valid():
                new_user = authority_form.save()
                messages.success(
                    request,
                    f"Authority Officer account '{new_user.username}' "
                    f"({new_user.profile.full_name or new_user.username}) successfully provisioned and activated."
                )
                return redirect('accounts:admin_provision')
            else:
                messages.error(request, "Failed to create Authority Officer account. Please review the errors below.")

        # --- 8. Direct Provisioning: Add Forest Ranger ---
        elif action == 'add_ranger' or request.POST.get('role') == UserProfile.ROLE_RANGER:
            active_tab = 'ranger'
            ranger_form = AdminRangerProvisionForm(request.POST)
            if ranger_form.is_valid():
                new_user = ranger_form.save()
                messages.success(
                    request,
                    f"Forest Ranger account '{new_user.username}' "
                    f"({new_user.profile.full_name or new_user.username}) successfully provisioned with base '{new_user.profile.registered_location}'."
                )
                return redirect('accounts:admin_provision')
            else:
                messages.error(request, "Failed to create Forest Ranger account. Please review the errors below.")

        # --- 9. Fallback Generic Provisioning Form ---
        else:
            form = AdminAccountProvisionForm(request.POST)
            if form.is_valid():
                new_user = form.save()
                messages.success(
                    request,
                    f"Successfully provisioned {new_user.profile.get_role_display()} account for '{new_user.username}'."
                )
                return redirect('accounts:admin_provision')
            else:
                messages.error(request, "Failed to provision account. Please check the form errors below.")
                if request.POST.get('role') == UserProfile.ROLE_RANGER:
                    active_tab = 'ranger'
                    ranger_form = AdminRangerProvisionForm(request.POST)
                    ranger_form.is_valid()
                else:
                    active_tab = 'authority'
                    authority_form = AdminAuthorityProvisionForm(request.POST)
                    authority_form.is_valid()

    # Query operational roster
    roster_qs = User.objects.filter(
        profile__role__in=['authority', 'ranger', 'admin']
    ).select_related('profile').order_by('-date_joined')

    # Pending and reviewed registration applications
    pending_applications = AccountApplication.objects.filter(
        status=AccountApplication.STATUS_PENDING
    ).select_related('user').order_by('-submitted_at')

    reviewed_applications = AccountApplication.objects.exclude(
        status=AccountApplication.STATUS_PENDING
    ).select_related('user', 'reviewed_by').order_by('-reviewed_at')[:20]

    # Audit log entries
    audit_logs = AuditLog.objects.select_related('actor').order_by('-timestamp')[:25]

    # Quick statistics across all operational accounts
    total_authority = roster_qs.filter(profile__role=UserProfile.ROLE_AUTHORITY).count()
    total_rangers = roster_qs.filter(profile__role=UserProfile.ROLE_RANGER).count()
    available_rangers = roster_qs.filter(
        profile__role=UserProfile.ROLE_RANGER,
        profile__availability=UserProfile.AVAILABILITY_AVAILABLE,
        is_active=True
    ).count()
    deactivated_count = roster_qs.filter(is_active=False).count()
    suspended_count = roster_qs.filter(profile__account_status=UserProfile.ACCOUNT_SUSPENDED).count()
    banned_count = roster_qs.filter(profile__account_status=UserProfile.ACCOUNT_BANNED).count()

    # Optional roster filtering
    role_filter = request.GET.get('role', '').strip().lower()
    status_filter = request.GET.get('status', '').strip().lower()
    search_q = request.GET.get('q', '').strip()

    filtered_users = roster_qs
    if role_filter in ['authority', 'ranger', 'admin']:
        filtered_users = filtered_users.filter(profile__role=role_filter)
    if status_filter == 'active':
        filtered_users = filtered_users.filter(is_active=True, profile__account_status=UserProfile.ACCOUNT_ACTIVE)
    elif status_filter == 'suspended':
        filtered_users = filtered_users.filter(profile__account_status=UserProfile.ACCOUNT_SUSPENDED)
    elif status_filter == 'banned':
        filtered_users = filtered_users.filter(profile__account_status=UserProfile.ACCOUNT_BANNED)
    elif status_filter == 'inactive':
        filtered_users = filtered_users.filter(is_active=False)

    if search_q:
        filtered_users = filtered_users.filter(
            Q(username__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(profile__full_name__icontains=search_q) |
            Q(profile__assigned_region__icontains=search_q) |
            Q(profile__registered_location__icontains=search_q) |
            Q(profile__organization__icontains=search_q)
        )

    return render(request, 'accounts/admin_provision.html', {
        'authority_form': authority_form,
        'ranger_form': ranger_form,
        'form': form,
        'provisioned_users': filtered_users,
        'pending_applications': pending_applications,
        'reviewed_applications': reviewed_applications,
        'audit_logs': audit_logs,
        'active_tab': active_tab,
        'stats': {
            'total_authority': total_authority,
            'total_rangers': total_rangers,
            'available_rangers': available_rangers,
            'deactivated_accounts': deactivated_count,
            'suspended_accounts': suspended_count,
            'banned_accounts': banned_count,
            'pending_applications': pending_applications.count(),
            'total_accounts': roster_qs.count(),
        },
        'filters': {
            'role': role_filter,
            'status': status_filter,
            'q': search_q,
        }
    })


@login_required
@never_cache
def admin_application_detail_view(request, app_id):
    """
    Platform Admin: Read-only Registration Application Details view.
    Displays applicant contact info, requested role, location coordinates,
    submission timestamp, status, and verification document inspection link.
    """
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import get_object_or_404, render
    from .models import AccountApplication

    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        raise PermissionDenied("Access Denied: Platform Administrator privileges required to view application details.")

    app = get_object_or_404(AccountApplication.objects.select_related('user', 'reviewed_by'), pk=app_id)

    return render(request, 'accounts/admin_application_detail.html', {
        'app': app,
        'page_title': f"Application #{app.pk} - {app.full_name}",
    })


@login_required
@never_cache
def admin_application_document_view(request, app_id):
    """
    Securely serves private supporting documents to Platform Administrators only.
    Strictly blocks access to non-admin users and does not expose direct public file URLs.
    Handles missing applications and documents safely with informative responses.
    """
    import mimetypes
    from django.http import FileResponse
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import get_object_or_404, render
    from .models import AccountApplication

    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        raise PermissionDenied("Access Denied: Platform Administrator privileges required to view verification documents.")

    try:
        app = AccountApplication.objects.select_related('user').get(pk=app_id)
    except AccountApplication.DoesNotExist:
        return render(request, 'accounts/admin_document_error.html', {
            'error_title': 'Application Not Found',
            'error_message': f'Application #{app_id} does not exist in the database.',
            'back_url': reverse('accounts:admin_provision') + '?tab=applications',
        }, status=404)

    if not app.supporting_document:
        return render(request, 'accounts/admin_document_error.html', {
            'application': app,
            'error_title': 'No Document Attached',
            'error_message': f'No verification document was uploaded with application #{app.id} ({app.full_name}).',
            'back_url': reverse('accounts:admin_provision') + '?tab=applications',
        }, status=404)

    try:
        f = app.supporting_document.open('rb')
    except Exception as e:
        logger.error(f"Error opening verification document for application #{app_id}: {e}")
        return render(request, 'accounts/admin_document_error.html', {
            'application': app,
            'error_title': 'Document File Unavailable',
            'error_message': f'The document file for application #{app.id} could not be read from disk storage ({e}).',
            'back_url': reverse('accounts:admin_provision') + '?tab=applications',
        }, status=404)

    content_type, _ = mimetypes.guess_type(app.supporting_document.name)
    content_type = content_type or 'application/octet-stream'

    response = FileResponse(f, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{app.supporting_document.name.split("/")[-1]}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@never_cache
def admin_application_approve_view(request, app_id):
    """
    Platform Admin: Approve registration application.
    Requires POST method. Validates application is pending, activates user account,
    assigns requested role, records audit log, and notifies applicant.
    """
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import get_object_or_404, redirect
    from django.utils import timezone
    from django.db import transaction
    from .models import AccountApplication, UserProfile, AuditLog, Notification

    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    if request.method != 'POST':
        messages.error(request, "Invalid request method. Approval must be submitted via POST.")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

    app = get_object_or_404(AccountApplication.objects.select_related('user'), pk=app_id)

    # Validate that application is still awaiting review
    if app.status == AccountApplication.STATUS_APPROVED:
        messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been approved.")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")
    elif app.status == AccountApplication.STATUS_REJECTED:
        messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been rejected and cannot be directly approved.")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

    with transaction.atomic():
        app.status = AccountApplication.STATUS_APPROVED
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save()

        target_user = app.user
        target_user.is_active = True
        target_user.save(update_fields=['is_active'])

        target_prof, _ = UserProfile.objects.get_or_create(user=target_user)
        target_prof.role = app.requested_role
        if app.organization:
            target_prof.organization = app.organization
        if app.assigned_region:
            target_prof.assigned_region = app.assigned_region
        if app.registered_location:
            target_prof.registered_location = app.registered_location
        if app.latitude is not None:
            target_prof.latitude = app.latitude
        if app.longitude is not None:
            target_prof.longitude = app.longitude
        target_prof.account_status = UserProfile.ACCOUNT_ACTIVE
        target_prof.save()

        AuditLog.record(
            actor=request.user,
            action='APPLICATION_APPROVED',
            target_type='AccountApplication',
            target_id=app.pk,
            target_repr=f"Application #{app.pk} ({target_user.username})",
            details=f"Approved and activated {app.get_requested_role_display()} account."
        )
        Notification.send(
            recipient=target_user,
            actor=request.user,
            title="Application Approved",
            message=f"Your application for an official {app.get_requested_role_display()} account has been approved. You may now sign in.",
            notification_type=Notification.TYPE_SUCCESS,
            link=reverse('accounts:login')
        )

    messages.success(request, f"Application #{app.pk} ({target_user.username}) approved. Account is now active.")
    return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")


@login_required
@never_cache
def admin_application_reject_view(request, app_id):
    """
    Platform Admin: Reject registration application.
    Requires POST method. Validates application is pending, deactivates account,
    records documented rejection reason, creates audit log, and notifies applicant.
    """
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import get_object_or_404, redirect
    from django.utils import timezone
    from django.db import transaction
    from .models import AccountApplication, UserProfile, AuditLog, Notification

    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    if request.method != 'POST':
        messages.error(request, "Destructive action prevented: Rejection must be submitted via POST confirmation.")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

    app = get_object_or_404(AccountApplication.objects.select_related('user'), pk=app_id)

    if app.status in [AccountApplication.STATUS_APPROVED, AccountApplication.STATUS_REJECTED]:
        messages.warning(request, f"Application #{app.pk} ({app.user.username}) has already been reviewed ({app.get_status_display()}).")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

    reason = request.POST.get('rejection_reason', '').strip()
    if not reason:
        messages.error(request, "A documented rejection reason is required to reject an application.")
        return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")

    with transaction.atomic():
        app.status = AccountApplication.STATUS_REJECTED
        app.rejection_reason = reason
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save()

        target_user = app.user
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])

        if hasattr(target_user, 'profile'):
            target_user.profile.account_status = UserProfile.ACCOUNT_SUSPENDED
            target_user.profile.save(update_fields=['account_status'])

        AuditLog.record(
            actor=request.user,
            action='APPLICATION_REJECTED',
            target_type='AccountApplication',
            target_id=app.pk,
            target_repr=f"Application #{app.pk} ({target_user.username})",
            details=f"Rejected. Rationale: {app.rejection_reason}"
        )
        Notification.send(
            recipient=target_user,
            actor=request.user,
            title="Application Not Approved",
            message=f"Your application for an official account was not approved. Reason: {app.rejection_reason}",
            notification_type=Notification.TYPE_DANGER
        )

    messages.warning(request, f"Application #{app.pk} ({target_user.username}) rejected.")
    return redirect(f"{reverse('accounts:admin_provision')}?tab=applications")


def protected_media_block_view(request, path=''):
    """
    Security gate: Denies direct HTTP access to verification documents under /media/verification_docs/.
    """
    from django.core.exceptions import PermissionDenied
    raise PermissionDenied("Access Denied: Direct public access to verification documents is strictly prohibited.")


@login_required
@never_cache
def notifications_list_view(request):
    """View all persistent in-app notifications for the logged in user."""
    notifications = request.user.notifications.all()
    # Mark read on view
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifications})


@login_required
@never_cache
def mark_notification_read_view(request, pk):
    """Marks a single notification as read and redirects to its link or notifications page."""
    from django.shortcuts import get_object_or_404
    notif = get_object_or_404(request.user.notifications, pk=pk)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if notif.link:
        return redirect(notif.link)
    return redirect('accounts:notifications_list')


@login_required
@never_cache
def admin_dashboard_view(request):
    """
    Focused Platform Admin Dashboard:
    Displays only essential administration metrics calculated from real database records:
    1. Pending Authority applications
    2. Pending Ranger applications
    3. Active Authority accounts
    4. Active Ranger accounts
    5. Suspended / Banned accounts count
    Provides exactly three primary actions: Review Applications, Manage Accounts, Manage Hospital Registry.
    """
    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    from django.contrib.auth.models import User
    from .models import UserProfile, AccountApplication

    # Actual Database Metrics
    pending_authority = AccountApplication.objects.filter(
        status=AccountApplication.STATUS_PENDING,
        requested_role=UserProfile.ROLE_AUTHORITY
    ).count()

    pending_ranger = AccountApplication.objects.filter(
        status=AccountApplication.STATUS_PENDING,
        requested_role=UserProfile.ROLE_RANGER
    ).count()

    active_authority = UserProfile.objects.filter(
        role=UserProfile.ROLE_AUTHORITY,
        account_status=UserProfile.ACCOUNT_ACTIVE,
        user__is_active=True
    ).count()

    active_ranger = UserProfile.objects.filter(
        role=UserProfile.ROLE_RANGER,
        account_status=UserProfile.ACCOUNT_ACTIVE,
        user__is_active=True
    ).count()

    suspended_banned_count = UserProfile.objects.filter(
        account_status__in=[UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED]
    ).count()

    total_pending = pending_authority + pending_ranger

    return render(request, 'accounts/admin_dashboard.html', {
        'stats': {
            'pending_authority': pending_authority,
            'pending_ranger': pending_ranger,
            'total_pending': total_pending,
            'active_authority': active_authority,
            'active_ranger': active_ranger,
            'suspended_banned_count': suspended_banned_count,
        }
    })


@login_required
@never_cache
def admin_account_edit_view(request, user_id):
    """
    Platform Admin: Read-only Account Detail View.
    SECURITY REQUIREMENT: Platform Administrators must NOT edit personal or operational
    details of existing Authority or Ranger accounts (e.g. name, email, phone, location,
    coordinates, availability, role).
    Crafted POST requests attempting to alter account profiles are blocked with PermissionDenied.
    Account status management (suspension, ban, reinstatement) is handled via the audited
    admin_provision_account_view workflow.
    """
    prof = getattr(request.user, 'profile', None)
    if not (request.user.is_superuser or (prof and prof.is_admin)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Access Denied: Platform Administrator privileges required.")

    from django.contrib.auth.models import User
    from django.shortcuts import get_object_or_404
    from django.core.exceptions import PermissionDenied

    target_user = get_object_or_404(User.objects.select_related('profile'), pk=user_id)

    if request.method == 'POST':
        # Strictly reject any attempt to modify profile fields
        raise PermissionDenied(
            "Access Denied: Platform Administrators are not permitted to edit personal or operational "
            "details of Authority or Ranger accounts. Profile details are maintained by the account owner."
        )

    return render(request, 'accounts/admin_account_detail.html', {
        'target_user': target_user,
    })


# Read-only detail view alias
admin_account_detail_view = admin_account_edit_view



