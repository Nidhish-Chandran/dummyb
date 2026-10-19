"""Location-based ranger dispatch helpers.

Reuses existing data: SightingReport.latitude/longitude/location_name and
UserProfile.registered_location/latitude/longitude/availability.
No hard-coded rangers or locations — everything comes from the database.
"""
import math

from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import UserProfile, AccountApplication
from reports.models import RangerAssignment

# Search radius (km) used when the report has coordinates. Rangers farther
# than this are considered unrelated to the incident location.
NEARBY_RADIUS_KM = 30.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two coordinate pairs."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return None
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 2)


def get_candidate_rangers(sighting, only_available=True, radius_km=NEARBY_RADIUS_KM):
    """Return genuine, active, approved rangers relevant to THIS report location, annotated with distance.

    Eligibility rules (strictly enforced server-side):
      1. Account is active (is_active=True).
      2. Profile role is RANGER and account_status is ACTIVE (not SUSPENDED or BANNED).
      3. AccountApplication, if present, is APPROVED.
      4. No conflicting active assignments.
      5. Availability is AVAILABLE (when only_available=True).
      6. Distance within `radius_km` via Haversine calculation, or textual operational location match.
    Returns a list of dicts sorted by distance (nearest first, None-distance last).
    """
    rangers = User.objects.filter(
        is_active=True,
        profile__role=UserProfile.ROLE_RANGER,
        profile__account_status=UserProfile.ACCOUNT_STATUS_ACTIVE,
    ).select_related('profile')

    # Exclude applicants whose registration is not approved
    unapproved_app_users = AccountApplication.objects.exclude(
        status=AccountApplication.STATUS_APPROVED
    ).values_list('user_id', flat=True)
    rangers = rangers.exclude(id__in=unapproved_app_users)

    # Exclude rangers with an active conflicting assignment
    active_busy_rangers = RangerAssignment.objects.filter(
        status__in=RangerAssignment.ACTIVE_STATUSES
    ).values_list('ranger_id', flat=True)
    rangers = rangers.exclude(id__in=active_busy_rangers)

    if only_available:
        rangers = rangers.filter(profile__availability=UserProfile.AVAILABILITY_AVAILABLE)

    has_coords = sighting.latitude is not None and sighting.longitude is not None

    candidates = []
    for u in rangers:
        prof = u.profile
        dist = None
        location_relevant = False

        if has_coords and prof.latitude is not None and prof.longitude is not None:
            dist = haversine_km(prof.latitude, prof.longitude, sighting.latitude, sighting.longitude)
            if dist is not None and dist <= radius_km:
                location_relevant = True

        if not location_relevant and sighting.location_name:
            # single-user textual relevance check against this ranger's fields
            rl = (prof.registered_location or '').lower()
            ar = (prof.assigned_region or '').lower()
            loc = sighting.location_name.lower()
            if rl and (rl in loc or loc.split(',')[0].strip() == rl):
                location_relevant = True
            elif rl or ar:
                words = [w for w in loc.replace(',', ' ').split() if len(w) >= 4]
                if rl and any(w in rl for w in words):
                    location_relevant = True
                elif ar and (ar in loc or any(w in ar for w in words)):
                    location_relevant = True

        if not has_coords and (prof.registered_location or prof.assigned_region):
            # Without report coordinates rely purely on textual relevance already computed
            pass

        if location_relevant:
            candidates.append({
                'user': u,
                'profile': prof,
                'distance_km': dist,
            })

    candidates.sort(key=lambda c: (c['distance_km'] is None, c['distance_km'] if c['distance_km'] is not None else 0))
    return candidates
