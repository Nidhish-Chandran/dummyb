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
    model_1_name = models.CharField(max_length=150, default="Snake Detection.v2-model_snake-detection-2.yolov8")
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
