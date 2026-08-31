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

    def __str__(self):
        return f"{self.name} ({'Anti-Venom Available' if self.anti_venom_available else 'Out of Stock'})"

    def distance_from(self, user_lat, user_lng):
        """Calculates distance in kilometers using the Haversine formula."""
        R = 6371.0  # Earth's radius in kilometers

        dlat = math.radians(self.latitude - user_lat)
        dlng = math.radians(self.longitude - user_lng)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(user_lat)) * math.cos(math.radians(self.latitude)) * math.sin(dlng / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
