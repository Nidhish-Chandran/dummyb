import math
from django.utils import timezone
from datetime import timedelta
from .models import SightingReport

class DuplicateSpamDetectionService:
    """
    Automated Duplicate Sighting & Spam Detection Engine.
    Flags potential duplicates (spatial < 500m, temporal < 2h) and
    suspicious rate-limited submissions without deleting database records.
    """

    @staticmethod
    def haversine_distance_km(lat1, lon1, lat2, lon2):
        """Calculates distance between two lat/lng coordinates in kilometers using Haversine formula."""
        R = 6371.0  # Earth's radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @classmethod
    def evaluate_and_flag(cls, report):
        """
        Evaluates a newly saved report for duplicate proximity and spam patterns.
        Updates duplicate_flag, duplicate_of, spam_flag, and spam_reason fields.
        """
        modified = False

        # 1. Check Spam Submissions (Rate limiting: >3 reports by same user in 5 minutes)
        if report.user and report.user.is_authenticated:
            cutoff_5min = timezone.now() - timedelta(minutes=5)
            user_recent_count = SightingReport.objects.filter(
                user=report.user,
                created_at__gte=cutoff_5min
            ).exclude(pk=report.pk).count()

            if user_recent_count >= 3:
                report.spam_flag = True
                report.spam_reason = f"High frequency submission ({user_recent_count + 1} reports in 5 minutes)"
                modified = True

        # 2. Check Duplicate Submissions (Spatial distance < 0.5 km & Temporal window < 2 hours)
        cutoff_2h = timezone.now() - timedelta(hours=2)
        recent_candidates = SightingReport.objects.filter(
            created_at__gte=cutoff_2h
        ).exclude(pk=report.pk).exclude(status=SightingReport.STATUS_REJECTED)

        for candidate in recent_candidates:
            dist_km = cls.haversine_distance_km(report.latitude, report.longitude, candidate.latitude, candidate.longitude)
            if dist_km <= 0.5:
                # Geographic & temporal match found
                report.duplicate_flag = True
                report.duplicate_of = candidate
                modified = True
                break

        if modified:
            report.save(update_fields=['duplicate_flag', 'duplicate_of', 'spam_flag', 'spam_reason'])

        return report
