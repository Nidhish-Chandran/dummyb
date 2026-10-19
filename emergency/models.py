from django.db import models
import math

class Hospital(models.Model):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=50, help_text="Emergency Contact / Hotline")
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    anti_venom_available = models.BooleanField(default=True)
    anti_venom_stock_vials = models.IntegerField(default=50, help_text="Vials in stock")
    has_icu = models.BooleanField(default=True, help_text="24/7 ICU & Ventilator availability")
    operating_hours = models.CharField(max_length=100, default="24/7 Emergency Care")

    district = models.CharField(max_length=100, blank=True, default='', help_text="District or administrative region")
    emergency_department = models.BooleanField(default=True, help_text="Dedicated 24/7 Emergency Department")
    anti_venom_notes = models.TextField(blank=True, default='', help_text="Stock notes, species-specific anti-venom details, or supplier info")
    stock_last_updated = models.DateTimeField(auto_now=True, help_text="Timestamp when anti-venom stock was last verified/updated")
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_hospitals', help_text="Admin who last updated this record")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        dist_str = f" - {self.district}" if self.district else ""
        return f"{self.name}{dist_str} ({'Anti-Venom Available' if self.anti_venom_available else 'Out of Stock'})"

    def distance_from(self, user_lat, user_lng):
        """Calculates distance in kilometers using the Haversine formula."""
        R = 6371.0  # Earth's radius in kilometers

        dlat = math.radians(self.latitude - user_lat)
        dlng = math.radians(self.longitude - user_lng)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(user_lat)) * math.cos(math.radians(self.latitude)) * math.sin(dlng / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)


class EmergencySOSEvent(models.Model):
    """Real-time Emergency SOS distress event log.

    Persists citizen distress signals with GPS coordinates, contact details,
    and status tracking for Authority operations and emergency logistics.
    """
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_ACKNOWLEDGED = 'ACKNOWLEDGED'
    STATUS_RESOLVED = 'RESOLVED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active Distress'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged by Authority'),
        (STATUS_RESOLVED, 'Resolved / Assistance Provided'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sos_events')
    phone_number = models.CharField(max_length=50, blank=True, null=True, help_text="Contact number for emergency callbacks")
    latitude = models.FloatField(help_text="Distress incident latitude")
    longitude = models.FloatField(help_text="Distress incident longitude")
    location_name = models.CharField(max_length=255, default='Unknown Location', help_text="Reported landmark or district")
    emergency_type = models.CharField(max_length=50, default='SNAKEBITE_DISTRESS', help_text="Type of emergency")
    description = models.TextField(blank=True, null=True, help_text="Victim condition or encounter notes")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    acknowledged_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_sos_events')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SOS #{self.pk} - {self.location_name} ({self.get_status_display()}) at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

