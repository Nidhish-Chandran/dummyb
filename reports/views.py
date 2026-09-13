from django.shortcuts import render, redirect, get_object_or_404
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
from accounts.decorators import authority_required
from django.views.decorators.cache import never_cache

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
                report.model_1_name = ai_results.get('model_1', 'Snake Detection.v2 YOLOv8')
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
    is_authority = hasattr(user, 'profile') and user.profile.is_authority
    is_responder = hasattr(user, 'profile') and user.profile.is_responder and not is_authority

    if is_authority:
        reports = SightingReport.objects.all()
    elif is_responder:
        reports = SightingReport.objects.filter(Q(assigned_responder=user) | Q(response_status=SightingReport.RESPONSE_UNASSIGNED))
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
    responders = User.objects.filter(profile__role__in=['responder', 'authority']) if is_authority else []

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
    is_authority = hasattr(user, 'profile') and user.profile.is_authority
    is_assigned_responder = (report.assigned_responder == user)

    if not is_authority and not is_assigned_responder and report.user != user:
        raise PermissionDenied("Access Denied: You are not authorized to view other citizens' detailed report information or coordinates.")

    responders = User.objects.filter(profile__role__in=['responder', 'authority']) if is_authority else []

    return render(request, 'reports/detail.html', {
        'report': report,
        'is_authority': is_authority,
        'is_assigned_responder': is_assigned_responder,
        'responders': responders
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
    """Authority endpoint to assign a volunteer/responder to a reported incident."""
    report = get_object_or_404(SightingReport, pk=pk)
    if request.method == 'POST':
        responder_id = request.POST.get('responder_id')
        if responder_id:
            responder_user = get_object_or_404(User, pk=responder_id)
            report.assigned_responder = responder_user
            report.response_status = SightingReport.RESPONSE_ASSIGNED
            report.save()
            messages.success(request, f"Incident assigned to responder: {responder_user.username}")
        else:
            report.assigned_responder = None
            report.response_status = SightingReport.RESPONSE_UNASSIGNED
            report.save()
            messages.info(request, "Incident responder unassigned.")

    return redirect('reports:detail', pk=pk)


@login_required
@never_cache
def update_response_status_view(request, pk):
    """Endpoint for assigned responders or authority to update rescue response status."""
    report = get_object_or_404(SightingReport, pk=pk)
    user = request.user
    is_authority = hasattr(user, 'profile') and user.profile.is_authority
    is_assigned = (report.assigned_responder == user)

    if not is_authority and not is_assigned:
        raise PermissionDenied("Only the assigned responder or wildlife authority can update response status.")

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
