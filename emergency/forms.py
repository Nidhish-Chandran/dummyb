import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Hospital


class HospitalForm(forms.ModelForm):
    """
    Form for adding and editing registered hospitals and anti-venom supplies.
    Provides validation on coordinates, contact numbers, and duplicate detection.
    """
    name = forms.CharField(
        max_length=200,
        required=True,
        label="Hospital Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. District General Hospital & Anti-Venom Center',
            'id': 'id_hospital_name'
        })
    )
    district = forms.CharField(
        max_length=100,
        required=True,
        label="District / Region",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Ernakulam / Kollam / Wayanad',
            'id': 'id_hospital_district'
        })
    )
    address = forms.CharField(
        max_length=255,
        required=True,
        label="Full Address / Location",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Hospital Junction, Civil Station Road',
            'id': 'id_hospital_address'
        })
    )
    phone_number = forms.CharField(
        max_length=50,
        required=True,
        label="Emergency Contact / Hotline",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 108 / +91 484 2555555',
            'id': 'id_hospital_phone'
        })
    )
    latitude = forms.FloatField(
        required=True,
        label="Latitude",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 9.9312',
            'step': 'any',
            'id': 'id_hospital_lat'
        })
    )
    longitude = forms.FloatField(
        required=True,
        label="Longitude",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 76.2673',
            'step': 'any',
            'id': 'id_hospital_lng'
        })
    )
    operating_hours = forms.CharField(
        max_length=100,
        required=False,
        initial="24/7 Emergency Care",
        label="Operating Hours",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 24/7 Trauma Emergency Care',
            'id': 'id_operating_hours'
        })
    )
    anti_venom_stock_vials = forms.IntegerField(
        required=False,
        initial=50,
        min_value=0,
        label="Anti-Venom Stock (Vials)",
        help_text="Current verified vial quantity",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 50',
            'id': 'id_anti_venom_stock_vials'
        })
    )
    anti_venom_notes = forms.CharField(
        required=False,
        label="Anti-Venom Notes & Status",
        help_text="Specify polyvalent / monovalent types, cold storage status, or supplier details",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'e.g. Polyvalent ASV in stock. Lyophilized vials verified by pharmacy on inspection.',
            'id': 'id_anti_venom_notes'
        })
    )
    emergency_department = forms.BooleanField(
        required=False,
        initial=True,
        label="24/7 Emergency Department Available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_emergency_department'})
    )
    has_icu = forms.BooleanField(
        required=False,
        initial=True,
        label="ICU & Ventilator Support Available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_icu'})
    )
    anti_venom_available = forms.BooleanField(
        required=False,
        initial=True,
        label="Anti-Venom Available in Stock",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_anti_venom_available'})
    )

    class Meta:
        model = Hospital
        fields = [
            'name', 'district', 'address', 'phone_number',
            'latitude', 'longitude', 'operating_hours',
            'emergency_department', 'has_icu',
            'anti_venom_available', 'anti_venom_stock_vials', 'anti_venom_notes'
        ]

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError("Hospital name must be at least 3 characters long.")
        return name

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is not None and (lat < -90.0 or lat > 90.0):
            raise ValidationError("Latitude must be between -90.0 and 90.0 degrees.")
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data.get('longitude')
        if lng is not None and (lng < -180.0 or lng > 180.0):
            raise ValidationError("Longitude must be between -180.0 and 180.0 degrees.")
        return lng

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        # Accept hotline like 108 or standard phone formats
        if not re.match(r'^(?:108|1926|\+?[0-9\s\-()./]{5,30})$', phone):
            raise ValidationError("Enter a valid emergency contact or telephone number.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        district = cleaned_data.get('district')
        address = cleaned_data.get('address')
        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')
        av_available = cleaned_data.get('anti_venom_available')
        stock = cleaned_data.get('anti_venom_stock_vials')

        # Consistency: if stock is 0 and anti_venom_available is True, warn or adjust
        if stock == 0 and av_available:
            cleaned_data['anti_venom_available'] = False
        elif stock and stock > 0 and not av_available:
            cleaned_data['anti_venom_available'] = True

        # Duplicate detection: prevent records with identical name + district, or identical coordinates
        if name and district:
            qs = Hospital.objects.filter(name__iexact=name, district__iexact=district)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"A hospital named '{name}' is already registered in district '{district}'. "
                    "Please update the existing record instead of creating a duplicate."
                )

        if lat is not None and lng is not None:
            # Check for very close coordinates (within ~10 meters / 0.0001 deg)
            coord_qs = Hospital.objects.filter(
                latitude__range=(lat - 0.0001, lat + 0.0001),
                longitude__range=(lng - 0.0001, lng + 0.0001)
            )
            if self.instance and self.instance.pk:
                coord_qs = coord_qs.exclude(pk=self.instance.pk)
            if coord_qs.exists():
                existing = coord_qs.first()
                raise ValidationError(
                    f"Another facility ('{existing.name}') is already registered at these exact GPS coordinates."
                )

        return cleaned_data
