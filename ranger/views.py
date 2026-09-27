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


@login_required
@ranger_required
@never_cache
@require_POST
def assignment_update_view(request, pk):
    """Ranger lifecycle actions: ACCEPT / DECLINE / ON THE WAY / AT LOCATION / COMPLETE.

    Only the strictly allowed next transition is accepted; anything else
    (including arbitrary status injection) is rejected server-side.
    Completing requires an outcome choice.
    """
    assignment = get_object_or_404(RangerAssignment, pk=pk, ranger=request.user)
    action = request.POST.get('action', '')

    valid_actions = {
        'ACCEPT': RangerAssignment.STATUS_ACCEPTED,
        'DECLINE': RangerAssignment.STATUS_DECLINED,
        'ON_THE_WAY': RangerAssignment.STATUS_ON_THE_WAY,
        'AT_LOCATION': RangerAssignment.STATUS_AT_LOCATION,
        'COMPLETE': RangerAssignment.STATUS_COMPLETED,
    }
    target = valid_actions.get(action)

    if target is None:
        messages.error(request, "Unknown assignment action.")
        return redirect('ranger:assignment_detail', pk=assignment.pk)

    if not assignment.can_transition(target):
        messages.error(
            request,
            f"Illegal status change: cannot move from '{assignment.get_status_display()}' "
            f"to '{target.replace('_', ' ').title()}'.")
        return redirect('ranger:assignment_detail', pk=assignment.pk)

    profile = request.user.profile

    if target == RangerAssignment.STATUS_COMPLETED:
        outcome = request.POST.get('outcome', '')
        outcome_keys = dict(RangerAssignment.OUTCOME_CHOICES)
        if outcome not in outcome_keys:
            messages.error(request, "Please select a valid outcome before completing the assignment.")
            return redirect('ranger:assignment_detail', pk=assignment.pk)
        assignment.outcome = outcome
        assignment.notes = request.POST.get('notes', '').strip() or None
        img = request.FILES.get('outcome_image')
        if img:
            assignment.outcome_image = img
        assignment.completed_at = timezone.now()
        # Free the ranger back to AVAILABLE once work is done
        if profile.availability == UserProfile.AVAILABILITY_BUSY:
            profile.availability = UserProfile.AVAILABILITY_AVAILABLE
            profile.save(update_fields=['availability'])
        # Resolve parent report response state
        rep = assignment.sighting
        rep.response_status = SightingReport.RESPONSE_RESOLVED
        rep.status = SightingReport.STATUS_RESOLVED
        rep.save(update_fields=['response_status', 'status'])
        messages.success(request, f"Assignment #{assignment.pk} completed — outcome recorded.")
    elif target == RangerAssignment.STATUS_DECLINED:
        assignment.responded_at = timezone.now()
        # Ranger stays AVAILABLE after declining
        messages.info(request, "You declined this assignment. The Authority has been notified and can reassign.")
    else:
        if target == RangerAssignment.STATUS_ACCEPTED:
            assignment.responded_at = timezone.now()
            # First active step -> ranger becomes BUSY
            if profile.availability == UserProfile.AVAILABILITY_AVAILABLE:
                profile.availability = UserProfile.AVAILABILITY_BUSY
                profile.save(update_fields=['availability'])
        messages.success(request, f"Assignment updated: {target.replace('_', ' ').title()}.")

    assignment.status = target
    assignment.save(update_fields=['status', 'responded_at', 'completed_at', 'outcome', 'notes', 'outcome_image'])
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
