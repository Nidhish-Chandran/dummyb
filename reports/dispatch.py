"""Location-based ranger dispatch helpers.

Reuses existing data: SightingReport.latitude/longitude/location_name and
UserProfile.registered_location/latitude/longitude/availability.
No hard-coded rangers or locations — everything comes from the database.
"""
import math

from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import UserProfile

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


def _location_match_q(location_name):
    """Q object matching rangers whose registered location / region shares a
    word with the report's location name (case-insensitive, >=4 chars)."""
    q = Q(profile__registered_location__iexact=location_name) | \
        Q(profile__assigned_region__iexact=location_name)
    for word in [w for w in location_name.replace(',', ' ').split() if len(w) >= 4]:
        q |= Q(profile__registered_location__icontains=word)
        q |= Q(profile__assigned_region__icontains=word)
    return q


def get_candidate_rangers(sighting, only_available=True, radius_km=NEARBY_RADIUS_KM):
    """Return rangers relevant to THIS report location, annotated with distance.

    Selection logic (server-side, never exposes the whole ranger DB):
      1. Ranger role users with a registered operational location.
      2. If the report has coordinates -> include rangers within `radius_km`
         (Haversine) OR whose registered location textually matches the
         report location (ranger base without coordinates still surfaces;
         distance shown as "nearby").
      3. If the report has no usable coordinates -> textual location match.
      4. Optionally restricted to AVAILABLE rangers (default for new
         assignments; reassignment view may pass False to also show BUSY).
    Returns a list of dicts sorted by distance (None-distance last).
    """
    rangers = User.objects.filter(
        profile__role=UserProfile.ROLE_RANGER
    ).select_related('profile')

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
            if prof.registered_location and (
                prof.registered_location.lower() in sighting.location_name.lower()
                or sighting.location_name.lower().split(',')[0].strip() == prof.registered_location.lower()
            ):
                location_relevant = True
            elif _location_match_q(sighting.location_name).isEmpty():
                pass
            else:
                # single-user textual check against this ranger's fields
                rl = (prof.registered_location or '').lower()
                ar = (prof.assigned_region or '').lower()
                loc = sighting.location_name.lower()
                words = [w for w in loc.replace(',', ' ').split() if len(w) >= 4]
                if rl and (rl in loc or any(w in rl for w in words)):
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
