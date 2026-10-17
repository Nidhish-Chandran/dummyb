from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from accounts.decorators import authority_required
from .models import Hospital, EmergencySOSEvent

DEFAULT_HOSPITALS = [
    {
        'name': 'Government Medical College Hospital & Trauma Center',
        'phone_number': '108 / +91 484 2555555',
        'address': 'Kalamassery Main Road, Sector 1',
        'latitude': 10.0456,
        'longitude': 76.3212,
        'anti_venom_available': True,
        'anti_venom_stock_vials': 85,
        'has_icu': True,
        'operating_hours': '24/7 Trauma Emergency Care'
    },
    {
        'name': 'District Anti-Venom Specialty Emergency Clinic',
        'phone_number': '+91 484 2360001',
        'address': 'MG Road Bypass, Near General Hospital',
        'latitude': 9.9723,
        'longitude': 76.2801,
        'anti_venom_available': True,
        'anti_venom_stock_vials': 40,
        'has_icu': True,
        'operating_hours': '24/7 Emergency Care'
    },
    {
        'name': 'Lakeside Wildlife & Toxicology Hospital',
        'phone_number': '+91 484 2701100',
        'address': 'NH 66 Bypass, Nettoor Junction',
        'latitude': 9.9211,
        'longitude': 76.3054,
        'anti_venom_available': True,
        'anti_venom_stock_vials': 60,
        'has_icu': True,
        'operating_hours': '24/7 Emergency Care'
    }
]

def assistance_view(request):
    """
    Snakebite Emergency Support view.
    Computes nearest hospitals with anti-venom stock using Haversine formula.
    """
    # Seed default sample hospitals if DB is empty
    if Hospital.objects.count() == 0:
        for h in DEFAULT_HOSPITALS:
            Hospital.objects.create(**h)

    try:
        user_lat = float(request.GET.get('lat', 9.9312))
        user_lng = float(request.GET.get('lng', 76.2673))
    except (ValueError, TypeError):
        user_lat = 9.9312
        user_lng = 76.2673

    hospitals = list(Hospital.objects.all())

    # Compute Haversine distance for each hospital
    for h in hospitals:
        h.distance_km = h.distance_from(user_lat, user_lng)

    # Sort by nearest distance
    hospitals.sort(key=lambda x: x.distance_km)

    return render(request, 'emergency/assistance.html', {
        'hospitals': hospitals,
        'user_lat': user_lat,
        'user_lng': user_lng
    })


@require_POST
def sos_trigger_api(request):
    """
    Real-time Emergency SOS broadcast API.
    Persists distress incident with coordinates, phone, and reporter into database.
    Prevents duplicate activations within 2 minutes.
    """
    try:
        lat = float(request.POST.get('latitude', 0))
        lng = float(request.POST.get('longitude', 0))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'ERROR', 'message': 'Invalid latitude or longitude provided.'}, status=400)

    if lat == 0 and lng == 0:
        return JsonResponse({'status': 'ERROR', 'message': 'GPS coordinates are required to log Emergency SOS.'}, status=400)

    phone = request.POST.get('phone_number', '').strip()
    location_name = request.POST.get('location', 'Current GPS Location').strip()
    description = request.POST.get('description', 'Immediate snakebite distress assistance requested.').strip()
    user = request.user if request.user.is_authenticated else None

    # Duplicate throttle: Check if an identical active SOS was created in the last 2 minutes
    cutoff_2min = timezone.now() - timedelta(minutes=2)
    recent_sos = EmergencySOSEvent.objects.filter(
        created_at__gte=cutoff_2min,
        status=EmergencySOSEvent.STATUS_ACTIVE,
        latitude__range=(lat - 0.001, lat + 0.001),
        longitude__range=(lng - 0.001, lng + 0.001)
    ).first()

    if recent_sos:
        return JsonResponse({
            'status': 'SUCCESS',
            'duplicate': True,
            'event_id': recent_sos.id,
            'message': 'Active Emergency SOS already registered for this location. Authority operations are actively monitoring.',
            'latitude': lat,
            'longitude': lng,
            'emergency_contacts': ['108 (National Emergency Ambulance)', '1926 (Forest Department Wildlife Response)']
        })

    sos_event = EmergencySOSEvent.objects.create(
        user=user,
        phone_number=phone,
        latitude=lat,
        longitude=lng,
        location_name=location_name,
        emergency_type='SNAKEBITE_DISTRESS',
        description=description,
        status=EmergencySOSEvent.STATUS_ACTIVE
    )

    return JsonResponse({
        'status': 'SUCCESS',
        'event_id': sos_event.id,
        'message': 'Emergency SOS logged into VenomWatch Operations Console. Please call the direct emergency hotlines below immediately.',
        'latitude': lat,
        'longitude': lng,
        'emergency_contacts': [
            '108 (State Emergency Ambulance & Trauma Hotline)',
            '1926 (Forest Department Wildlife Rescue Center)'
        ]
    })


@login_required
@authority_required
def sos_feed_api(request):
    """
    JSON feed of active and recent SOS distress events for Authority operations monitor.
    """
    events = EmergencySOSEvent.objects.all()[:20]
    data = []
    for ev in events:
        data.append({
            'id': ev.id,
            'user': ev.user.username if ev.user else 'Anonymous Citizen',
            'phone_number': ev.phone_number or 'Not provided',
            'latitude': ev.latitude,
            'longitude': ev.longitude,
            'location_name': ev.location_name,
            'emergency_type': ev.emergency_type,
            'status': ev.status,
            'status_display': ev.get_status_display(),
            'created_at': ev.created_at.strftime('%b %d, %Y %H:%M'),
            'acknowledged_by': ev.acknowledged_by.username if ev.acknowledged_by else None,
            'resolution_notes': ev.resolution_notes or '',
        })
    return JsonResponse({'sos_events': data})


@login_required
@authority_required
@require_POST
def sos_acknowledge_api(request, pk):
    """
    Authority acknowledges or resolves an active Emergency SOS distress event.
    """
    sos_event = get_object_or_404(EmergencySOSEvent, pk=pk)
    action = request.POST.get('action', 'ACKNOWLEDGE')
    notes = request.POST.get('notes', '').strip()

    if action == 'RESOLVE':
        sos_event.status = EmergencySOSEvent.STATUS_RESOLVED
        sos_event.resolved_at = timezone.now()
        sos_event.resolution_notes = notes
    else:
        sos_event.status = EmergencySOSEvent.STATUS_ACKNOWLEDGED
        sos_event.acknowledged_by = request.user
        sos_event.acknowledged_at = timezone.now()
        if notes:
            sos_event.resolution_notes = notes

    sos_event.save()
    return JsonResponse({
        'success': True,
        'event_id': sos_event.id,
        'status': sos_event.status,
        'status_display': sos_event.get_status_display(),
        'message': f"SOS Event #{sos_event.id} marked as {sos_event.get_status_display()}."
    })
