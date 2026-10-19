"""Ranger Console — dedicated, isolated module for RANGER-role users.

Security model (enforced server-side, never template-only):
- Every view is decorated with @ranger_required (role check).
- Assignment detail/action views fetch the assignment filtered by
  ranger=request.user, so changing a URL ID to another ranger's
  assignment returns 404/403 — object-level security.
- Rangers get NO access to the Authority dashboard, all-reports list,
  hotspot administration or assignment controls.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.decorators import ranger_required
from accounts.forms import UserProfileForm
from reports.models import SightingReport, RangerAssignment
from accounts.models import UserProfile


def _active_assignment_ids(user):
    return RangerAssignment.objects.filter(
        ranger=user, status__in=RangerAssignment.ACTIVE_STATUSES
    ).values_list('sighting_id', flat=True)


@login_required
@ranger_required
@never_cache
def ranger_dashboard_view(request):
    """Ranger landing page: stats + NEW (unseen) assignments."""
    user = request.user
    qs = RangerAssignment.objects.filter(ranger=user).select_related('sighting')

    new_assignments = qs.filter(status=RangerAssignment.STATUS_ASSIGNED, is_read=False)
    active = qs.filter(status__in=RangerAssignment.ACTIVE_STATUSES)
    completed = qs.filter(status=RangerAssignment.STATUS_COMPLETED)

    context = {
        'new_assignments': new_assignments,
        'active_assignments': active,
        'completed_count': completed.count(),
        'active_count': active.count(),
        'new_count': new_assignments.count(),
        'unread_count': qs.filter(is_read=False).count(),
        'profile': user.profile,
    }
    return render(request, 'ranger/dashboard.html', context)


@login_required
@ranger_required
@never_cache
def assignment_list_view(request):
    """ONLY this ranger's assignments — never the full report repository."""
    assignments = (
        RangerAssignment.objects.filter(ranger=request.user)
        .select_related('sighting')
    )
    return render(request, 'ranger/assignments.html', {
        'assignments': assignments,
        'unread_count': assignments.filter(is_read=False).count(),
    })


@login_required
@ranger_required
@never_cache
def assignment_detail_view(request, pk):
    """Object-level security: assignment must belong to request.user."""
    assignment = get_object_or_404(
        RangerAssignment.objects.select_related('sighting', 'assigned_by'),
        pk=pk, ranger=request.user,
    )

    # Mark-as-read notification state
    if not assignment.is_read:
        assignment.is_read = True
        assignment.read_at = timezone.now()
        assignment.save(update_fields=['is_read', 'read_at'])

    return render(request, 'ranger/assignment_detail.html', {
        'assignment': assignment,
        'report': assignment.sighting,
        'next_action': assignment.next_action,
    })


from django.urls import reverse
from accounts.models import UserProfile, Notification, AuditLog


