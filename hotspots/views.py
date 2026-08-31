from django.shortcuts import render
from django.http import JsonResponse
from .services import DBSCANHotspotService

from django.contrib.auth.decorators import login_required
from accounts.decorators import authority_required
from django.views.decorators.cache import never_cache

@login_required
@authority_required
@never_cache
def hotspots_view(request):
    """Render Hotspot Radar page with interactive Leaflet map and cluster cards."""
    hotspot_data = DBSCANHotspotService.compute_hotspots(eps_km=1.0, min_samples=2, hours=48)
    return render(request, 'hotspots/view.html', {
        'hotspot_data': hotspot_data
    })

@login_required
@authority_required
@never_cache
def hotspots_api_view(request):
    """JSON API endpoint returning active DBSCAN spatial clusters."""
    hours = int(request.GET.get('hours', 48))
    eps_km = float(request.GET.get('eps', 1.0))
    hotspot_data = DBSCANHotspotService.compute_hotspots(eps_km=eps_km, min_samples=2, hours=hours)
    return JsonResponse(hotspot_data)

