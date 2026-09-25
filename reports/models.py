from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class SightingReport(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_RESOLVED = 'RESOLVED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending AI & Authority Verification'),
        (STATUS_VERIFIED, 'Verified Sighting'),
        (STATUS_REJECTED, 'Rejected / False Alarm'),
        (STATUS_RESOLVED, 'Captured / Area Cleared'),
    ]

    VENOM_HIGHLY = 'HIGHLY_VENOMOUS'
    VENOM_MODERATE = 'VENOMOUS'
    VENOM_SAFE = 'NON_VENOMOUS'

    VENOM_CHOICES = [
        (VENOM_HIGHLY, 'Highly Venomous'),
        (VENOM_MODERATE, 'Venomous'),
        (VENOM_SAFE, 'Non-Venomous'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    title = models.CharField(max_length=200, default="Snake Sighting")
    original_image = models.ImageField(upload_to='sightings/')
    processed_image = models.ImageField(upload_to='processed_sightings/', blank=True, null=True)
    
    # GPS Coordinates
    latitude = models.FloatField(help_text="Latitude in decimal degrees")
    longitude = models.FloatField(help_text="Longitude in decimal degrees")
    location_name = models.CharField(max_length=255, help_text="Street, District, or Landmark Name")

    # Status & Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # AI Detection Metadata
    ai_detected = models.BooleanField(default=False)
    snake_detected = models.BooleanField(default=False)
    snake_confidence = models.FloatField(default=0.0, null=True, blank=True)
    venomous = models.BooleanField(null=True, blank=True)
    venom_confidence = models.FloatField(default=0.0, null=True, blank=True)
    species_predicted = models.CharField(max_length=150, blank=True, null=True)
    common_name = models.CharField(max_length=150, blank=True, null=True)
    venom_category = models.CharField(max_length=30, choices=VENOM_CHOICES, default=VENOM_SAFE)
    toxicity_level = models.CharField(max_length=50, default='SAFE')
    danger_score = models.IntegerField(default=10)
    ai_confidence = models.FloatField(default=0.0)
    model_1_name = models.CharField(max_length=150, default="venomwatch_cnn2_final (CNN)")
    model_2_name = models.CharField(max_length=150, default="venom_watch_cnn2_keras")
    notes = models.TextField(blank=True, null=True, help_text="Additional observer details")

    # Authority Verification & Task Assignment
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_reports')
    authority_notes = models.TextField(blank=True, null=True)

    # Duplicate & Spam Detection Flags
    duplicate_flag = models.BooleanField(default=False, help_text="Flagged as potential duplicate sighting")
    duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='duplicates')
    spam_flag = models.BooleanField(default=False, help_text="Flagged as suspicious/spam submission")
    spam_reason = models.CharField(max_length=255, blank=True, null=True)

    # Volunteer / Responder Incident Task Assignment
    RESPONSE_UNASSIGNED = 'UNASSIGNED'
    RESPONSE_ASSIGNED = 'ASSIGNED'
    RESPONSE_IN_PROGRESS = 'IN_PROGRESS'
    RESPONSE_RESOLVED = 'RESOLVED'

    RESPONSE_STATUS_CHOICES = [
        (RESPONSE_UNASSIGNED, 'Unassigned'),
        (RESPONSE_ASSIGNED, 'Responder Assigned'),
        (RESPONSE_IN_PROGRESS, 'Response in Progress'),
        (RESPONSE_RESOLVED, 'Captured / Resolved'),
    ]

    assigned_responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    response_status = models.CharField(max_length=20, choices=RESPONSE_STATUS_CHOICES, default=RESPONSE_UNASSIGNED)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.species_predicted or 'Snake'} - {self.location_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def is_active_48h(self):
        """Checks if the sighting report occurred within the last 48 hours for DBSCAN hotspot clustering."""
        return self.created_at >= timezone.now() - timedelta(hours=48)

    @property
    def is_venomous(self):
        return self.venom_category in [self.VENOM_HIGHLY, self.VENOM_MODERATE]


class RangerAssignment(models.Model):
    """Formal incident assignment linking a SightingReport to a Ranger.

    Object-level security: only the assigned ranger (and Authority/Admin)
    may view or act on an assignment. Assignments are created by an
    Authority user for a specific sighting report.
    """

    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_ON_THE_WAY = 'ON_THE_WAY'
    STATUS_AT_LOCATION = 'AT_LOCATION'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_DECLINED = 'DECLINED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_ASSIGNED, 'Assigned'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_ON_THE_WAY, 'On the way'),
        (STATUS_AT_LOCATION, 'At location'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_DECLINED, 'Declined'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    ACTIVE_STATUSES = [STATUS_ASSIGNED, STATUS_ACCEPTED, STATUS_ON_THE_WAY, STATUS_AT_LOCATION]

    OUTCOME_CHOICES = [
        ('SNAKE_CAPTURED', 'Snake Captured'),
        ('SNAKE_ESCAPED', 'Snake Escaped'),
        ('SNAKE_NOT_FOUND', 'Snake Not Found'),
        ('FALSE_REPORT', 'False Report'),
        ('OTHER', 'Other'),
    ]

    # Allowed ranger-driven status transitions (lifecycle is strictly linear)
    ALLOWED_TRANSITIONS = {
        STATUS_ASSIGNED: {STATUS_ACCEPTED, STATUS_DECLINED},
        STATUS_ACCEPTED: {STATUS_ON_THE_WAY},
        STATUS_ON_THE_WAY: {STATUS_AT_LOCATION},
        STATUS_AT_LOCATION: {STATUS_COMPLETED},
    }

    sighting = models.ForeignKey(SightingReport, on_delete=models.CASCADE, related_name='ranger_assignments')
    ranger = models.ForeignKey(User, on_delete=models.PROTECT, related_name='ranger_assignments',
                               limit_choices_to={'profile__role': 'ranger'})
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assignments_created')
    assigned_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True,
                                        help_text="When the ranger accepted or declined")
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ASSIGNED)
    distance_km = models.FloatField(null=True, blank=True,
                                    help_text="Haversine distance from ranger base to report at assignment time")
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text="Ranger field notes captured at completion")
    outcome_image = models.ImageField(upload_to='assignment_outcomes/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"Assignment #{self.pk} - Report #{self.sighting_id} -> {self.ranger.username} ({self.status})"

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    def can_transition(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    @property
    def next_action(self):
        """The single next action button label/status for the ranger workflow."""
        nxt = {
            self.STATUS_ASSIGNED: self.STATUS_ACCEPTED,
            self.STATUS_ACCEPTED: self.STATUS_ON_THE_WAY,
            self.STATUS_ON_THE_WAY: self.STATUS_AT_LOCATION,
            self.STATUS_AT_LOCATION: None,
        }
        return nxt.get(self.status)