@login_required
@ranger_required
@never_cache
@require_POST
def assignment_update_view(request, pk):
    """Ranger lifecycle actions: ACCEPT / DECLINE / ON_THE_WAY / AT_LOCATION / SUBMIT_OUTCOME.

    Only strictly allowed next transitions are accepted; arbitrary status jumps are rejected server-side.
    Rangers CANNOT self-verify or mark an incident completed; only Authority review can verify outcomes.
    """
    assignment = get_object_or_404(RangerAssignment, pk=pk, ranger=request.user)
    action = request.POST.get('action', '').strip()

    valid_actions = {
        'ACCEPT': RangerAssignment.STATUS_ACCEPTED,
        'DECLINE': RangerAssignment.STATUS_DECLINED,
        'ON_THE_WAY': RangerAssignment.STATUS_ON_THE_WAY,
        'AT_LOCATION': RangerAssignment.STATUS_AT_LOCATION,
        'SUBMIT_OUTCOME': RangerAssignment.STATUS_OUTCOME_SUBMITTED,
    }
    target = valid_actions.get(action)

    if target is None:
        messages.error(request, "Invalid or unauthorized assignment action.")
        return redirect('ranger:assignment_detail', pk=assignment.pk)

    if not assignment.can_transition(target):
        messages.error(
            request,
            f"Illegal status change: cannot transition from '{assignment.get_status_display()}' "
            f"to '{target.replace('_', ' ').title()}'.")
        return redirect('ranger:assignment_detail', pk=assignment.pk)

    profile = request.user.profile
    sighting = assignment.sighting

    if target == RangerAssignment.STATUS_ACCEPTED:
        assignment.status = target
        assignment.responded_at = timezone.now()
        assignment.save(update_fields=['status', 'responded_at'])

        # Ranger transitions to BUSY
        if profile.availability == UserProfile.AVAILABILITY_AVAILABLE:
            profile.availability = UserProfile.AVAILABILITY_BUSY
            profile.save(update_fields=['availability'])

        # Update parent report response status
        sighting.response_status = SightingReport.RESPONSE_IN_PROGRESS
        sighting.save(update_fields=['response_status'])

        AuditLog.record(
            actor=request.user,
            action='ACCEPT_ASSIGNMENT',
            target_type='RangerAssignment',
            target_id=assignment.pk,
            target_repr=f"Assignment #{assignment.pk} for Incident #{sighting.pk}",
            details="Ranger accepted incident dispatch."
        )

        # Notify Citizen that assigned ranger accepted
        Notification.send(
            recipient=sighting.user,
            actor=request.user,
            title="Ranger Accepted Sighting",
            message=f"Ranger {profile.display_name} has accepted Incident #{sighting.pk} and is preparing to respond.",
            notification_type=Notification.TYPE_SUCCESS,
            link=reverse('reports:detail', kwargs={'pk': sighting.pk})
        )

        # Notify Authority
        if assignment.assigned_by:
            Notification.send(
                recipient=assignment.assigned_by,
                actor=request.user,
                title="Assignment Accepted",
                message=f"Ranger {profile.display_name} accepted dispatch for Incident #{sighting.pk}.",
                notification_type=Notification.TYPE_INFO,
                link=reverse('reports:detail', kwargs={'pk': sighting.pk})
            )

        messages.success(request, f"Assignment #{assignment.pk} accepted. You are now designated responder.")

    elif target == RangerAssignment.STATUS_DECLINED:
        assignment.status = target
        assignment.responded_at = timezone.now()
        assignment.save(update_fields=['status', 'responded_at'])

        # Sighting returns to unassigned
        sighting.assigned_responder = None
        sighting.response_status = SightingReport.RESPONSE_UNASSIGNED
        sighting.save(update_fields=['assigned_responder', 'response_status'])

        AuditLog.record(
            actor=request.user,
            action='DECLINE_ASSIGNMENT',
            target_type='RangerAssignment',
            target_id=assignment.pk,
            target_repr=f"Assignment #{assignment.pk} for Incident #{sighting.pk}",
            details="Ranger declined assignment."
        )

        # Notify Authority of decline so they can reassign
        if assignment.assigned_by:
            Notification.send(
                recipient=assignment.assigned_by,
                actor=request.user,
                title="Assignment Declined",
                message=f"Ranger {profile.display_name} declined Incident #{sighting.pk}. Reassignment required.",
                notification_type=Notification.TYPE_WARNING,
                link=reverse('reports:detail', kwargs={'pk': sighting.pk})
            )

        messages.info(request, "You declined this assignment. The Authority has been notified to reassign another responder.")

    elif target == RangerAssignment.STATUS_ON_THE_WAY:
        assignment.status = target
        assignment.save(update_fields=['status'])

        sighting.response_status = SightingReport.RESPONSE_IN_PROGRESS
        sighting.save(update_fields=['response_status'])

        AuditLog.record(
            actor=request.user,
            action='PROGRESS_UPDATE',
            target_type='RangerAssignment',
            target_id=assignment.pk,
            target_repr=f"Assignment #{assignment.pk} for Incident #{sighting.pk}",
            details="Ranger is on the way to incident location."
        )

        Notification.send(
            recipient=sighting.user,
            actor=request.user,
            title="Ranger En Route",
            message=f"Ranger {profile.display_name} is currently on the way to your reported sighting location for Incident #{sighting.pk}.",
            notification_type=Notification.TYPE_INFO,
            link=reverse('reports:detail', kwargs={'pk': sighting.pk})
        )

        messages.success(request, "Status updated: On The Way to incident location.")

    elif target == RangerAssignment.STATUS_AT_LOCATION:
        assignment.status = target
        assignment.save(update_fields=['status'])

        sighting.response_status = SightingReport.RESPONSE_IN_PROGRESS
        sighting.save(update_fields=['response_status'])

        AuditLog.record(
            actor=request.user,
            action='PROGRESS_UPDATE',
            target_type='RangerAssignment',
            target_id=assignment.pk,
            target_repr=f"Assignment #{assignment.pk} for Incident #{sighting.pk}",
            details="Ranger has arrived at the incident location."
        )

        Notification.send(
            recipient=sighting.user,
            actor=request.user,
            title="Ranger At Location",
            message=f"Ranger {profile.display_name} has arrived at the sighting location for Incident #{sighting.pk} and has initiated search / inspection.",
            notification_type=Notification.TYPE_INFO,
            link=reverse('reports:detail', kwargs={'pk': sighting.pk})
        )

        messages.success(request, "Status updated: At Location. Conduct search and record evidence.")

    elif target == RangerAssignment.STATUS_OUTCOME_SUBMITTED:
        outcome = request.POST.get('outcome', '').strip()
        outcome_keys = dict(RangerAssignment.OUTCOME_CHOICES)
        if outcome not in outcome_keys:
            messages.error(request, "Please select a valid response outcome category before submitting.")
            return redirect('ranger:assignment_detail', pk=assignment.pk)

        notes = request.POST.get('notes', '').strip()
        if not notes:
            messages.error(request, "Please provide field notes documenting the incident response findings.")
            return redirect('ranger:assignment_detail', pk=assignment.pk)

        img = request.FILES.get('outcome_image')
        if img:
            # Validate evidence image
            if img.size > 5 * 1024 * 1024:
                messages.error(request, "Supporting evidence image must not exceed 5 MB in file size.")
                return redirect('ranger:assignment_detail', pk=assignment.pk)
            import os
            ext = os.path.splitext(img.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                messages.error(request, "Supporting evidence image must be JPEG or PNG format.")
                return redirect('ranger:assignment_detail', pk=assignment.pk)
            assignment.outcome_image = img

        assignment.outcome = outcome
        assignment.notes = notes
        assignment.outcome_submitted_at = timezone.now()
        assignment.review_decision = 'PENDING_REVIEW'
        assignment.status = target
        assignment.save(update_fields=['status', 'outcome', 'notes', 'outcome_image', 'outcome_submitted_at', 'review_decision'])

        AuditLog.record(
            actor=request.user,
            action='OUTCOME_SUBMITTED',
            target_type='RangerAssignment',
            target_id=assignment.pk,
            target_repr=f"Assignment #{assignment.pk} for Incident #{sighting.pk}",
            details=f"Outcome: {assignment.get_outcome_display()}. Notes: {notes}"
        )

        # Notify Authority for verification
        if assignment.assigned_by:
            Notification.send(
                recipient=assignment.assigned_by,
                actor=request.user,
                title="Outcome Submitted for Verification",
                message=f"Ranger {profile.display_name} submitted outcome ({assignment.get_outcome_display()}) for Incident #{sighting.pk}. Authority verification required.",
                notification_type=Notification.TYPE_WARNING,
                link=reverse('reports:detail', kwargs={'pk': sighting.pk})
            )

        # Notify Citizen that response was submitted and awaits authority review
        Notification.send(
            recipient=sighting.user,
            actor=request.user,
            title="Field Response Submitted",
            message=f"Ranger {profile.display_name} has concluded the field response for Incident #{sighting.pk}. Awaiting formal Authority verification.",
            notification_type=Notification.TYPE_INFO,
            link=reverse('reports:detail', kwargs={'pk': sighting.pk})
        )

        messages.success(request, f"Outcome report for Incident #{sighting.pk} submitted successfully. Awaiting formal Authority verification.")

    return redirect('ranger:assignment_detail', pk=assignment.pk)


@login_required
@ranger_required
@never_cache
def ranger_profile_view(request):
    """Ranger's own profile incl. operational base (location used for dispatch)."""
    profile = request.user.profile
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your ranger profile details have been updated.")
            return redirect('ranger:profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'ranger/profile.html', {'form': form, 'profile': profile})
