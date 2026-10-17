import math
from django.utils import timezone
from datetime import timedelta
from .models import SightingReport

class DuplicateSpamDetectionService:
    """
    Automated Multi-Signal Duplicate Sighting & Spam Detection Engine.

    Calculates a documented composite duplicate likelihood score (0-100) based on:
    - Precise Geographic Haversine Distance (50m radius = +50 pts, 200m = +35 pts, 500m = +20 pts)
    - Temporal Proximity (30min window = +30 pts, 2hr = +15 pts)
    - Species / Venom Category consistency (+10 to +20 pts)
    - Active Incident Status (Only unresolved incidents can be candidate parents)

    Decision Thresholds:
    - High-Confidence Duplicate (Score >= 75):
        Automatically links `duplicate_of` to the canonical active incident report.
        Prevents redundant second active responder assignments.
    - Medium-Confidence Suspected Duplicate (45 <= Score < 75):
        Flags `duplicate_flag = True` for Authority manual review without blocking response.
    - Low-Confidence / Independent (Score < 45):
        Kept independent as a distinct incident.
    """

    @staticmethod
    def haversine_distance_meters(lat1, lon1, lat2, lon2):
        """Calculates exact spherical distance between two coordinates in meters using Haversine formula."""
        R = 6371000.0  # Earth's radius in meters
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @classmethod
    def calculate_duplicate_score(cls, report, candidate):
        """
        Calculates a multi-signal duplicate likelihood score between 0 and 100.
        Returns (score, rationale_str, dist_meters, time_diff_minutes).
        """
        dist_m = cls.haversine_distance_meters(report.latitude, report.longitude, candidate.latitude, candidate.longitude)
        
        # Calculate time difference
        if report.created_at and candidate.created_at:
            time_diff = abs((report.created_at - candidate.created_at).total_seconds())
        else:
            time_diff = 0.0
        time_diff_min = time_diff / 60.0

        score = 0
        signals = []

        # 1. Geographic Signal (max 50 points)
        if dist_m <= 50.0:
            score += 50
            signals.append(f"Immediate proximity ({dist_m:.0f}m)")
        elif dist_m <= 200.0:
            score += 35
            signals.append(f"Close proximity ({dist_m:.0f}m)")
        elif dist_m <= 500.0:
            score += 20
            signals.append(f"Area proximity ({dist_m:.0f}m)")
        else:
            # Over 500m is not considered a duplicate incident
            return 0, "Distance exceeds 500m threshold", dist_m, time_diff_min

        # 2. Temporal Signal (max 30 points)
        if time_diff_min <= 30.0:
            score += 30
            signals.append(f"Within 30m window ({time_diff_min:.0f} mins)")
        elif time_diff_min <= 120.0:
            score += 15
            signals.append(f"Within 2h window ({time_diff_min:.0f} mins)")
        elif time_diff_min <= 360.0:
            score += 5
            signals.append(f"Within 6h window ({time_diff_min:.0f} mins)")

        # 3. Species / Venom Signal (max 20 points)
        if report.species_predicted and candidate.species_predicted:
            if report.species_predicted.lower() == candidate.species_predicted.lower():
                score += 20
                signals.append(f"Matching species ({report.species_predicted})")
            elif report.venom_category == candidate.venom_category:
                score += 10
                signals.append(f"Matching venom class ({report.venom_category})")
        elif report.venom_category and candidate.venom_category:
            if report.venom_category == candidate.venom_category:
                score += 10
                signals.append(f"Matching venom class ({report.venom_category})")

        # 4. Same reporter penalty/boost
        if report.user and candidate.user and report.user_id == candidate.user_id:
            score = min(100, score + 10)
            signals.append("Same reporter re-submission")

        rationale = "; ".join(signals)
        return min(100, score), rationale, dist_m, time_diff_min

    @classmethod
    def evaluate_and_flag(cls, report):
        """
        Evaluates a newly saved report for duplicate proximity and spam patterns.
        Updates duplicate_flag, duplicate_of, duplicate_score, duplicate_reason,
        spam_flag, and spam_reason fields.
        """
        modified = False

        # 1. Spam Submissions Check (Rate limiting: >3 reports by same user in 5 minutes)
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

        # 2. Multi-Signal Candidate Search
        # Candidate must have been created within 6 hours and NOT be REJECTED
        # Edge case: Resolved reports must NOT be automatically linked as active parents
        cutoff_6h = timezone.now() - timedelta(hours=6)
        candidates = SightingReport.objects.filter(
            created_at__gte=cutoff_6h
        ).exclude(pk=report.pk).exclude(status=SightingReport.STATUS_REJECTED)

        best_score = 0
        best_candidate = None
        best_rationale = ""

        for candidate in candidates:
            # If candidate was already resolved, don't auto-merge as an active duplicate
            if candidate.status == SightingReport.STATUS_RESOLVED:
                continue

            score, rationale, dist_m, time_diff_min = cls.calculate_duplicate_score(report, candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate
                best_rationale = rationale

        # 3. Apply Decision Thresholds
        if best_candidate and best_score >= 75:
            # High-confidence duplicate: Automatically link to root parent
            canonical_parent = best_candidate.duplicate_of if best_candidate.duplicate_of else best_candidate
            report.duplicate_flag = True
            report.duplicate_of = canonical_parent
            report.duplicate_score = best_score
            report.duplicate_reason = f"High confidence duplicate (Score {best_score}/100: {best_rationale})"
            modified = True
        elif best_candidate and best_score >= 45:
            # Medium-confidence duplicate: Flag for Authority review without blocking
            report.duplicate_flag = True
            report.duplicate_of = best_candidate
            report.duplicate_score = best_score
            report.duplicate_reason = f"Suspected duplicate for Authority review (Score {best_score}/100: {best_rationale})"
            modified = True
        elif best_candidate:
            # Low confidence match: Record score but do not flag as duplicate
            report.duplicate_score = best_score
            report.duplicate_reason = f"Independent sighting (Score {best_score}/100: {best_rationale})"
            modified = True

        if modified:
            report.save(update_fields=[
                'duplicate_flag', 'duplicate_of', 'duplicate_score', 'duplicate_reason',
                'spam_flag', 'spam_reason'
            ])

        return report
