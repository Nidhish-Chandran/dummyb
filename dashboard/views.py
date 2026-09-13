from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from reports.models import SightingReport
from hotspots.services import DBSCANHotspotService
from django.contrib.auth.decorators import login_required
from accounts.decorators import authority_required
from django.views.decorators.cache import never_cache

def landing_page_view(request):
    """
    Public landing page for unauthenticated visitors.
    If user is authenticated, redirect to appropriate dashboard.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_authority:
            return redirect('dashboard:home')
        return redirect('reports:list')
    
    return render(request, 'landing.html')


@login_required
@authority_required
@never_cache
def dashboard_home_view(request):
    """
    Main Surveillance & Authority Dashboard view.
    Restricted to Wildlife Authorities and Authorized Staff.
    Aggregates sighting statistics, DBSCAN high-alert clusters, duplicate/spam flags,
    and active GIS map surveillance data.
    """
    all_reports = SightingReport.objects.all()
    total_sightings = all_reports.count()
    
    # 48-hour active sightings
    cutoff_48h = timezone.now() - timedelta(hours=48)
    active_reports = all_reports.filter(created_at__gte=cutoff_48h)
    active_count = active_reports.count()

    # Venomous breakdown
    venomous_reports = all_reports.filter(venom_category__in=[SightingReport.VENOM_HIGHLY, SightingReport.VENOM_MODERATE])
    venomous_count = venomous_reports.count()

    # Pending authority verification count
    pending_count = all_reports.filter(status=SightingReport.STATUS_PENDING).count()

    # Duplicate & Spam Flag counts
    duplicate_count = all_reports.filter(duplicate_flag=True).count()
    spam_count = all_reports.filter(spam_flag=True).count()
    unassigned_count = all_reports.filter(response_status=SightingReport.RESPONSE_UNASSIGNED).count()

    # DBSCAN spatial clustering
    hotspot_data = DBSCANHotspotService.compute_hotspots(eps_km=1.0, min_samples=2, hours=48)

    # Recent 6 sightings
    recent_sightings = all_reports[:6]

    return render(request, 'dashboard/index.html', {
        'total_sightings': total_sightings,
        'active_count': active_count,
        'venomous_count': venomous_count,
        'pending_count': pending_count,
        'duplicate_count': duplicate_count,
        'spam_count': spam_count,
        'unassigned_count': unassigned_count,
        'hotspot_data': hotspot_data,
        'recent_sightings': recent_sightings,
        'reports': all_reports[:50] # Detailed GIS map dataset
    })
