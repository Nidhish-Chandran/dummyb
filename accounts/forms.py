import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import UserProfile


class CustomAuthenticationForm(AuthenticationForm):
    """Login form with clear field-level validation and styled widgets."""
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'Enter your username',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )

    error_messages = {
        'invalid_login': (
            "Invalid username or password. Please check your credentials and try again."
        ),
        'inactive': ("This account is inactive. Please contact support."),
    }

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        username = re.sub(r'\s+', '', username or '')
        if not username:
            raise ValidationError("Username is required.")
        if len(username) > 150:
            raise ValidationError("Username is too long.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if not password:
            raise ValidationError("Password is required.")
        return password

    def clean(self):
        # Keep Django's authentication flow; error messages stay generic so
        # the form never reveals whether a username exists.
        return super().clean()


class UserRegistrationForm(UserCreationForm):
    """Public registration form — creates CITIZEN accounts only.

    Authority / Ranger / Admin accounts cannot be self-registered; they are
    provisioned by the platform administrator (Django admin or the demo seed
    command).  The role is therefore fixed to CITIZEN on the server side and
    any attempt to POST a different role is rejected.
    """
    email = forms.EmailField(
        required=True,
        label="Email address",
        help_text="Required. Used for account recovery and emergency notifications.",
        widget=forms.EmailInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        })
    )
    first_name = forms.CharField(
        max_length=150, required=True, label="First name",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150, required=False, label="Last name (optional)",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'Last name'})
    )
    # Public registration is always CITIZEN.  The role is not a user-editable
    # choice — any POSTed value other than citizen is rejected in clean_role.
    role = forms.CharField(
        widget=forms.HiddenInput(), required=False, initial=UserProfile.ROLE_CITIZEN)
    phone_number = forms.CharField(
        max_length=20, required=False, label="Phone number",
        help_text="Contact number used for emergency verification (required for Ranger/Authority).",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': '+91 98765 43210',
            'autocomplete': 'tel',
        })
    )
    organization = forms.CharField(
        max_length=100, required=False, label="Organization",
        help_text="Department, Hospital, or Agency (if applicable).",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'Organization name'})
    )

    # --- Role-specific fields (shown/hidden per selected account type) ---
    registered_location = forms.CharField(
        max_length=150, required=False, label="Registered operational location",
        help_text="Town/city where you operate, e.g. Kollam.",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'e.g. Kollam'})
    )
    latitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Base latitude",
        widget=forms.NumberInput(attrs={'class': 'auth-form-control', 'placeholder': '8.8932', 'step': 'any'})
    )
    longitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Base longitude",
        widget=forms.NumberInput(attrs={'class': 'auth-form-control', 'placeholder': '76.6141', 'step': 'any'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'auth-form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pw_attrs = {'class': 'auth-form-control', 'autocomplete': 'new-password'}
        self.fields['password1'].widget.attrs.update(pw_attrs)
        self.fields['password1'].widget.attrs['placeholder'] = 'Create a strong password'
        self.fields['password2'].widget.attrs.update(pw_attrs)
        self.fields['password2'].widget.attrs['placeholder'] = 'Repeat the password'

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[A-Za-z][A-Za-z0-9._@+-]{2,29}$', username):
            raise ValidationError(
                "Username must be 3-30 characters, start with a letter, and contain only "
                "letters, digits, and the symbols . _ + - @."
            )
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not re.match(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$', email):
            raise ValidationError("Enter a valid email address, e.g. name@example.com.")
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("An account with this email already exists. Sign in instead.")
        return email

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if len(name) < 2:
            raise ValidationError("First name must be at least 2 characters.")
        if not re.match(r"^[A-Za-z][A-Za-z .'-]*$", name):
            raise ValidationError("First name may only contain letters, spaces, apostrophes and hyphens.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if name and not re.match(r"^[A-Za-z][A-Za-z .'-]*$", name):
            raise ValidationError("Last name may only contain letters, spaces, apostrophes and hyphens.")
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        role = self._posted_role()
        if not phone and role in (UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY):
            raise ValidationError("Ranger and Authority accounts must provide a phone number.")
        if phone and not re.match(r'^\+?[0-9][0-9\s\-().]{5,19}$', phone):
            raise ValidationError(
                "Enter a valid phone number (digits only, optional leading +, 6-20 characters)."
            )
        digits = re.sub(r'\D', '', phone)
        if not (6 <= len(digits) <= 14):
            raise ValidationError("Phone number must contain 6 to 14 digits.")
        return phone

    def clean_role(self):
        role = self.cleaned_data.get('role') or UserProfile.ROLE_CITIZEN
        if role not in UserProfile.SELF_SERVICE_ROLES:
            raise ValidationError(
                "Public registration is available for Citizen accounts only. "
                "Ranger, Authority and Administrator accounts are created by "
                "the platform administrator."
            )
        return role

    # --- Role-conditional validation for Ranger / Authority registration ---
    def _posted_role(self):
        role = self.cleaned_data.get('role')
        if not role and hasattr(self, 'data'):
            role = self.data.get('role')
        return role or (self.initial.get('role') if isinstance(self.initial, dict) else None)

    def clean_registered_location(self):
        loc = self.cleaned_data.get('registered_location', '').strip()
        role = self._posted_role()
        if role == UserProfile.ROLE_RANGER and not loc:
            raise ValidationError("Ranger accounts must provide a registered operational location (e.g. Kollam).")
        if loc and not re.match(r"^[A-Za-z][A-Za-z .'\-]*$", loc):
            raise ValidationError("Location may only contain letters, spaces, apostrophes and hyphens.")
        return loc

    def _clean_coord(self, value, field_name, lo, hi):
        if value is None:
            return None
        v = float(value)
        if not (lo <= v <= hi):
            raise ValidationError(f"{field_name} must be between {lo} and {hi}.")
        return round(v, 6)

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        role = self._posted_role()
        if role == UserProfile.ROLE_RANGER and lat is None:
            raise ValidationError("Ranger accounts must provide a base latitude (decimal degrees).")
        return self._clean_coord(lat, "Latitude", -90.0, 90.0)

    def clean_longitude(self):
        lon = self.cleaned_data.get('longitude')
        role = self._posted_role()
        if role == UserProfile.ROLE_RANGER and lon is None:
            raise ValidationError("Ranger accounts must provide a base longitude (decimal degrees).")
        return self._clean_coord(lon, "Longitude", -180.0, 180.0)

    def clean_organization(self):
        org = self.cleaned_data.get('organization', '').strip()
        role = self._posted_role()
        if role == UserProfile.ROLE_AUTHORITY and not org:
            raise ValidationError("Authority officers must provide their department/organisation.")
        return org

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data.get('role', UserProfile.ROLE_CITIZEN)
        profile.full_name = " ".join(n for n in [self.cleaned_data.get('first_name', ''),
                                                 self.cleaned_data.get('last_name', '')] if n).strip() or None
        profile.phone_number = self.cleaned_data.get('phone_number') or None
        profile.organization = self.cleaned_data.get('organization') or None
        profile.registered_location = self.cleaned_data.get('registered_location') or None
        profile.latitude = self.cleaned_data.get('latitude')
        profile.longitude = self.cleaned_data.get('longitude')
        profile.save()
        return user


class UserProfileForm(forms.ModelForm):
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'organization', 'assigned_region',
                  'registered_location', 'latitude', 'longitude', 'availability']

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if phone and not re.match(r'^\+?[0-9][0-9\s\-().]{5,19}$', phone):
            raise ValidationError("Enter a valid phone number (digits, optional leading +).")
        return phone
