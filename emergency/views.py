from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Sum
from accounts.decorators import authority_required, admin_required
from .models import Hospital, EmergencySOSEvent
from .forms import HospitalForm

def assistance_view(request):
    """
    Emergency Support & Hospital Directory view.
    Retrieves Authority-managed hospital records and sorts by geodesic distance
    from the citizen's detected or provided coordinates.
    Never injects hardcoded sample hospitals.
    """
    user_lat = None
    user_lng = None
    location_detected = False

    raw_lat = request.GET.get('lat')
    raw_lng = request.GET.get('lng')

    if raw_lat and raw_lng:
        try:
            val_lat = float(raw_lat)
            val_lng = float(raw_lng)
            if -90.0 <= val_lat <= 90.0 and -180.0 <= val_lng <= 180.0:
                user_lat = round(val_lat, 6)
                user_lng = round(val_lng, 6)
                location_detected = True
        except (ValueError, TypeError):
            pass

    # If coordinates not passed in GET, check user profile
    if user_lat is None and request.user.is_authenticated and hasattr(request.user, 'profile'):
        prof = request.user.profile
        if prof.latitude is not None and prof.longitude is not None:
            user_lat = float(prof.latitude)
            user_lng = float(prof.longitude)
            location_detected = True

    display_lat = user_lat if user_lat is not None else 9.9312
    display_lng = user_lng if user_lng is not None else 76.2673

    hospitals_qs = Hospital.objects.all()
    hospitals = []

    for h in hospitals_qs:
        if h.latitude is not None and h.longitude is not None:
            if user_lat is not None and user_lng is not None:
                h.distance_km = h.distance_from(user_lat, user_lng)
            else:
                h.distance_km = None
            hospitals.append(h)

    # Sort nearest first if distance calculated
    if user_lat is not None and user_lng is not None:
        hospitals.sort(key=lambda x: (x.distance_km is None, x.distance_km or 999999))

    return render(request, 'emergency/assistance.html', {
        'hospitals': hospitals,
        'user_lat': display_lat,
        'user_lng': display_lng,
        'has_user_coords': location_detected
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


# ==============================================================================
# Platform Admin Hospital & Anti-Venom Management
# ==============================================================================

@login_required
@admin_required
def admin_hospital_manage_view(request):
    """
    Platform Admin: Manage registered medical facilities, emergency departments,
    and anti-venom vial inventory records.
    """
    form = HospitalForm()

    if request.method == 'POST':
        action = request.POST.get('action', 'add_hospital').strip()
        if action == 'add_hospital':
            form = HospitalForm(request.POST)
            if form.is_valid():
                hospital = form.save(commit=False)
                hospital.updated_by = request.user
                hospital.stock_last_updated = timezone.now()
                hospital.save()
                messages.success(
                    request,
                    f"Hospital '{hospital.name}' in {hospital.district or 'district'} successfully registered "
                    f"with {hospital.anti_venom_stock_vials} anti-venom vials."
                )
                return redirect('emergency:hospital_manage')
            else:
                messages.error(request, "Failed to register hospital. Please correct the validation errors below.")

    # Search & filters
    search_q = request.GET.get('q', '').strip()
    district_filter = request.GET.get('district', '').strip()
    av_filter = request.GET.get('av', '').strip().lower()
    icu_filter = request.GET.get('icu', '').strip().lower()

    hospitals_qs = Hospital.objects.select_related('updated_by').all().order_by('district', 'name')

    if search_q:
        hospitals_qs = hospitals_qs.filter(
            Q(name__icontains=search_q) |
            Q(address__icontains=search_q) |
            Q(district__icontains=search_q) |
            Q(phone_number__icontains=search_q) |
            Q(anti_venom_notes__icontains=search_q)
        )
    if district_filter:
        hospitals_qs = hospitals_qs.filter(district__iexact=district_filter)
    if av_filter == 'available':
        hospitals_qs = hospitals_qs.filter(anti_venom_available=True)
    elif av_filter == 'unavailable':
        hospitals_qs = hospitals_qs.filter(anti_venom_available=False)
    if icu_filter == 'yes':
        hospitals_qs = hospitals_qs.filter(has_icu=True)
    elif icu_filter == 'no':
        hospitals_qs = hospitals_qs.filter(has_icu=False)

    # All unique districts for filter dropdown
    all_districts = Hospital.objects.exclude(district='').values_list('district', flat=True).distinct().order_by('district')

    # Aggregated metrics from real database
    total_hospitals = Hospital.objects.count()
    hospitals_with_av = Hospital.objects.filter(anti_venom_available=True).count()
    total_vials = Hospital.objects.filter(anti_venom_available=True).aggregate(total=Sum('anti_venom_stock_vials'))['total'] or 0
    hospitals_with_icu = Hospital.objects.filter(has_icu=True).count()
    hospitals_with_ed = Hospital.objects.filter(emergency_department=True).count()

    return render(request, 'emergency/hospital_manage.html', {
        'form': form,
        'hospitals': hospitals_qs,
        'districts': all_districts,
        'stats': {
            'total_hospitals': total_hospitals,
            'hospitals_with_av': hospitals_with_av,
            'total_vials': total_vials,
            'hospitals_with_icu': hospitals_with_icu,
            'hospitals_with_ed': hospitals_with_ed,
        },
        'filters': {
            'q': search_q,
            'district': district_filter,
            'av': av_filter,
            'icu': icu_filter,
        }
    })


@login_required
@admin_required
def admin_hospital_edit_view(request, pk):
    """
    Platform Admin: Edit hospital operational parameters, coordinates,
    and anti-venom inventory details.
    """
    hospital = get_object_or_404(Hospital, pk=pk)

    if request.method == 'POST':
        form = HospitalForm(request.POST, instance=hospital)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.stock_last_updated = timezone.now()
            updated.save()
            messages.success(request, f"Hospital record '{updated.name}' updated successfully.")
            return redirect('emergency:hospital_manage')
        else:
            messages.error(request, "Failed to update hospital. Please check the form errors below.")
    else:
        form = HospitalForm(instance=hospital)

    return render(request, 'emergency/hospital_edit.html', {
        'form': form,
        'hospital': hospital
    })


@login_required
@admin_required
@require_POST
def admin_hospital_delete_view(request, pk):
    """
    Platform Admin: Remove a hospital record with safety confirmation.
    """
    hospital = get_object_or_404(Hospital, pk=pk)
    hospital_name = hospital.name
    hospital.delete()
    messages.success(request, f"Hospital record '{hospital_name}' has been deleted from the registry.")
    return redirect('emergency:hospital_manage')

