import numpy as np
from sklearn.cluster import DBSCAN
from django.utils import timezone
from datetime import timedelta
from reports.models import SightingReport

class DBSCANHotspotService:
    """
    Geospatial analysis & Community Risk Zone classification engine.
    Four-state incident-based lifecycle:
    - RED (High Risk): 3+ distinct active snake incidents.
    - ORANGE (Caution): 1-2 distinct active snake incidents.
    - YELLOW (Recently Resolved): Captured or confirmed resolved within cooldown.
    - GREEN (No Recent Active Incidents): Eligible after yellow cooldown expires until retention expires.
    """
    # Configurable Lifecycle Time Windows (Timezone-Aware)
    ACTIVE_INCIDENT_WINDOW_HOURS = 24    # Active risk evaluation window
    RESOLVED_COOLDOWN_HOURS = 24         # Yellow cooldown after confirmed resolution
    GREEN_RETENTION_HOURS = 48           # Green retention after cooldown before zone expires

    @classmethod
    def get_active_sightings(cls, hours=None, include_duplicates=False):
        """Returns non-rejected valid reports submitted within the specified hours window."""
        h = hours or cls.ACTIVE_INCIDENT_WINDOW_HOURS
        cutoff = timezone.now() - timedelta(hours=h)
        qs = SightingReport.objects.filter(created_at__gte=cutoff).exclude(status=SightingReport.STATUS_REJECTED)
        if not include_duplicates:
            qs = qs.filter(duplicate_flag=False, spam_flag=False, duplicate_of__isnull=True)
        return qs

    @classmethod
    def compute_community_risk_zones(cls, hours=None, eps_km=1.5):
        """
        Calculates geographic community risk zones based on distinct snake incidents:
        1. Excludes duplicate reports so multiple submissions about the same incident count as 1.
        2. Four-state lifecycle per geographic zone:
           - RED (High Risk): 3+ distinct active snake incidents.
           - ORANGE (Caution): 1-2 distinct active snake incidents.
           - YELLOW (Recently Resolved): Captured or confirmed resolved within cooldown.
           - GREEN (No Recent Active Incidents): Eligible after yellow cooldown expires until retention expires.
           - Stale zones outside retention are removed.
        3. Groups distinct incidents geographically via spherical Haversine clustering.
        """
        active_window_hours = hours or cls.ACTIVE_INCIDENT_WINDOW_HOURS
        cooldown_hours = cls.RESOLVED_COOLDOWN_HOURS
        retention_hours = cls.GREEN_RETENTION_HOURS
        max_evaluation_hours = active_window_hours + cooldown_hours + retention_hours

        now = timezone.now()
        max_cutoff = now - timedelta(hours=max_evaluation_hours)

        # 1. Fetch distinct, non-duplicate, non-rejected incident records
        candidate_reports = list(SightingReport.objects.filter(
            created_at__gte=max_cutoff
        ).exclude(
            status=SightingReport.STATUS_REJECTED
        ).filter(
            duplicate_flag=False,
            spam_flag=False,
            duplicate_of__isnull=True
        ).select_related('assigned_responder', 'user'))

        if not candidate_reports:
            return {
                'active_window_hours': active_window_hours,
                'cooldown_hours': cooldown_hours,
                'retention_hours': retention_hours,
                'total_active_incidents': 0,
                'total_zones': 0,
                'zones': [],
                'overall_risk_level': 'GREEN',
                'status_title': 'No Recent Active Incidents',
                'badge_class': 'bg-success',
                'description': 'No active snake incidents reported across monitored community sectors.'
            }

        # 2. Helper to classify individual incident lifecycle
        def incident_state(r):
            # Check if resolved by authorized workflow
            is_resolved = (r.status == SightingReport.STATUS_RESOLVED)
            if not is_resolved:
                # Check if formal ranger assignment was completed/approved
                completed_assignment = r.ranger_assignments.filter(
                    status__in=['COMPLETED'],
                ).first() if hasattr(r, 'ranger_assignments') else None
                if completed_assignment:
                    is_resolved = True

            if is_resolved:
                # Calculate resolution timestamp
                res_time = r.updated_at
                # If ranger assignment has completed_at, use that
                if hasattr(r, 'ranger_assignments'):
                    ca = r.ranger_assignments.filter(status='COMPLETED').order_by('-completed_at').first()
                    if ca and ca.completed_at:
                        res_time = ca.completed_at

                time_since_res = (now - res_time).total_seconds() / 3600.0
                if time_since_res <= cooldown_hours:
                    return 'YELLOW_COOLDOWN', res_time
                elif time_since_res <= (cooldown_hours + retention_hours):
                    return 'GREEN_RETENTION', res_time
                else:
                    return 'EXPIRED', res_time
            else:
                # Active incident
                time_since_creation = (now - r.created_at).total_seconds() / 3600.0
                if time_since_creation <= active_window_hours:
                    return 'ACTIVE', r.created_at
                else:
                    return 'EXPIRED', r.created_at

        # Filter out expired incidents
        valid_incidents = []
        for r in candidate_reports:
            state, ts = incident_state(r)
            if state != 'EXPIRED':
                r._incident_state = state
                r._incident_timestamp = ts
                valid_incidents.append(r)

        if not valid_incidents:
            return {
                'active_window_hours': active_window_hours,
                'cooldown_hours': cooldown_hours,
                'retention_hours': retention_hours,
                'total_active_incidents': 0,
                'total_zones': 0,
                'zones': [],
                'overall_risk_level': 'GREEN',
                'status_title': 'No Recent Active Incidents',
                'badge_class': 'bg-success',
                'description': 'All previously tracked incidents have cleared and expired past retention.'
            }

        # 3. Cluster distinct incidents geographically via DBSCAN
        coords = np.array([[r.latitude, r.longitude] for r in valid_incidents])
        coords_rad = np.radians(coords)
        kms_per_radian = 6371.0
        epsilon = eps_km / kms_per_radian

        if len(coords) >= 2:
            db = DBSCAN(eps=epsilon, min_samples=1, metric='haversine', algorithm='ball_tree')
            db.fit(coords_rad)
            labels = db.labels_
        else:
            labels = np.array([0])

        cluster_groups = {}
        for idx, label in enumerate(labels):
            cluster_groups.setdefault(label, []).append(valid_incidents[idx])

        # 4. Formulate risk zone for each geographic cluster
        zones = []
        for cid, reports_in_cluster in cluster_groups.items():
            active_list = [r for r in reports_in_cluster if r._incident_state == 'ACTIVE']
            yellow_list = [r for r in reports_in_cluster if r._incident_state == 'YELLOW_COOLDOWN']
            green_list = [r for r in reports_in_cluster if r._incident_state == 'GREEN_RETENTION']

            active_cnt = len(active_list)
            yellow_cnt = len(yellow_list)
            green_cnt = len(green_list)

            # Determine Zone State
            if active_cnt >= 3:
                zone_state = 'RED'
                state_title = 'High Risk'
                badge_class = 'bg-danger'
                color = '#dc2626'
                summary = f'{active_cnt} distinct active snake incidents reported in this zone. Multiple sightings active.'
            elif active_cnt >= 1:
                zone_state = 'ORANGE'
                state_title = 'Caution'
                badge_class = 'bg-warning text-dark'
                color = '#f97316'
                summary = f'{active_cnt} distinct active snake incident(s) in this zone. Exercise caution.'
            elif yellow_cnt > 0:
                zone_state = 'YELLOW'
                state_title = 'Recently Resolved'
                badge_class = 'bg-warning text-dark'
                color = '#eab308'
                summary = 'Snake incident recently captured or resolved by wildlife response. Cooldown in effect.'
            elif green_cnt > 0:
                zone_state = 'GREEN'
                state_title = 'No Recent Active Incidents'
                badge_class = 'bg-success'
                color = '#10b981'
                summary = 'Previous incident safely resolved and cooldown completed. No active threats.'
            else:
                # Expired cluster
                continue

            # Calculate geographic centroid and radius
            clats = [r.latitude for r in reports_in_cluster]
            clngs = [r.longitude for r in reports_in_cluster]
            center_lat = float(np.mean(clats))
            center_lng = float(np.mean(clngs))

            if len(clats) > 1:
                lat_diff = (np.array(clats) - center_lat) * 111000
                lng_diff = (np.array(clngs) - center_lng) * 111000 * np.cos(np.radians(center_lat))
                distances = np.sqrt(lat_diff**2 + lng_diff**2)
                radius_meters = max(500, int(np.max(distances)) + 250)
            else:
                radius_meters = 600

            # Privacy-preserving locality label
            loc_name = reports_in_cluster[0].location_name or 'Monitored Sector'

            zones.append({
                'zone_id': f"zone_{cid}_{int(center_lat*100)}_{int(center_lng*100)}",
                'state': zone_state,
                'state_title': state_title,
                'badge_class': badge_class,
                'color': color,
                'center_lat': round(center_lat, 6),
                'center_lng': round(center_lng, 6),
                'radius_meters': radius_meters,
                'location_name': loc_name,
                'active_count': active_cnt,
                'resolved_count': yellow_cnt + green_cnt,
                'total_distinct_incidents': len(reports_in_cluster),
                'summary': summary,
            })

        # Sort zones by severity: RED first, then ORANGE, YELLOW, GREEN
        severity_order = {'RED': 0, 'ORANGE': 1, 'YELLOW': 2, 'GREEN': 3}
        zones.sort(key=lambda z: (severity_order.get(z['state'], 4), -z['active_count']))

        total_active = sum(z['active_count'] for z in zones)
        highest_state = zones[0]['state'] if zones else 'GREEN'
        overall_badge = zones[0]['badge_class'] if zones else 'bg-success'
        overall_title = zones[0]['state_title'] if zones else 'No Recent Active Incidents'

        return {
            'active_window_hours': active_window_hours,
            'cooldown_hours': cooldown_hours,
            'retention_hours': retention_hours,
            'total_active_incidents': total_active,
            'total_zones': len(zones),
            'zones': zones,
            'overall_risk_level': highest_state,
            'status_title': overall_title,
            'badge_class': overall_badge,
            'description': f"{len(zones)} community risk sector(s) monitored. {total_active} active incident(s) across zones."
        }


    @classmethod
    def compute_hotspots(cls, eps_km=1.0, min_samples=2, hours=48):
        """
        Authority-only spatial density clustering engine using scikit-learn DBSCAN.
        Computes spatial density clusters for authorized GIS surveillance.
        """
        active_reports = list(cls.get_active_sightings(hours=hours))
        
        if not active_reports:
            return {
                'clusters': [],
                'green_spots': [],
                'total_active_sightings': 0,
                'high_alert_count': 0
            }

        coords = np.array([[r.latitude, r.longitude] for r in active_reports])
        
        if len(coords) < min_samples:
            clusters = []
            green_spots = []
            for r in active_reports:
                spot_data = {
                    'report_id': r.id,
                    'title': r.title,
                    'species': r.species_predicted or 'Snake',
                    'latitude': r.latitude,
                    'longitude': r.longitude,
                    'location_name': r.location_name,
                    'venom_category': r.venom_category,
                    'is_venomous': r.is_venomous,
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
                }
                if r.is_venomous:
                    clusters.append({
                        'cluster_id': f"single_{r.id}",
                        'center_lat': r.latitude,
                        'center_lng': r.longitude,
                        'radius_meters': 500,
                        'sighting_count': 1,
                        'venomous_count': 1,
                        'alert_level': 'HIGH_ALERT',
                        'location_name': r.location_name,
                        'reports': [spot_data]
                    })
                else:
                    green_spots.append(spot_data)

            return {
                'clusters': clusters,
                'green_spots': green_spots,
                'total_active_sightings': len(active_reports),
                'high_alert_count': len(clusters)
            }

        coords_rad = np.radians(coords)
        kms_per_radian = 6371.0
        epsilon = eps_km / kms_per_radian

        db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='haversine', algorithm='ball_tree')
        db.fit(coords_rad)

        labels = db.labels_
        unique_labels = set(labels)

        clusters = []
        green_spots = []

        for label in unique_labels:
            if label == -1:
                noise_indices = np.where(labels == -1)[0]
                for idx in noise_indices:
                    r = active_reports[idx]
                    spot_data = {
                        'report_id': r.id,
                        'title': r.title,
                        'species': r.species_predicted or 'Snake',
                        'latitude': r.latitude,
                        'longitude': r.longitude,
                        'location_name': r.location_name,
                        'venom_category': r.venom_category,
                        'is_venomous': r.is_venomous,
                        'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
                    }
                    if r.is_venomous:
                        clusters.append({
                            'cluster_id': f"single_{r.id}",
                            'center_lat': r.latitude,
                            'center_lng': r.longitude,
                            'radius_meters': 500,
                            'sighting_count': 1,
                            'venomous_count': 1,
                            'alert_level': 'MEDIUM_ALERT',
                            'location_name': r.location_name,
                            'reports': [spot_data]
                        })
                    else:
                        green_spots.append(spot_data)
            else:
                cluster_indices = np.where(labels == label)[0]
                cluster_reports = [active_reports[i] for i in cluster_indices]
                cluster_coords = coords[cluster_indices]

                center_lat = float(np.mean(cluster_coords[:, 0]))
                center_lng = float(np.mean(cluster_coords[:, 1]))

                lat_diff = (cluster_coords[:, 0] - center_lat) * 111000
                lng_diff = (cluster_coords[:, 1] - center_lng) * 111000 * np.cos(np.radians(center_lat))
                distances = np.sqrt(lat_diff**2 + lng_diff**2)
                radius_meters = max(500, int(np.max(distances)) + 200)

                venomous_count = sum(1 for r in cluster_reports if r.is_venomous)
                alert_level = 'HIGH_ALERT' if venomous_count > 0 else 'GREEN_ZONE'

                cluster_data = {
                    'cluster_id': f"cluster_{label}",
                    'center_lat': center_lat,
                    'center_lng': center_lng,
                    'radius_meters': radius_meters,
                    'sighting_count': len(cluster_reports),
                    'venomous_count': venomous_count,
                    'alert_level': alert_level,
                    'location_name': cluster_reports[0].location_name,
                    'reports': [{
                        'report_id': r.id,
                        'title': r.title,
                        'species': r.species_predicted or 'Snake',
                        'latitude': r.latitude,
                        'longitude': r.longitude,
                        'location_name': r.location_name,
                        'venom_category': r.venom_category,
                        'is_venomous': r.is_venomous,
                        'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
                    } for r in cluster_reports]
                }
                
                if alert_level == 'HIGH_ALERT':
                    clusters.append(cluster_data)
                else:
                    green_spots.extend(cluster_data['reports'])

        high_alert_count = sum(1 for c in clusters if c['alert_level'] in ['HIGH_ALERT', 'MEDIUM_ALERT'])

        return {
            'clusters': clusters,
            'green_spots': green_spots,
            'total_active_sightings': len(active_reports),
            'high_alert_count': high_alert_count
        }
