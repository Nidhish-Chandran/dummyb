from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from .models import SightingReport
from .forms import SightingReportForm
from .services import DuplicateSpamDetectionService
from ai.services import SnakeAIPipelineService
from hotspots.services import DBSCANHotspotService
from accounts.models import UserProfile, Notification, AuditLog
from accounts.decorators import authority_required
from .models import RangerAssignment
from .dispatch import get_candidate_rangers, haversine_km
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.urls import reverse


def _refresh_ranger_availability(ranger_user):
    """Recompute a ranger's availability from their active assignments.

    BUSY only while an ACCEPTED/ON_THE_WAY/AT_LOCATION assignment exists;
    otherwise AVAILABLE (an OFFLINE ranger is never auto-changed).
    """
    prof = getattr(ranger_user, 'profile', None)
    if prof is None or not prof.is_ranger:
        return
    if prof.availability == UserProfile.AVAILABILITY_OFFLINE:
        return
    busy_exists = RangerAssignment.objects.filter(
        ranger=ranger_user,
        status__in=[RangerAssignment.STATUS_ACCEPTED,
                    RangerAssignment.STATUS_ON_THE_WAY,
                    RangerAssignment.STATUS_AT_LOCATION],
    ).exists()
    want = UserProfile.AVAILABILITY_BUSY if busy_exists else UserProfile.AVAILABILITY_AVAILABLE
    if prof.availability != want:
        prof.availability = want
        prof.save(update_fields=['availability'])


@login_required
@never_cache
def create_report_view(request):
    """Citizen sighting submission view with AI feature analysis and duplicate/spam checks."""
    if request.method == 'POST':
        form = SightingReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            if request.user.is_authenticated:
                report.user = request.user
            report.save()

            # 1. Trigger Two-Stage AI Pipeline (Model #1 Snake Detection + Model #2 Venom Classification)
            try:
                ai_results = SnakeAIPipelineService.analyze_image(report.original_image.path)
                
                report.snake_detected = ai_results.get('snake_detected', False)
                report.snake_confidence = ai_results.get('snake_confidence', 0.0)
                report.venomous = ai_results.get('venomous')
                report.venom_confidence = ai_results.get('venom_confidence')
                
                species_name = ai_results.get('species')
                if not species_name:
                    species_name = 'Snake' if report.snake_detected else 'Not a Snake'
                report.species_predicted = species_name
                report.venom_category = ai_results.get('venom_category') or 'NON_VENOMOUS'
                report.ai_confidence = report.venom_confidence if report.venom_confidence is not None else report.snake_confidence
                report.model_1_name = 'Snake Detector'
                report.model_2_name = 'Venom Classifier'
                
                report.save()
            except Exception as e:
                messages.warning(request, f"Report logged. AI processing note: {str(e)}")

            # 2. Trigger Duplicate Proximity & Spam Rate-limit Evaluator
            try:
                report = DuplicateSpamDetectionService.evaluate_and_flag(report)
                if report.duplicate_flag and report.duplicate_of:
                    messages.info(request, f"Note: This report has been linked as an update to existing incident {report.duplicate_of.report_reference}.")
                elif report.duplicate_flag:
                    messages.info(request, "Note: This report has been flagged for authority review as a potential duplicate of a recent sighting.")
                if report.spam_flag:
                    messages.warning(request, "Note: Submission rate limit flagged for administrative review.")
            except Exception as e:
                pass

            ref = report.report_reference
            sub_num = f"#{report.citizen_submission_number}" if report.user else ""
            status_disp = report.get_status_display()
            if report.snake_detected:
                messages.success(request, f"Sighting report {ref} {sub_num} submitted successfully! Current status: {status_disp}. AI Result: {report.species_predicted} ({report.get_venom_category_display()}).")
            else:
                messages.info(request, f"Sighting report {ref} {sub_num} recorded. Current status: {status_disp}. Note: AI snake detector did not confirm a snake in the uploaded image.")
            return redirect('reports:detail', pk=report.pk)
        else:
            messages.error(request, "Error creating report. Please check the required form fields.")
    else:
        initial_data = {}
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            prof = request.user.profile
            if prof.latitude is not None and prof.longitude is not None:
                initial_data['latitude'] = prof.latitude
                initial_data['longitude'] = prof.longitude
            if prof.registered_location:
                initial_data['location_name'] = prof.registered_location

        if not initial_data.get('latitude'):
            initial_data['latitude'] = 9.9312
            initial_data['longitude'] = 76.2673

        form = SightingReportForm(initial=initial_data)

    return render(request, 'reports/create.html', {'form': form})


