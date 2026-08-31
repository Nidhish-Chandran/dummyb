from django import forms
from .models import SightingReport

class SightingReportForm(forms.ModelForm):
    class Meta:
        model = SightingReport
        fields = ['title', 'original_image', 'latitude', 'longitude', 'location_name', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cobra spotted near garden hedge'}),
            'original_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'id': 'sightingImageInput'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'id': 'latInput', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'id': 'lngInput', 'step': 'any'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'id': 'locationInput', 'placeholder': 'e.g. Sector 4 Park, Coastal Highway'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Behavior observed, direction moving, size estimate...'}),
        }
