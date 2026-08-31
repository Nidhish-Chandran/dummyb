import numpy as np
from sklearn.cluster import DBSCAN
from django.utils import timezone
from datetime import timedelta
from reports.models import SightingReport

class DBSCANHotspotService:
    """
    Geospatial analysis & Risk Zone classification engine.
    Applies strict 24-hour window criteria for public community risk zones:
    - 0 reports in 24h -> GREEN ZONE (Low Risk / Safe)
    - 1-5 reports in 24h -> YELLOW ZONE (Moderate Risk)
    - >5 reports in 24h -> RED ZONE (High Risk / Emergency Alert)
    Excludes duplicate and spam-flagged submissions from cluster statistics.
    """

    @classmethod
    def get_active_sightings(cls, hours=24, include_duplicates=False):
        """Returns non-rejected valid reports submitted within the specified hours window."""
        cutoff = timezone.now() - timedelta(hours=hours)
        qs = SightingReport.objects.filter(created_at__gte=cutoff).exclude(status=SightingReport.STATUS_REJECTED)
        if not include_duplicates:
            qs = qs.filter(duplicate_flag=False, spam_flag=False)
        return qs

    @classmethod
    def compute_community_risk_zones(cls, hours=24):
        """
        Calculates aggregated public community risk status based on strict rules:
        - 0 reports -> GREEN
        - 1-5 reports -> YELLOW
        - >5 reports -> RED
        Groups valid reports by location/district for public safety overview.
        Does NOT return exact coordinates or individual markers to public users.
        """
        active_reports = cls.get_active_sightings(hours=hours)
        count = active_reports.count()

        if count == 0:
            overall_level = 'GREEN'
            status_title = 'Low Incident Zone (Safe)'
            badge_class = 'bg-success'
            description = 'No active snake sightings reported in the last 24 hours in your area.'
        elif 1 <= count <= 5:
            overall_level = 'YELLOW'
            status_title = 'Moderate Risk Zone'
            badge_class = 'bg-warning text-dark'
            description = f'{count} snake sighting(s) logged within the last 24 hours. Exercise routine caution.'
        else: # count > 5
            overall_level = 'RED'
            status_title = 'High Risk / Emergency Zone'
            badge_class = 'bg-danger'
            description = f'{count} active snake sightings logged within the last 24 hours. Stay alert and avoid dark/overgrown areas.'

        # Aggregated count per district / location name
        location_counts = {}
        for r in active_reports:
            loc = r.location_name or 'General Region'
            location_counts[loc] = location_counts.get(loc, 0) + 1

        location_summary = []
        for loc, c in location_counts.items():
            if c == 0:
                lvl, cls_name = 'GREEN', 'text-success'
            elif 1 <= c <= 5:
                lvl, cls_name = 'YELLOW', 'text-warning'
            else:
                lvl, cls_name = 'RED', 'text-danger'

            location_summary.append({
                'location_name': loc,
                'sighting_count': c,
                'risk_level': lvl,
                'class_name': cls_name
            })

        return {
            'hours_window': hours,
            'total_active_count': count,
            'overall_risk_level': overall_level,
            'status_title': status_title,
            'badge_class': badge_class,
            'description': description,
            'location_summary': location_summary
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