@login_required
@never_cache
def list_reports_view(request):
    """
    Role-specific report tracking:
    - Citizen: My Sightings only
    - Responder: Assigned response tasks
    - Authority/Admin: Full sighting repository with filters
    """
    user = request.user
    profile = getattr(user, 'profile', None)
    is_admin = profile is not None and profile.is_admin
    is_ranger_user = profile is not None and profile.is_ranger
    # Authority console = platform admins + authority officers (rangers use /ranger/)
    is_authority = profile is not None and profile.is_authority
    is_responder = False

    if is_ranger_user:
        # Rangers must work through their own isolated console.
        return redirect('ranger:dashboard')

    if is_authority:
        reports = SightingReport.objects.all()
    elif is_ranger_user:
        # Rangers may ONLY see reports explicitly assigned to them.
        reports = SightingReport.objects.filter(
            ranger_assignments__ranger=user
        ).distinct()
    else:
        # Citizen default: Only show own reports
        reports = SightingReport.objects.filter(user=user)

    query = request.GET.get('q')
    filter_venom = request.GET.get('venom')
    filter_active = request.GET.get('active')
    filter_dup = request.GET.get('duplicate')

    if query:
        reports = reports.filter(
            Q(title__icontains=query) |
            Q(location_name__icontains=query) |
            Q(species_predicted__icontains=query)
        )

    if filter_venom:
        reports = reports.filter(venom_category=filter_venom)

    if filter_active == '1':
        reports = [r for r in reports if r.is_active_48h]

    if filter_dup == '1' and is_authority:
        reports = reports.filter(duplicate_flag=True)

    # Fetch available responders for authority assignment modal/dropdown
    responders = User.objects.filter(profile__role__in=['ranger', 'authority']) if is_authority else []

    return render(request, 'reports/list.html', {
        'reports': reports,
        'query': query,
        'filter_venom': filter_venom,
        'filter_active': filter_active,
        'filter_dup': filter_dup,
        'is_authority': is_authority,
        'is_responder': is_responder,
        'responders': responders
    })


@login_required
@never_cache
def report_detail_view(request, pk):
    """
    Report detail view with strict backend permission check:
    Citizens can ONLY view their own reports.
    Authorities & assigned responders can view details.
    """
    report = get_object_or_404(SightingReport, pk=pk)
    user = request.user
    profile = getattr(user, 'profile', None)
    is_admin = profile is not None and profile.is_admin
    is_ranger_user = profile is not None and profile.is_ranger
    # Authority console = platform admins + authority officers
    is_authority = profile is not None and profile.is_authority
    is_assigned_responder = (report.assigned_responder == user)

    if is_ranger_user:
        # Rangers may ONLY open reports explicitly assigned to them via RangerAssignment.
        raise PermissionDenied(
            "Access Denied: Rangers must handle incidents through the "
            "Ranger Console (/ranger/assignments/).")
    elif not is_authority and not is_assigned_responder and report.user != user:
        raise PermissionDenied("Access Denied: You are not authorized to view other citizens' detailed report information or coordinates.")

    responders = User.objects.filter(profile__role__in=['ranger', 'authority']) if is_authority else []

    active_assignment = report.ranger_assignments.filter(
        status__in=RangerAssignment.ACTIVE_STATUSES).first()
    verified_assignment = report.ranger_assignments.filter(
        status=RangerAssignment.STATUS_COMPLETED, review_decision='APPROVED').first()
    assignment_history = report.ranger_assignments.all()[:10]
    candidate_rangers = get_candidate_rangers(report, only_available=True) if is_authority else []

    return render(request, 'reports/detail.html', {
        'report': report,
        'is_authority': is_authority,
        'is_assigned_responder': is_assigned_responder,
        'responders': responders,
        'active_assignment': active_assignment,
        'verified_assignment': verified_assignment,
        'candidate_rangers': candidate_rangers,
        'assignment_history': assignment_history,
    })


@login_required
@authority_required
@never_cache
def verify_report_view(request, pk):
    """Authority verification & status update endpoint."""
    report = get_object_or_404(SightingReport, pk=pk)

    if request.method == 'POST':
        if report.is_resolved:
            messages.warning(request, f"Report #{report.id} is already verified and resolved. The verification record is closed.")
            return redirect('reports:detail', pk=pk)

        new_status = request.POST.get('status')
        notes = request.POST.get('authority_notes', '')

        if new_status in dict(SightingReport.STATUS_CHOICES):
            report.status = new_status
            report.verified_by = request.user
            report.authority_notes = notes
            report.save()

            AuditLog.record(
                actor=request.user,
                action='VERIFY_INCIDENT',
                target_type='SightingReport',
                target_id=report.pk,
                target_repr=f"Incident #{report.pk}",
                details=f"Verification status set to '{report.get_status_display()}'. Notes: {notes}"
            )

            messages.success(request, f"Report #{report.id} verified status updated to '{report.get_status_display()}'.")

    return redirect('reports:detail', pk=pk)


