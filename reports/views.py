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
from accounts.models import UserProfile
from accounts.decorators import authority_required
from .models import RangerAssignment
from .dispatch import get_candidate_rangers, haversine_km
from django.views.decorators.cache import never_cache


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
                
                report.ai_detected = report.snake_detected
                report.species_predicted = ai_results.get('species', 'Snake')
                report.venom_category = ai_results.get('venom_category', 'NON_VENOMOUS')
                report.ai_confidence = report.venom_confidence if report.venom_confidence is not None else report.snake_confidence
                report.model_1_name = ai_results.get('model_1', 'venomwatch_cnn2_final (CNN)')
                report.model_2_name = ai_results.get('model_2', 'venom_watch_cnn2_keras')
                
                report.save()
            except Exception as e:
                messages.warning(request, f"Report logged. AI processing note: {str(e)}")

            # 2. Trigger Duplicate Proximity & Spam Rate-limit Evaluator
            try:
                report = DuplicateSpamDetectionService.evaluate_and_flag(report)
                if report.duplicate_flag:
                    messages.info(request, "Note: This report has been flagged for authority review as a potential duplicate of a recent sighting.")
                if report.spam_flag:
                    messages.warning(request, "Note: Submission rate limit flagged for administrative review.")
            except Exception as e:
                pass

            messages.success(request, f"Sighting reported successfully! AI Result: {report.species_predicted} ({report.get_venom_category_display()}).")
            return redirect('reports:detail', pk=report.pk)
        else:
            messages.error(request, "Error creating report. Please check the required form fields.")
    else:
        initial_data = {
            'latitude': 9.9312,
            'longitude': 76.2673,
            'location_name': 'Kochi Sector 4'
        }
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

    # Authority assignment panel data (location-filtered rangers — never the whole DB)
    active_assignment = None
    candidate_rangers = []
    assignment_history = []
    if is_authority:
        active_assignment = report.ranger_assignments.filter(
            status__in=RangerAssignment.ACTIVE_STATUSES).first()
        candidate_rangers = get_candidate_rangers(report, only_available=True)
        assignment_history = report.ranger_assignments.all()[:10]

    return render(request, 'reports/detail.html', {
        'report': report,
        'is_authority': is_authority,
        'is_assigned_responder': is_assigned_responder,
        'responders': responders,
        'active_assignment': active_assignment,
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
        new_status = request.POST.get('status')
        notes = request.POST.get('authority_notes', '')

        if new_status in dict(SightingReport.STATUS_CHOICES):
            report.status = new_status
            report.verified_by = request.user
            report.authority_notes = notes
            report.save()
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

    if request.method == 'POST':
        ranger_id = request.POST.get('ranger_id') or request.POST.get('responder_id')
        if ranger_id:
            ranger_user = get_object_or_404(User, pk=ranger_id)
            prof = getattr(ranger_user, 'profile', None)
            if prof is None or prof.effective_role != UserProfile.ROLE_RANGER:
                return _fail("Selected user is not a registered Ranger.")

            # Location guard: the chosen ranger must be relevant to THIS report
            candidates = get_candidate_rangers(report, only_available=False)
            if not any(c['user'].pk == ranger_user.pk for c in candidates):
                return _fail(
                    "Access Denied: That ranger is not registered in or near this report's location.")
            if prof.availability != UserProfile.AVAILABILITY_AVAILABLE:
                return _fail(
                    f"{ranger_user.username} is currently {prof.get_availability_display()} and cannot take a new incident.")

            # Cancel any existing active assignment for this report
            for prev in report.ranger_assignments.filter(status__in=RangerAssignment.ACTIVE_STATUSES):
                prev.status = RangerAssignment.STATUS_CANCELLED
                prev.save(update_fields=['status'])
                _refresh_ranger_availability(prev.ranger)

            dist = None
            if prof.latitude is not None and prof.longitude is not None:
                dist = haversine_km(prof.latitude, prof.longitude, report.latitude, report.longitude)

            RangerAssignment.objects.create(
                sighting=report,
                ranger=ranger_user,
                assigned_by=request.user,
                distance_km=dist,
                status=RangerAssignment.STATUS_ASSIGNED,
            )
            report.assigned_responder = ranger_user
            report.response_status = SightingReport.RESPONSE_ASSIGNED
            report.save(update_fields=['assigned_responder', 'response_status'])
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
    if request.method == 'POST':
        if not assignment.is_active:
            messages.info(request, "This assignment is already closed.")
        else:
            assignment.status = RangerAssignment.STATUS_CANCELLED
            assignment.save(update_fields=['status'])
            _refresh_ranger_availability(assignment.ranger)
            rep = assignment.sighting
            still_active = rep.ranger_assignments.filter(status__in=RangerAssignment.ACTIVE_STATUSES).first()
            if still_active is None:
                rep.assigned_responder = None
                rep.response_status = SightingReport.RESPONSE_UNASSIGNED
                rep.save(update_fields=['assigned_responder', 'response_status'])
            messages.success(request, f"Assignment #{assignment.pk} cancelled.")
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
    Displays aggregated risk level (GREEN / YELLOW / RED) without exposing exact citizen coordinates or individual markers.
    Rule: 0 in 24h -> GREEN, 1-5 -> YELLOW, >5 -> RED.
    """
    risk_data = DBSCANHotspotService.compute_community_risk_zones(hours=24)
    return render(request, 'reports/risk_zones.html', {'risk_data': risk_data})


# ---------------------------------------------------------------------------
# Authority geolocation map APIs (used by the dashboard incident map)
# ---------------------------------------------------------------------------

def _active_assignment_info(report):
    """Return (assignment, info-dict) for a report's active ranger assignment."""
    a = getattr(report, '_prefetched_active', None)
    if a is None:
        a = report.ranger_assignments.filter(
            status__in=RangerAssignment.ACTIVE_STATUSES).first()
    if not a:
        return None, {
            'assigned': False,
            'ranger': None,
            'status': 'UNASSIGNED',
            'status_display': 'Unassigned',
            'distance_km': None,
            'assigned_at': None,
        }
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
    from django.db.models import Count, Max
    geo_count = SightingReport.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).count()
    unassigned_venomous = SightingReport.objects.filter(
        venomous=True, ranger_assignments__isnull=True
    ).exclude(latitude__isnull=True).count()
    active = RangerAssignment.objects.filter(status__in=RangerAssignment.ACTIVE_STATUSES).count()
    completed = RangerAssignment.objects.filter(status=RangerAssignment.STATUS_COMPLETED).count()
    context = {
        'geo_report_count': geo_count,
        'unassigned_venomous': unassigned_venomous,
        'active_assignments': active,
        'completed_assignments': completed,
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
    reports = SightingReport.objects.select_related('user').prefetch_related(
        'ranger_assignments__ranger__profile')
    reports = [r for r in reports if r.latitude is not None and r.longitude is not None]

    # Group assignments per report once (avoid N queries)
    active_by_report = {}
    for a in RangerAssignment.objects.filter(
            status__in=RangerAssignment.ACTIVE_STATUSES).select_related('ranger__profile'):
        active_by_report.setdefault(a.sighting_id, a)
    resolved_ids = set(r.id for r in reports if r.ranger_assignments.filter(
        status=RangerAssignment.STATUS_COMPLETED).exists())

    data = []
    for r in reports:
        a = active_by_report.get(r.id)
        if a:
            dispatch_state = 'ACTIVE'
            assign = {
                'assigned': True,
                'ranger': a.ranger.username,
                'ranger_name': a.ranger.profile.display_name if hasattr(a.ranger, 'profile') else a.ranger.username,
                'status': a.status,
                'status_display': a.get_status_display(),
                'distance_km': a.distance_km,
                'assigned_at': a.assigned_at.strftime('%b %d, %Y %H:%M'),
            }
        elif r.id in resolved_ids or r.response_status == SightingReport.RESPONSE_RESOLVED:
            dispatch_state = 'COMPLETED'
            assign = {'assigned': False, 'ranger': None, 'status': 'COMPLETED',
                      'status_display': 'Completed'}
        else:
            dispatch_state = 'UNASSIGNED'
            assign = {'assigned': False, 'ranger': None, 'status': 'UNASSIGNED',
                      'status_display': 'Unassigned'}
        data.append({
            'id': r.id,
            'title': r.title,
            'latitude': r.latitude,
            'longitude': r.longitude,
            'location_name': r.location_name,
            'venom_status': r.venom_category,
            'is_venomous': r.is_venomous,
            'species': r.species_predicted or '',
            'confidence': round((r.venom_confidence or 0) * 100),
            'created_at': r.created_at.strftime('%b %d, %Y %H:%M'),
            'report_status': r.status,
            'dispatch_state': dispatch_state,
            'assignment': assign,
        })
    return JsonResponse({'reports': data})


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

    payload = dict(assign)
    payload.update({
        'id': report.id,
        'title': report.title,
        'image_url': report.original_image.url if report.original_image else None,
        'snake_status': report.get_venom_category_display(),
        'is_venomous': report.is_venomous,
        'species': report.species_predicted or '',
        'confidence': round((report.venom_confidence or 0) * 100),
        'reported_at': report.created_at.strftime('%b %d, %Y, %I:%M %p'),
        'location_name': report.location_name,
        'latitude': report.latitude,
        'longitude': report.longitude,
        'notes': report.notes or '',
        'detail_url': f"/reports/{report.id}/",
        'candidates': candidates,
    })
    return JsonResponse(payload)
