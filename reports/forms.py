from django import forms
from django.core.exceptions import ValidationError
from .models import SightingReport

class SightingReportForm(forms.ModelForm):
    class Meta:
        model = SightingReport
        fields = ['title', 'original_image', 'latitude', 'longitude', 'location_name', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cobra spotted near garden hedge', 'id': 'id_title'}),
            'original_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'sightingImageInput'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'id': 'latInput', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'id': 'lngInput', 'step': 'any'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'locationInput', 'placeholder': 'e.g. Sector 4 Park, Coastal Highway'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Behavior observed, direction moving, size estimate...', 'id': 'id_notes'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            return "Snake Sighting"
        return title

    def clean_location_name(self):
        loc = self.cleaned_data.get('location_name', '').strip()
        if not loc:
            raise ValidationError("Please provide a location name or landmark.")
        return loc

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is None:
            raise ValidationError("Latitude coordinate is required.")
        try:
            val = float(lat)
        except (ValueError, TypeError):
            raise ValidationError("Invalid latitude coordinate.")
        if not (-90.0 <= val <= 90.0):
            raise ValidationError("Latitude must be between -90.0 and 90.0 degrees.")
        return round(val, 6)

    def clean_longitude(self):
        lng = self.cleaned_data.get('longitude')
        if lng is None:
            raise ValidationError("Longitude coordinate is required.")
        try:
            val = float(lng)
        except (ValueError, TypeError):
            raise ValidationError("Invalid longitude coordinate.")
        if not (-180.0 <= val <= 180.0):
            raise ValidationError("Longitude must be between -180.0 and 180.0 degrees.")
        return round(val, 6)