@login_required
@authority_required
@never_cache
def assign_responder_view(request, pk):
    """Authority assigns a location-relevant AVAILABLE ranger to this report.

    Creates a formal RangerAssignment row (no text-only ranger names).
    Server-side re-validates the candidate against the report location —
    the Authority cannot assign an arbitrary/unrelated ranger by tampering
    with the posted ranger_id. Handles reassignment cleanly: the previous
    active assignment is CANCELLED and its ranger's availability recomputed.
    """
    report = get_object_or_404(SightingReport, pk=pk)
    wants_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def _fail(msg):
        if wants_json:
            return JsonResponse({'success': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('reports:detail', pk=pk)

    if report.status == SightingReport.STATUS_RESOLVED or report.response_status == SightingReport.RESPONSE_RESOLVED:
        return _fail("Cannot assign or reassign a responder to an incident that has already been verified and resolved.")

    if request.method == 'POST':
        ranger_id = request.POST.get('ranger_id') or request.POST.get('responder_id')
        if ranger_id:
            ranger_user = get_object_or_404(User, pk=ranger_id)
            prof = getattr(ranger_user, 'profile', None)
            if prof is None or prof.effective_role != UserProfile.ROLE_RANGER:
                return _fail("Selected user is not a registered Ranger.")

            # Location guard: the chosen ranger must be eligible and relevant to THIS report
            candidates = get_candidate_rangers(report, only_available=False)
            if not any(c['user'].pk == ranger_user.pk for c in candidates):
                return _fail(
                    "Access Denied: That ranger is not registered in or near this report's location or is ineligible.")
            if prof.availability != UserProfile.AVAILABILITY_AVAILABLE:
                return _fail(
                    f"{ranger_user.username} is currently {prof.get_availability_display()} and cannot take a new incident.")

            # Reassignment: Cancel any existing active assignment while preserving outcome evidence if submitted
            for prev in report.ranger_assignments.filter(status__in=RangerAssignment.ACTIVE_STATUSES):
                prev.status = RangerAssignment.STATUS_CANCELLED
                update_fields = ['status']
                if prev.outcome:
                    prev.review_notes = (prev.review_notes or '') + f" [Reassigned to Ranger {ranger_user.username} by Authority]"
                    update_fields.append('review_notes')
                prev.save(update_fields=update_fields)
                _refresh_ranger_availability(prev.ranger)

            dist = None
            if prof.latitude is not None and prof.longitude is not None:
                dist = haversine_km(prof.latitude, prof.longitude, report.latitude, report.longitude)

            new_assignment = RangerAssignment.objects.create(
                sighting=report,
                ranger=ranger_user,
                assigned_by=request.user,
                distance_km=dist,
                status=RangerAssignment.STATUS_ASSIGNED,
            )
            report.assigned_responder = ranger_user
            report.response_status = SightingReport.RESPONSE_ASSIGNED
            report.save(update_fields=['assigned_responder', 'response_status'])

            AuditLog.record(
                actor=request.user,
                action='ASSIGN_RANGER',
                target_type='SightingReport',
                target_id=report.pk,
                target_repr=f"Incident #{report.pk}",
                details=f"Assigned Ranger {ranger_user.username} ({dist} km away)."
            )

            Notification.send(
                recipient=ranger_user,
                actor=request.user,
                title="New Incident Assignment",
                message=f"You have been assigned to Incident #{report.pk} at {report.location_name or 'designated area'}. Please accept or decline.",
                notification_type=Notification.TYPE_WARNING,
                link=reverse('ranger:assignment_detail', kwargs={'pk': new_assignment.pk})
            )

            messages.success(request,
                f"Incident #{report.pk} assigned to ranger {prof.display_name}"
                + (f" ({dist} km away)." if dist is not None else "."))
            if wants_json:
                return JsonResponse({'success': True,
                                     'message': f"Incident #{report.pk} assigned to {prof.display_name}."})
        else:
            for prev in report.ranger_assignments.filter(status__in=RangerAssignment.ACTIVE_STATUSES):
                prev.status = RangerAssignment.STATUS_CANCELLED
                prev.save(update_fields=['status'])
                _refresh_ranger_availability(prev.ranger)
            report.assigned_responder = None
            report.response_status = SightingReport.RESPONSE_UNASSIGNED
            report.save(update_fields=['assigned_responder', 'response_status'])
            messages.info(request, "Active ranger assignment cancelled; incident marked unassigned.")

    return redirect('reports:detail', pk=pk)


@login_required
@authority_required
@never_cache
def cancel_assignment_view(request, pk):
    """Authority cancels the active assignment on a report (reassign control)."""
    assignment = get_object_or_404(RangerAssignment, pk=pk)
    rep = assignment.sighting

    if request.method == 'POST':
        # Guard 1: Resolved incidents cannot be cancelled or reopened
        if rep.status == SightingReport.STATUS_RESOLVED or rep.response_status == SightingReport.RESPONSE_RESOLVED or assignment.status == RangerAssignment.STATUS_COMPLETED:
            messages.error(request, "Cannot cancel or reassign an incident that has already been verified and resolved.")
            return redirect('reports:detail', pk=rep.pk)

        if not assignment.is_active:
            messages.info(request, "This assignment is already closed.")
            return redirect('reports:detail', pk=rep.pk)

        # Guard 2: If an outcome has already been submitted by the ranger, require explicit cancellation rationale
        cancellation_reason = request.POST.get('cancellation_reason', '').strip()
        if assignment.status == RangerAssignment.STATUS_OUTCOME_SUBMITTED and not cancellation_reason:
            messages.error(request, "An outcome has been submitted by the ranger and is awaiting review. Please review the outcome (Approve or Reject), or specify an explicit cancellation reason to reassign.")
            return redirect('reports:detail', pk=rep.pk)

        assignment.status = RangerAssignment.STATUS_CANCELLED
        update_fields = ['status']
        if cancellation_reason:
            assignment.review_notes = f"Assignment cancelled before verification: {cancellation_reason}"
            update_fields.append('review_notes')
        assignment.save(update_fields=update_fields)

        _refresh_ranger_availability(assignment.ranger)
        still_active = rep.ranger_assignments.filter(status__in=RangerAssignment.ACTIVE_STATUSES).first()
        if still_active is None:
            rep.assigned_responder = None
            rep.response_status = SightingReport.RESPONSE_UNASSIGNED
            rep.save(update_fields=['assigned_responder', 'response_status'])

        AuditLog.record(
            actor=request.user,
            action='CANCEL_ASSIGNMENT',
            target_type='SightingReport',
            target_id=rep.pk,
            target_repr=f"Incident #{rep.pk}",
            details=f"Cancelled assignment #{assignment.pk} for Ranger {assignment.ranger.username}. Reason: {cancellation_reason or 'No reason specified'}."
        )

        Notification.send(
            recipient=assignment.ranger,
            actor=request.user,
            title="Assignment Cancelled",
            message=f"Your assignment for Incident #{rep.pk} has been cancelled by Authority." + (f" Reason: {cancellation_reason}" if cancellation_reason else ""),
            notification_type=Notification.TYPE_INFO,
            link=reverse('ranger:dashboard')
        )

        messages.success(request, f"Assignment #{assignment.pk} cancelled." + (f" (Reason recorded: {cancellation_reason})" if cancellation_reason else ""))
    return redirect('reports:detail', pk=rep.pk)


@login_required
@authority_required
@never_cache
@require_POST
def review_assignment_outcome_view(request, pk):
    """Authority reviews and verifies the outcome reported by a Ranger.

    Actions:
    - APPROVE: Marks assignment COMPLETED, records reviewer, timestamp, and marks report RESOLVED.
    - REJECT: Returns assignment to AT_LOCATION with rejection rationale notes so the Ranger can follow up or rectify.
    - CLARIFY: Keeps status at OUTCOME_SUBMITTED but sets review_decision to CLARIFICATION_REQUESTED with notes.
    """
    assignment = get_object_or_404(RangerAssignment, pk=pk)
    decision = request.POST.get('decision', '').strip()
    review_notes = request.POST.get('review_notes', '').strip()

    if decision not in ['APPROVED', 'REJECTED', 'CLARIFICATION_REQUESTED']:
        messages.error(request, "Invalid outcome review decision.")
        return redirect('reports:detail', pk=assignment.sighting_id)

    if decision in ['REJECTED', 'CLARIFICATION_REQUESTED'] and not review_notes:
        messages.error(request, "Please provide review comments or rationale when rejecting or requesting clarification.")
        return redirect('reports:detail', pk=assignment.sighting_id)

    assignment.review_decision = decision
    assignment.review_notes = review_notes
    assignment.reviewed_by = request.user
    assignment.reviewed_at = timezone.now()

    if decision == 'APPROVED':
        assignment.status = RangerAssignment.STATUS_COMPLETED
        assignment.completed_at = timezone.now()
        assignment.save(update_fields=['status', 'review_decision', 'review_notes', 'reviewed_by', 'reviewed_at', 'completed_at'])
        
        # Free ranger availability
        _refresh_ranger_availability(assignment.ranger)

        # Mark sighting report resolved
        rep = assignment.sighting
        rep.status = SightingReport.STATUS_RESOLVED
        rep.response_status = SightingReport.RESPONSE_RESOLVED
        if review_notes:
            rep.authority_notes = f"Verified: {assignment.get_outcome_display()}. {review_notes}".strip()
        rep.save(update_fields=['status', 'response_status', 'authority_notes'])

        AuditLog.record(
            actor=request.user,
            action='VERIFY_OUTCOME',
            target_type='SightingReport',
            target_id=rep.pk,
            target_repr=f"Incident #{rep.pk}",
            details=f"Approved outcome '{assignment.get_outcome_display()}'. Notes: {review_notes}"
        )

        # Notify Citizen that incident is verified as resolved
        Notification.send(
            recipient=rep.user,
            actor=request.user,
            title="Incident Verified & Resolved",
            message=f"Your snake sighting #{rep.pk} has been officially verified and resolved by the Authority ({assignment.get_outcome_display()}).",
            notification_type=Notification.TYPE_SUCCESS,
            link=reverse('reports:detail', kwargs={'pk': rep.pk})
        )

        # Notify Ranger that outcome was approved
        Notification.send(
            recipient=assignment.ranger,
            actor=request.user,
            title="Outcome Verified & Approved",
            message=f"Your outcome submission for Incident #{rep.pk} was verified and approved by Authority Officer {request.user.profile.display_name}.",
            notification_type=Notification.TYPE_SUCCESS,
            link=reverse('ranger:assignment_detail', kwargs={'pk': assignment.pk})
        )

        messages.success(request, f"Outcome for Incident #{rep.pk} approved. Incident marked resolved.")

    elif decision == 'REJECTED':
        # Revert to AT_LOCATION so ranger can re-inspect or re-submit
        assignment.status = RangerAssignment.STATUS_AT_LOCATION
        assignment.save(update_fields=['status', 'review_decision', 'review_notes', 'reviewed_by', 'reviewed_at'])

        AuditLog.record(
            actor=request.user,
            action='REJECT_OUTCOME',
            target_type='SightingReport',
            target_id=assignment.sighting_id,
            target_repr=f"Incident #{assignment.sighting_id}",
            details=f"Outcome rejected. Reason: {review_notes}"
        )

        Notification.send(
            recipient=assignment.ranger,
            actor=request.user,
            title="Outcome Rejected by Authority",
            message=f"Your outcome submission for Incident #{assignment.sighting_id} was rejected: {review_notes}. Please re-inspect and resubmit.",
            notification_type=Notification.TYPE_DANGER,
            link=reverse('ranger:assignment_detail', kwargs={'pk': assignment.pk})
        )

        messages.warning(request, f"Outcome rejected. Ranger {assignment.ranger.username} has been instructed to re-inspect and follow up.")

    elif decision == 'CLARIFICATION_REQUESTED':
        assignment.save(update_fields=['review_decision', 'review_notes', 'reviewed_by', 'reviewed_at'])

        AuditLog.record(
            actor=request.user,
            action='CLARIFY_OUTCOME',
            target_type='SightingReport',
            target_id=assignment.sighting_id,
            target_repr=f"Incident #{assignment.sighting_id}",
            details=f"Clarification requested: {review_notes}"
        )

        Notification.send(
            recipient=assignment.ranger,
            actor=request.user,
            title="Clarification Requested",
            message=f"Authority requested clarification on Incident #{assignment.sighting_id}: {review_notes}",
            notification_type=Notification.TYPE_WARNING,
            link=reverse('ranger:assignment_detail', kwargs={'pk': assignment.pk})
        )

        messages.info(request, f"Clarification requested from ranger {assignment.ranger.username}.")

    return redirect('reports:detail', pk=assignment.sighting_id)


@login_required
@never_cache
def update_response_status_view(request, pk):
    """Legacy response-status endpoint — now restricted to Authority only.

    Rangers update incidents through the Ranger Console lifecycle
    (/ranger/assignments/<id>/update/) instead of arbitrary status writes.
    """
    report = get_object_or_404(SightingReport, pk=pk)
    profile = getattr(request.user, 'profile', None)
    if not (profile and profile.is_admin):
        raise PermissionDenied("Only the Authority console can change the raw response status here. Rangers must use their assignment workflow.")

    if request.method == 'POST':
        new_status = request.POST.get('response_status')
        if new_status in dict(SightingReport.RESPONSE_STATUS_CHOICES):
            report.response_status = new_status
            if new_status == SightingReport.RESPONSE_RESOLVED:
                report.status = SightingReport.STATUS_RESOLVED
            report.save()
            messages.success(request, f"Response task status updated to '{report.get_response_status_display()}'.")

    return redirect('reports:detail', pk=pk)


def risk_zones_public_view(request):
    """
    Public Community Risk Zones view.
    Displays interactive map with distinct incident clusters categorized into:
    - RED (High Risk: 3+ distinct active incidents)
    - ORANGE (Caution: 1-2 distinct active incidents)
    - YELLOW (Recently Resolved: active cooldown)
    - GREEN (No Recent Active Incidents: cleared retention)
    """
    risk_data = DBSCANHotspotService.compute_community_risk_zones()
    user_lat = 9.9312
    user_lng = 76.2673
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        prof = request.user.profile
        if prof.latitude is not None and prof.longitude is not None:
            try:
                user_lat = float(prof.latitude)
                user_lng = float(prof.longitude)
            except (ValueError, TypeError):
                pass
    return render(request, 'reports/risk_zones.html', {
        'risk_data': risk_data,
        'user_lat': user_lat,
        'user_lng': user_lng
    })


def risk_zones_api(request):
    """JSON API endpoint returning geographic community risk zones for dynamic map refresh and polling."""
    risk_data = DBSCANHotspotService.compute_community_risk_zones()
    risk_data['status'] = 'SUCCESS'
    return JsonResponse(risk_data)



# ---------------------------------------------------------------------------
# Authority geolocation map APIs (used by the dashboard incident map)
# ---------------------------------------------------------------------------

def normalize_confidence_percentage(val):
    """Normalize confidence score to percentage float (0.0 to 100.0) exactly once.

    Semantics:
    - If val is None: returns None
    - If val is float in [0.0, 1.0]: scale once (val * 100.0)
    - If val is float in (1.0, 100.0]: already in percentage scale
    - If val < 0.0 or val > 100.0: invalid/uncalibrated score, returns None
    """
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if f < 0.0 or f > 100.0:
        return None
    if 0.0 < f <= 1.0:
        f = f * 100.0
    return round(f, 1)


def _active_assignment_info(report):
    """Return (assignment, info-dict) for a report's active or latest completed ranger assignment."""
    # Priority 1: Check if report was resolved
    if report.status == SightingReport.STATUS_RESOLVED or report.response_status == SightingReport.RESPONSE_RESOLVED:
        completed_a = report.ranger_assignments.filter(status=RangerAssignment.STATUS_COMPLETED).first()
        ranger_u = completed_a.ranger if completed_a else report.assigned_responder
        return completed_a, {
            'assigned': False,
            'assignment_id': completed_a.pk if completed_a else None,
            'ranger': ranger_u.username if ranger_u else None,
            'ranger_name': ranger_u.profile.display_name if (ranger_u and hasattr(ranger_u, 'profile')) else (ranger_u.username if ranger_u else None),
            'status': 'COMPLETED',
            'status_display': 'Completed',
            'distance_km': completed_a.distance_km if completed_a else None,
            'assigned_at': completed_a.assigned_at.strftime('%b %d, %Y %H:%M') if completed_a else None,
        }

    a = getattr(report, '_prefetched_active', None)
    if a is None:
        a = report.ranger_assignments.filter(
            status__in=RangerAssignment.ACTIVE_STATUSES).first()
    if a:
        return a, {
            'assigned': True,
            'assignment_id': a.pk,
            'ranger': a.ranger.username,
            'ranger_name': a.ranger.profile.display_name if hasattr(a.ranger, 'profile') else a.ranger.username,
            'status': a.status,
            'status_display': a.get_status_display(),
            'distance_km': a.distance_km,
            'assigned_at': a.assigned_at.strftime('%b %d, %Y %H:%M'),
        }

    completed_a = report.ranger_assignments.filter(status=RangerAssignment.STATUS_COMPLETED).first()
    if completed_a:
        ranger_u = completed_a.ranger
        return completed_a, {
            'assigned': False,
            'assignment_id': completed_a.pk,
            'ranger': ranger_u.username,
            'ranger_name': ranger_u.profile.display_name if hasattr(ranger_u, 'profile') else ranger_u.username,
            'status': 'COMPLETED',
            'status_display': 'Completed',
            'distance_km': completed_a.distance_km,
            'assigned_at': completed_a.assigned_at.strftime('%b %d, %Y %H:%M'),
        }

    return None, {
        'assigned': False,
        'ranger': None,
        'status': 'UNASSIGNED',
        'status_display': 'Unassigned',
        'distance_km': None,
        'assigned_at': None,
    }


@login_required
@authority_required
@never_cache
def authority_map_view(request):
    """Dedicated Authority Operations Map page (/reports/map/).

    Server-side permission enforced via @authority_required — Citizens and
    Rangers receive 403/redirect even if they type the URL manually. The map
    itself loads real DB report markers through the existing
    api/map-reports/ endpoint (no fake/hard-coded data).
    """
    from django.db.models import Count, Max, Q
    all_reports = SightingReport.objects.all()

    # Geographical validity check
    geo_reports = all_reports.exclude(latitude__isnull=True).exclude(longitude__isnull=True).exclude(latitude=0, longitude=0)
    geo_count = geo_reports.count()
    unplotted_count = all_reports.count() - geo_count

    # Unassigned venomous: either HIGHLY/MODERATE or venomous=True, and response_status=UNASSIGNED, not RESOLVED
    unassigned_venomous = geo_reports.filter(
        Q(venom_category__in=[SightingReport.VENOM_HIGHLY, SightingReport.VENOM_MODERATE]) | Q(venomous=True),
        response_status=SightingReport.RESPONSE_UNASSIGNED
    ).exclude(status=SightingReport.STATUS_RESOLVED).exclude(response_status=SightingReport.RESPONSE_RESOLVED).count()

    active = RangerAssignment.objects.filter(status__in=RangerAssignment.ACTIVE_STATUSES).count()
    completed = RangerAssignment.objects.filter(status=RangerAssignment.STATUS_COMPLETED).count()

    context = {
        'geo_report_count': geo_count,
        'unassigned_venomous': unassigned_venomous,
        'active_assignments': active,
        'completed_assignments': completed,
        'unplotted_count': unplotted_count,
        'page_title': 'Authority Operations Map',
    }
    return render(request, 'reports/authority_map.html', context)


@login_required
@authority_required
@never_cache
def authority_map_reports_api(request):
    """JSON list of individual snake report markers for the Authority map.

    Returns one entry per report that has usable coordinates — never fake or
    hard-coded data. Includes assignment state so markers can be colour-coded
    (unassigned / active response / completed). Minimal fields only: no
    private citizen information beyond what Authority legitimately monitors.
    """
    def _is_valid_coord(lat, lng):
        try:
            if lat is None or lng is None:
                return False
            lat = float(lat)
            lng = float(lng)
            return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0 and not (lat == 0.0 and lng == 0.0)
        except (ValueError, TypeError):
            return False

    raw_reports = SightingReport.objects.select_related('user').prefetch_related(
        'ranger_assignments__ranger__profile')
    all_reports_list = list(raw_reports)
    reports = [r for r in all_reports_list if _is_valid_coord(r.latitude, r.longitude)]
    unplotted_count = len(all_reports_list) - len(reports)

    # Group assignments per report once (avoid N queries)
    active_by_report = {}
    for a in RangerAssignment.objects.filter(
            status__in=RangerAssignment.ACTIVE_STATUSES).select_related('ranger__profile'):
        active_by_report.setdefault(a.sighting_id, a)
    resolved_ids = set(r.id for r in reports if r.status == SightingReport.STATUS_RESOLVED or r.response_status == SightingReport.RESPONSE_RESOLVED or r.ranger_assignments.filter(
        status=RangerAssignment.STATUS_COMPLETED).exists())

    unassigned_venomous_count = 0
    active_assignments_count = 0
    completed_assignments_count = 0

    data = []
    for r in reports:
        a = active_by_report.get(r.id)
        if r.id in resolved_ids or r.response_status == SightingReport.RESPONSE_RESOLVED or r.status == SightingReport.STATUS_RESOLVED:
            dispatch_state = 'COMPLETED'
            completed_assignments_count += 1
            assign = {'assigned': False, 'ranger': None, 'status': 'COMPLETED',
                      'status_display': 'Completed'}
        elif a:
            dispatch_state = 'ACTIVE'
            active_assignments_count += 1
            assign = {
                'assigned': True,
                'assignment_id': a.pk,
                'ranger': a.ranger.username,
                'ranger_name': a.ranger.profile.display_name if hasattr(a.ranger, 'profile') else a.ranger.username,
                'status': a.status,
                'status_display': a.get_status_display(),
                'distance_km': a.distance_km,
                'assigned_at': a.assigned_at.strftime('%b %d, %Y %H:%M'),
            }
        else:
            dispatch_state = 'UNASSIGNED'
            assign = {'assigned': False, 'ranger': None, 'status': 'UNASSIGNED',
                      'status_display': 'Unassigned'}
            if r.is_venomous and r.status != SightingReport.STATUS_RESOLVED and r.response_status != SightingReport.RESPONSE_RESOLVED:
                unassigned_venomous_count += 1

        orig_img_url = None
        if r.original_image and hasattr(r.original_image, 'url'):
            try:
                orig_img_url = r.original_image.url
            except Exception:
                orig_img_url = None

        proc_img_url = None
        if r.processed_image and hasattr(r.processed_image, 'url'):
            try:
                proc_img_url = r.processed_image.url
            except Exception:
                proc_img_url = None

        img_url = orig_img_url or proc_img_url

        data.append({
            'id': r.id,
            'report_reference': r.report_reference,
            'title': r.title,
            'latitude': float(r.latitude),
            'longitude': float(r.longitude),
            'location_name': r.location_name,
            'venom_status': r.venom_category,
            'is_venomous': r.is_venomous,
            'species': r.species_predicted or '',
            'confidence': normalize_confidence_percentage(r.venom_confidence),
            'created_at': r.created_at.strftime('%b %d, %Y %H:%M'),
            'report_status': r.status,
            'dispatch_state': dispatch_state,
            'assignment': assign,
            'original_image_url': orig_img_url,
            'processed_image_url': proc_img_url,
            'image_url': img_url,
        })

    return JsonResponse({
        'reports': data,
        'counts': {
            'geo_report_count': len(data),
            'unassigned_venomous': unassigned_venomous_count,
            'active_assignments': active_assignments_count,
            'completed_assignments': completed_assignments_count,
            'unplotted_count': unplotted_count,
        }
    })


@login_required
@authority_required
@never_cache
def authority_report_panel_api(request, pk):
    """Full detail payload for the selected report marker + assignable rangers.

    Rangers offered here are location-filtered server-side via
    get_candidate_rangers() — only RANGER-role, AVAILABLE users registered
    in/near THIS report's location (Haversine distance when coordinates exist,
    sorted nearest-first). The whole ranger DB is never exposed.
    """
    report = get_object_or_404(SightingReport, pk=pk)
    _, assign = _active_assignment_info(report)

    candidates = []
    for c in get_candidate_rangers(report, only_available=True):
        prof = c['profile']
        candidates.append({
            'id': c['user'].pk,
            'username': c['user'].username,
            'name': prof.display_name,
            'location': prof.registered_location or prof.assigned_region or 'Base not set',
            'distance_km': c['distance_km'],
            'availability': prof.availability,
        })

    orig_img_url = None
    if report.original_image and hasattr(report.original_image, 'url'):
        try:
            orig_img_url = report.original_image.url
        except Exception:
            orig_img_url = None

    proc_img_url = None
    if report.processed_image and hasattr(report.processed_image, 'url'):
        try:
            proc_img_url = report.processed_image.url
        except Exception:
            proc_img_url = None

    display_img_url = orig_img_url or proc_img_url

    payload = dict(assign)
    payload.update({
        'id': report.id,
        'report_reference': report.report_reference,
        'title': report.title,
        'original_image_url': orig_img_url,
        'processed_image_url': proc_img_url,
        'image_url': display_img_url,
        'snake_status': report.get_venom_category_display() if report.venom_category else 'Pending Verification',
        'is_venomous': report.is_venomous,
        'species': report.species_predicted or '',
        'confidence': normalize_confidence_percentage(report.venom_confidence),
        'raw_confidence': report.venom_confidence,
        'reported_at': report.created_at.strftime('%b %d, %Y, %I:%M %p'),
        'location_name': report.location_name,
        'latitude': float(report.latitude),
        'longitude': float(report.longitude),
        'notes': report.notes or '',
        'detail_url': f"/reports/{report.id}/",
        'candidates': candidates,
    })
    return JsonResponse(payload)

