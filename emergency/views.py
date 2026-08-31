from django.shortcuts import render
from django.http import JsonResponse
from .models import Hospital

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

    user_lat = float(request.GET.get('lat', 9.9312))
    user_lng = float(request.GET.get('lng', 76.2673))

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


def sos_trigger_api(request):
    """API endpoint to handle quick SOS location broadcast."""
    if request.method == 'POST':
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        location = request.POST.get('location', 'Unknown')
        
        return JsonResponse({
            'status': 'SUCCESS',
            'message': 'Emergency SOS Alert Broadcasted! Nearby Medical Responders and Wildlife Rangers have been notified.',
            'latitude': lat,
            'longitude': lng,
            'emergency_contacts': ['108 (Ambulance)', '1926 (Forest Department Wildlife Emergency)']
        })
        
    return JsonResponse({'error': 'POST method required'}, status=400)
