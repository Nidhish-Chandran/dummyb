import re
import os

from django import forms
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.urls import reverse
from .models import UserProfile, AccountApplication, Notification, AuditLog


class CustomAuthenticationForm(AuthenticationForm):
    """Login form with clear field-level validation, styled widgets, and approval/ban checks."""
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
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            user = User.objects.filter(username__iexact=username).first()
            if user and user.check_password(password):
                # Check application status first if applicant
                if hasattr(user, 'application'):
                    app = user.application
                    if app.status == AccountApplication.STATUS_PENDING:
                        raise ValidationError(
                            "Your account application is currently pending administrative review. You will be able to sign in once an administrator approves your credentials.",
                            code='application_pending'
                        )
                    elif app.status == AccountApplication.STATUS_REJECTED:
                        reason = f" Reason: {app.rejection_reason}" if app.rejection_reason else ""
                        raise ValidationError(
                            f"Your account application was not approved.{reason}",
                            code='application_rejected'
                        )
                    elif app.status == AccountApplication.STATUS_NEEDS_INFO:
                        reason = f" Note: {app.rejection_reason}" if app.rejection_reason else ""
                        raise ValidationError(
                            f"Additional information is needed for your application.{reason} Please contact the platform administrator.",
                            code='application_needs_info'
                        )

                # Check UserProfile account status
                if hasattr(user, 'profile'):
                    prof = user.profile
                    if prof.account_status == UserProfile.ACCOUNT_SUSPENDED:
                        reason = f" Reason: {prof.suspension_reason}" if prof.suspension_reason else ""
                        raise ValidationError(
                            f"Your account has been suspended by an administrator.{reason}",
                            code='account_suspended'
                        )
                    elif prof.account_status == UserProfile.ACCOUNT_BANNED:
                        reason = f" Reason: {prof.suspension_reason}" if prof.suspension_reason else ""
                        raise ValidationError(
                            f"Your account has been banned.{reason}",
                            code='account_banned'
                        )

                if not user.is_active:
                    raise ValidationError(
                        "This account is inactive. Please contact system support.",
                        code='inactive'
                    )

        return super().clean()

    def confirm_login_allowed(self, user):
        if hasattr(user, 'profile'):
            prof = user.profile
            if prof.account_status == UserProfile.ACCOUNT_SUSPENDED:
                reason = f" Reason: {prof.suspension_reason}" if prof.suspension_reason else ""
                raise ValidationError(f"Your account has been suspended.{reason}", code='account_suspended')
            elif prof.account_status == UserProfile.ACCOUNT_BANNED:
                reason = f" Reason: {prof.suspension_reason}" if prof.suspension_reason else ""
                raise ValidationError(f"Your account has been banned.{reason}", code='account_banned')
        if hasattr(user, 'application'):
            if user.application.status != AccountApplication.STATUS_APPROVED:
                raise ValidationError("Your account application has not been approved.", code='not_approved')
        super().confirm_login_allowed(user)


class UserRegistrationForm(UserCreationForm):
    """
    Public registration form supporting:
    - Citizen accounts (immediate activation upon submission).
    - Authority Officer applications (requires Admin approval & verified department ID).
    - Forest Ranger applications (requires Admin approval, verified credential, & dispatch coords).
    Platform Administrator accounts CANNOT be registered publicly.
    """
    ROLE_CHOICES = [
        (UserProfile.ROLE_CITIZEN, 'Citizen / General Public'),
        (UserProfile.ROLE_RANGER, 'Forest Ranger (Field Responder Application)'),
        (UserProfile.ROLE_AUTHORITY, 'Authority Officer (Dispatch & Verification Application)'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial=UserProfile.ROLE_CITIZEN,
        widget=forms.RadioSelect(attrs={'class': 'auth-role-radio'}),
        required=False
    )
    email = forms.EmailField(
        required=True,
        label="Email address",
        help_text="Required. Used for account communications and safety alerts.",
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
    phone_number = forms.CharField(
        max_length=20, required=False, label="Phone number",
        help_text="Contact number for incident response and safety alerts.",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': '+91 98765 43210',
            'autocomplete': 'tel',
            'id': 'id_phone_number',
        })
    )
    organization = forms.CharField(
        max_length=150, required=False, label="Organization / Agency / Department",
        help_text="Department, Division, Wildlife Sanctuary, or Agency.",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'e.g. Kerala Forest & Wildlife Dept',
            'id': 'id_organization',
        })
    )
    assigned_region = forms.CharField(
        max_length=150, required=False, label="Assigned District / Division",
        help_text="Operational District / Division (e.g. Kollam District).",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'e.g. Kollam District',
            'id': 'id_assigned_region',
        })
    )
    supporting_document = forms.FileField(
        required=False, label="Official ID / Authorization Document",
        help_text="Department ID badge, government authorization letter, or official credential (PDF, JPEG, or PNG up to 5 MB).",
        widget=forms.FileInput(attrs={
            'class': 'auth-form-control',
            'id': 'id_supporting_document',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
    )

    # --- Location fields (for Citizen area mapping and Ranger dispatch) ---
    registered_location = forms.CharField(
        max_length=150, required=False, label="Operational Base / District",
        help_text="District, town, or city (e.g. Kollam).",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control',
            'placeholder': 'e.g. Kollam, Kerala',
            'id': 'id_registered_location',
        })
    )
    latitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Latitude",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control form-control-sm',
            'placeholder': 'e.g. 8.8932',
            'id': 'id_latitude',
            'step': 'any'
        })
    )
    longitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Longitude",
        widget=forms.TextInput(attrs={
            'class': 'auth-form-control form-control-sm',
            'placeholder': 'e.g. 76.6141',
            'id': 'id_longitude',
            'step': 'any'
        })
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

    def _posted_role(self):
        role = self.cleaned_data.get('role')
        if not role and hasattr(self, 'data'):
            role = self.data.get('role')
        return role or (self.initial.get('role') if isinstance(self.initial, dict) else None)

    def clean_role(self):
        role = self.cleaned_data.get('role') or UserProfile.ROLE_CITIZEN
        if role not in [UserProfile.ROLE_CITIZEN, UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY]:
            raise ValidationError("Invalid role. Administrator accounts cannot be registered publicly.")
        return role

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        role = self._posted_role()
        if not phone:
            if role in (UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY):
                raise ValidationError("Official Authority and Ranger applications must provide a contact phone number.")
            return ''
        if not re.match(r'^\+?[0-9][0-9\s\-().]{5,19}$', phone):
            raise ValidationError(
                "Enter a valid phone number (digits only, optional leading +, 6-20 characters)."
            )
        digits = re.sub(r'\D', '', phone)
        if not (6 <= len(digits) <= 14):
            raise ValidationError("Phone number must contain 6 to 14 digits.")
        return phone

    def clean_organization(self):
        org = self.cleaned_data.get('organization', '').strip()
        role = self._posted_role()
        if role == UserProfile.ROLE_AUTHORITY and not org:
            raise ValidationError("Authority Officer applicants must specify their organization or department.")
        return org

    def clean_supporting_document(self):
        doc = self.cleaned_data.get('supporting_document')
        role = self._posted_role()
        if role in (UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY):
            if not doc:
                raise ValidationError(
                    "Official Authority and Ranger applications must include a supporting department ID or authorization document."
                )
            if doc.size > 5 * 1024 * 1024:
                raise ValidationError("Supporting document must not exceed 5 MB in file size.")
            ext = os.path.splitext(doc.name)[1].lower()
            if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
                raise ValidationError("Only PDF, JPEG, and PNG files are accepted.")
            # Verify magic bytes/header
            header = doc.read(16)
            doc.seek(0)
            is_pdf = header.startswith(b'%PDF')
            is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
            is_jpeg = header.startswith(b'\xff\xd8\xff')
            if not (is_pdf or is_png or is_jpeg):
                raise ValidationError("Invalid file format. Please upload a genuine, non-corrupted PDF, JPEG, or PNG document.")
        return doc

    def clean_registered_location(self):
        loc = self.cleaned_data.get('registered_location', '').strip()
        role = self._posted_role()
        if role == UserProfile.ROLE_RANGER and not loc:
            raise ValidationError("Forest Ranger applications must specify a registered operational location (e.g. Kollam).")
        if loc and not re.match(r"^[A-Za-z0-9][A-Za-z0-9 .,'\-/#()]*$", loc):
            raise ValidationError("Location may only contain letters, numbers, spaces, and punctuation.")
        return loc

    def _clean_coord(self, value, field_name, lo, hi):
        if value is None:
            return None
        v = float(value)
        if not (lo <= v <= hi):
            raise ValidationError(f"{field_name} must be between {lo} and {hi}.")
        return round(v, 6)

    KERALA_LOCATION_COORDINATES = {
        'thiruvananthapuram': (8.5241, 76.9366),
        'trivandrum': (8.5241, 76.9366),
        'kollam': (8.8932, 76.6141),
        'pathanamthitta': (9.2648, 76.7870),
        'alappuzha': (9.4981, 76.3388),
        'alleppey': (9.4981, 76.3388),
        'kottayam': (9.5916, 76.5222),
        'idukki': (9.8500, 76.9700),
        'ernakulam': (9.9816, 76.2999),
        'kochi': (9.9816, 76.2999),
        'cochin': (9.9816, 76.2999),
        'thrissur': (10.5276, 76.2144),
        'trichur': (10.5276, 76.2144),
        'palakkad': (10.7867, 76.6548),
        'malappuram': (11.0732, 76.0740),
        'kozhikode': (11.2588, 75.7804),
        'calicut': (11.2588, 75.7804),
        'wayanad': (11.6050, 76.0829),
        'kalpetta': (11.6050, 76.0829),
        'kannur': (11.8745, 75.3704),
        'cannore': (11.8745, 75.3704),
        'kasaragod': (12.5102, 74.9852),
        'punalur': (9.0167, 76.9167),
        'munnar': (10.0889, 77.0595),
        'kottarakkara': (9.0000, 76.7667),
        'sulthan bathery': (11.6634, 76.2573),
        'mananthavady': (11.8026, 76.0033),
    }

    def _resolve_location_coords(self, loc_text):
        if not loc_text:
            return None, None
        norm = loc_text.lower().replace(',', ' ').replace('-', ' ').replace('/', ' ')
        words = [w.strip() for w in norm.split() if len(w.strip()) >= 3]
        for key, (lat, lon) in self.KERALA_LOCATION_COORDINATES.items():
            if key in norm or any(w in key for w in words):
                return lat, lon
        return None, None

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is None or lat == '':
            return None
        return self._clean_coord(lat, "Latitude", -90.0, 90.0)

    def clean_longitude(self):
        lon = self.cleaned_data.get('longitude')
        if lon is None or lon == '':
            return None
        return self._clean_coord(lon, "Longitude", -180.0, 180.0)

    def clean(self):
        cleaned_data = super().clean()
        role = self._posted_role()
        loc = (cleaned_data.get('registered_location') or '').strip()
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')

        if role == UserProfile.ROLE_RANGER:
            # Ranger must specify either a location name or coordinates
            if not loc and (lat is None or lon is None):
                self.add_error('registered_location', "Forest Ranger applications must specify a registered operational location (e.g. Kollam) or coordinates.")

            # If user entered a manual location name without explicit coordinates,
            # auto-resolve coordinates for proximity dispatch from known locations
            if (lat is None or lon is None) and loc:
                res_lat, res_lon = self._resolve_location_coords(loc)
                if res_lat is not None and res_lon is not None:
                    cleaned_data['latitude'] = res_lat
                    cleaned_data['longitude'] = res_lon
                    lat = res_lat
                    lon = res_lon

            # If only one coordinate is provided, require both
            if (lat is not None and lon is None) or (lat is None and lon is not None):
                self.add_error('latitude', "Both base latitude and longitude must be provided together.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role', UserProfile.ROLE_CITIZEN)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '').strip()
        user.last_name = self.cleaned_data.get('last_name', '').strip()

        # Official applications remain inactive until approved by Admin
        if role in (UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY):
            user.is_active = False
        else:
            user.is_active = True

        if commit:
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.full_name = " ".join(n for n in [user.first_name, user.last_name] if n).strip() or None
        profile.phone_number = self.cleaned_data.get('phone_number', '').strip() or None
        profile.organization = self.cleaned_data.get('organization', '').strip() or None
        profile.assigned_region = self.cleaned_data.get('assigned_region', '').strip() or None
        profile.registered_location = self.cleaned_data.get('registered_location', '').strip() or None
        profile.latitude = self.cleaned_data.get('latitude')
        profile.longitude = self.cleaned_data.get('longitude')
        profile.account_status = UserProfile.ACCOUNT_ACTIVE
        if commit:
            profile.save()

        user.profile = profile

        # Create AccountApplication for Ranger and Authority applicants
        if role in (UserProfile.ROLE_RANGER, UserProfile.ROLE_AUTHORITY):
            app = AccountApplication.objects.create(
                user=user,
                requested_role=role,
                full_name=profile.display_name,
                phone_number=profile.phone_number or '',
                organization=profile.organization,
                assigned_region=profile.assigned_region,
                registered_location=profile.registered_location,
                latitude=profile.latitude,
                longitude=profile.longitude,
                supporting_document=self.cleaned_data.get('supporting_document'),
                status=AccountApplication.STATUS_PENDING
            )
            AuditLog.record(
                actor=user,
                action='APPLICATION_SUBMITTED',
                target_type='AccountApplication',
                target_id=app.pk,
                target_repr=f"Application #{app.pk} - {user.username} ({role})",
                details=f"Submitted application for {role.title()} role. Org: {profile.organization}"
            )
            # Notify platform administrators
            for admin_u in User.objects.filter(Q(is_superuser=True) | Q(profile__role=UserProfile.ROLE_ADMIN), is_active=True).distinct():
                Notification.send(
                    recipient=admin_u,
                    actor=user,
                    title="New Account Application",
                    message=f"New {role.title()} application received from {profile.display_name} ({user.username}). Administrative review required.",
                    notification_type=Notification.TYPE_WARNING,
                    link=reverse('accounts:admin_provision')
                )

        return user


class UserProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150, required=False, label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Full Name', 'id': 'id_profile_full_name'})
    )
    email = forms.EmailField(
        required=True, label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'user@example.com', 'id': 'id_profile_email'})
    )
    phone_number = forms.CharField(
        max_length=20, required=False, label="Contact Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210', 'id': 'id_profile_phone'})
    )
    registered_location = forms.CharField(
        max_length=150, required=False, label="Residential District / City / Landmark",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ernakulam, Kerala', 'id': 'id_registered_location'})
    )
    latitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Latitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '9.9312', 'step': 'any', 'id': 'id_profile_latitude'})
    )
    longitude = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False, label="Longitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '76.2673', 'step': 'any', 'id': 'id_profile_longitude'})
    )
    availability = forms.ChoiceField(
        choices=UserProfile.AVAILABILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'organization', 'assigned_region',
                  'registered_location', 'latitude', 'longitude', 'availability']
        widgets = {
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Wildlife Protection Dept'}),
            'assigned_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Western Ghats Sector 4'}),
            'registered_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kollam District HQ', 'id': 'id_registered_location'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8.8932', 'step': 'any', 'id': 'id_profile_latitude'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '76.6141', 'step': 'any', 'id': 'id_profile_longitude'}),
            'availability': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            if self.instance.role == UserProfile.ROLE_ADMIN:
                for fld in ['organization', 'assigned_region', 'registered_location', 'latitude', 'longitude', 'availability']:
                    if fld in self.fields:
                        del self.fields[fld]
            if self.instance.user:
                self.fields['email'].initial = self.instance.user.email
                self.fields['full_name'].initial = self.instance.full_name or self.instance.user.get_full_name()
            if self.instance.phone_number:
                self.fields['phone_number'].initial = self.instance.phone_number
            if 'registered_location' in self.fields and self.instance.registered_location:
                self.fields['registered_location'].initial = self.instance.registered_location
            if 'latitude' in self.fields and self.instance.latitude is not None:
                self.fields['latitude'].initial = self.instance.latitude
            if 'longitude' in self.fields and self.instance.longitude is not None:
                self.fields['longitude'].initial = self.instance.longitude

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if self.instance and self.instance.user:
            if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user.pk).exists():
                raise ValidationError("This email address is already in use by another account.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not phone:
            return ''
        if not re.match(r'^\+?[0-9][0-9\s\-().]{5,19}$', phone):
            raise ValidationError("Enter a valid phone number (digits, optional leading +).")
        digits = re.sub(r'\D', '', phone)
        if not (6 <= len(digits) <= 14):
            raise ValidationError("Phone number must contain 6 to 14 digits.")
        return phone

    def _clean_coord(self, value, field_name, lo, hi):
        if value is None:
            return None
        v = float(value)
        if not (lo <= v <= hi):
            raise ValidationError(f"{field_name} must be between {lo} and {hi}.")
        return round(v, 6)

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is None:
            return None
        return self._clean_coord(lat, "Latitude", -90.0, 90.0)

    def clean_longitude(self):
        lon = self.cleaned_data.get('longitude')
        if lon is None:
            return None
        return self._clean_coord(lon, "Longitude", -180.0, 180.0)

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        if user:
            fn = self.cleaned_data.get('full_name', '').strip()
            profile.full_name = fn or None
            if fn:
                parts = fn.split(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ''
            email = self.cleaned_data.get('email', '').strip().lower()
            if email:
                user.email = email
            if commit:
                user.save()
        phone = self.cleaned_data.get('phone_number', '').strip()
        profile.phone_number = phone or None
        reg_loc = self.cleaned_data.get('registered_location', '').strip()
        profile.registered_location = reg_loc or None
        profile.latitude = self.cleaned_data.get('latitude')
        profile.longitude = self.cleaned_data.get('longitude')
        if commit:
            profile.save()
        if user:
            user.profile = profile
        return profile



class AdminAuthorityProvisionForm(forms.ModelForm):
    """Platform Admin form specifically for provisioning Authority Officer accounts."""
    full_name = forms.CharField(
        max_length=150, required=False, label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dr. Rajesh Kumar', 'id': 'id_auth_full_name'})
    )
    username = forms.CharField(
        max_length=150, required=True, label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. authority_kollam_hq', 'id': 'id_auth_username'})
    )
    email = forms.EmailField(
        required=True, label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'officer@venomwatch.gov', 'id': 'id_auth_email'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 94471 23456', 'id': 'id_auth_phone_number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create secure password', 'id': 'id_auth_password'}),
        required=True, label="Temporary Password", min_length=6
    )
    organization = forms.CharField(
        max_length=100, required=False, label="Organization / Department",
        initial="Kerala Forest & Wildlife Department",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kerala Forest & Wildlife Dept', 'id': 'id_auth_organization'})
    )
    assigned_region = forms.CharField(
        max_length=100, required=False, label="Assigned Region or District",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kollam District HQ', 'id': 'id_auth_assigned_region'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[A-Za-z][A-Za-z0-9._@+-]{2,29}$', username):
            raise ValidationError(
                "Username must be 3-30 characters, start with a letter, and contain only letters, digits, and . _ + - @."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(f"A user with username '{username}' already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(f"An account with email '{email}' already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not re.match(r'^\+?[0-9][0-9\s\-().]{6,19}$', phone):
            raise ValidationError("Enter a valid contact phone number (e.g. +91 94471 23456).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        full_name = cleaned_data.get('full_name') or ''
        first_name = self.data.get('first_name', '').strip()
        last_name = self.data.get('last_name', '').strip()
        if not full_name and (first_name or last_name):
            cleaned_data['full_name'] = f"{first_name} {last_name}".strip()
        elif not full_name:
            self.add_error('full_name', "Full name is required.")

        region = cleaned_data.get('assigned_region') or self.data.get('registered_location', '').strip()
        if not region:
            self.add_error('assigned_region', "Assigned region or district is required.")
        else:
            cleaned_data['assigned_region'] = region
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        full_name = self.cleaned_data.get('full_name', '').strip()
        first_name = self.data.get('first_name', '').strip()
        last_name = self.data.get('last_name', '').strip()
        if first_name or last_name:
            user.first_name = first_name
            user.last_name = last_name
        elif full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        if commit:
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_AUTHORITY
        profile.full_name = full_name or user.get_full_name() or user.username
        profile.phone_number = self.cleaned_data['phone_number']
        profile.organization = self.cleaned_data.get('organization') or 'Kerala Forest & Wildlife Department'
        region = self.cleaned_data.get('assigned_region') or 'Statewide'
        profile.assigned_region = region
        profile.registered_location = region
        profile.availability = UserProfile.AVAILABILITY_AVAILABLE
        profile.save()
        return user


class AdminRangerProvisionForm(forms.ModelForm):
    """Platform Admin form specifically for provisioning Forest Ranger field responder accounts."""
    full_name = forms.CharField(
        max_length=150, required=False, label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Suresh Gopi', 'id': 'id_ranger_full_name'})
    )
    username = forms.CharField(
        max_length=150, required=True, label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ranger_kollam_01', 'id': 'id_ranger_username'})
    )
    email = forms.EmailField(
        required=True, label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ranger.kollam@venomwatch.gov', 'id': 'id_ranger_email'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True, label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98472 54321', 'id': 'id_ranger_phone_number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create secure password', 'id': 'id_ranger_password'}),
        required=True, label="Temporary Password", min_length=6
    )
    organization = forms.CharField(
        max_length=100, required=False, label="Organization / Unit",
        initial="Kerala Forest Quick Response Team",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Forest Quick Response Team', 'id': 'id_ranger_organization'})
    )
    assigned_region = forms.CharField(
        max_length=100, required=False, label="Assigned Region / District",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kollam Forest Division', 'id': 'id_ranger_assigned_region'})
    )
    registered_location = forms.CharField(
        max_length=150, required=False, label="Registered Operational Location",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kollam Base Station', 'id': 'id_ranger_registered_location'})
    )
    latitude = forms.FloatField(
        required=False, label="Base Latitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8.8932', 'step': 'any', 'id': 'id_ranger_latitude'})
    )
    longitude = forms.FloatField(
        required=False, label="Base Longitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '76.6141', 'step': 'any', 'id': 'id_ranger_longitude'})
    )
    availability = forms.ChoiceField(
        choices=UserProfile.AVAILABILITY_CHOICES,
        initial=UserProfile.AVAILABILITY_AVAILABLE,
        label="Initial Availability",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_ranger_availability'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[A-Za-z][A-Za-z0-9._@+-]{2,29}$', username):
            raise ValidationError(
                "Username must be 3-30 characters, start with a letter, and contain only letters, digits, and . _ + - @."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(f"A user with username '{username}' already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(f"An account with email '{email}' already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not re.match(r'^\+?[0-9][0-9\s\-().]{6,19}$', phone):
            raise ValidationError("Enter a valid contact phone number (e.g. +91 98472 54321).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        full_name = cleaned_data.get('full_name') or ''
        first_name = self.data.get('first_name', '').strip()
        last_name = self.data.get('last_name', '').strip()
        if not full_name and (first_name or last_name):
            cleaned_data['full_name'] = f"{first_name} {last_name}".strip()
        elif not full_name:
            self.add_error('full_name', "Full name is required.")

        location = cleaned_data.get('registered_location') or self.data.get('registered_location', '').strip()
        region = cleaned_data.get('assigned_region') or self.data.get('assigned_region', '').strip() or location
        if not location:
            location = region
        if not location:
            self.add_error('registered_location', "Registered operational location is required.")
        cleaned_data['registered_location'] = location
        cleaned_data['assigned_region'] = region or location

        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')
        if lat is not None and (lat < -90.0 or lat > 90.0):
            self.add_error('latitude', "Latitude must be between -90.0 and 90.0 degrees.")
        if lng is not None and (lng < -180.0 or lng > 180.0):
            self.add_error('longitude', "Longitude must be between -180.0 and 180.0 degrees.")
        if (lat is not None and lng is None) or (lat is None and lng is not None):
            self.add_error('latitude', "Both base latitude and longitude must be provided together.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        full_name = self.cleaned_data.get('full_name', '').strip()
        first_name = self.data.get('first_name', '').strip()
        last_name = self.data.get('last_name', '').strip()
        if first_name or last_name:
            user.first_name = first_name
            user.last_name = last_name
        elif full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        if commit:
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = UserProfile.ROLE_RANGER
        profile.full_name = full_name or user.get_full_name() or user.username
        profile.phone_number = self.cleaned_data['phone_number']
        profile.organization = self.cleaned_data.get('organization') or 'Kerala Forest Quick Response Team'
        profile.registered_location = self.cleaned_data['registered_location']
        profile.assigned_region = self.cleaned_data.get('assigned_region') or self.cleaned_data['registered_location']
        profile.latitude = self.cleaned_data.get('latitude')
        profile.longitude = self.cleaned_data.get('longitude')
        profile.availability = self.cleaned_data.get('availability', UserProfile.AVAILABILITY_AVAILABLE)
        profile.save()
        return user


class AdminAccountProvisionForm(forms.ModelForm):
    """Platform Admin form to provision Authority Officers and Field Rangers (unified/backward-compatible)."""
    full_name = forms.CharField(
        max_length=150, required=False, label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Full Official Name'})
    )
    username = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. ranger_kollam_01'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'officer@venomwatch.gov'})
    )
    first_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Last Name'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Temporary Password'}),
        required=True
    )
    role = forms.ChoiceField(
        choices=[
            (UserProfile.ROLE_AUTHORITY, 'Authority Officer (Surveillance & Dispatch Console)'),
            (UserProfile.ROLE_RANGER, 'Forest Ranger / Field Responder (Ranger Console)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '+91 98765 43210'})
    )
    organization = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. Kerala Forest & Wildlife Dept'})
    )
    registered_location = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. Kollam Forest Division'})
    )
    assigned_region = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. Kollam District HQ'})
    )
    latitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '8.8932', 'step': 'any'})
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '76.6141', 'step': 'any'})
    )
    availability = forms.ChoiceField(
        choices=UserProfile.AVAILABILITY_CHOICES,
        initial=UserProfile.AVAILABILITY_AVAILABLE,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not re.match(r'^[A-Za-z][A-Za-z0-9._@+-]{2,29}$', username):
            raise ValidationError(
                "Username must be 3-30 characters, start with a letter, and contain only letters, digits, and . _ + - @."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(f"A user with username '{username}' already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(f"An account with email '{email}' already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip()
        if not re.match(r'^\+?[0-9][0-9\s\-().]{6,19}$', phone):
            raise ValidationError("Enter a valid phone number (digits, optional leading +, 7-20 chars).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        loc = cleaned_data.get('registered_location') or cleaned_data.get('assigned_region')
        if not loc:
            cleaned_data['registered_location'] = 'Operational Base'
            cleaned_data['assigned_region'] = 'Operational Base'
        else:
            cleaned_data['registered_location'] = loc
            cleaned_data['assigned_region'] = loc
        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')
        if lat is not None and (lat < -90.0 or lat > 90.0):
            self.add_error('latitude', "Latitude must be between -90.0 and 90.0 degrees.")
        if lng is not None and (lng < -180.0 or lng > 180.0):
            self.add_error('longitude', "Longitude must be between -180.0 and 180.0 degrees.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        fn = self.cleaned_data.get('first_name', '').strip()
        ln = self.cleaned_data.get('last_name', '').strip()
        full_name = self.cleaned_data.get('full_name', '').strip()
        if not fn and full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        else:
            user.first_name = fn
            user.last_name = ln
        if commit:
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data['role']
        profile.full_name = full_name or user.get_full_name() or user.username
        profile.phone_number = self.cleaned_data['phone_number']
        profile.organization = self.cleaned_data.get('organization') or None
        loc = self.cleaned_data.get('registered_location') or self.cleaned_data.get('assigned_region') or 'Operational Base'
        profile.registered_location = loc
        profile.assigned_region = self.cleaned_data.get('assigned_region') or loc
        profile.latitude = self.cleaned_data.get('latitude')
        profile.longitude = self.cleaned_data.get('longitude')
        profile.availability = self.cleaned_data.get('availability', UserProfile.AVAILABILITY_AVAILABLE)
        profile.save()
        return user


class AdminAccountEditForm(forms.Form):
    """
    Platform Admin form to edit an existing Authority or Ranger account's
    operational parameters, contact details, coordinates, and active status.
    """
    full_name = forms.CharField(
        max_length=150, required=False, label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Officer Name', 'id': 'id_edit_full_name'})
    )
    email = forms.EmailField(
        required=True, label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'officer@venomwatch.gov', 'id': 'id_edit_email'})
    )
    phone_number = forms.CharField(
        max_length=20, required=True, label="Contact Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 94471 23456', 'id': 'id_edit_phone'})
    )
    organization = forms.CharField(
        max_length=100, required=False, label="Organization / Department",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kerala Forest & Wildlife Dept', 'id': 'id_edit_organization'})
    )
    assigned_region = forms.CharField(
        max_length=100, required=False, label="Assigned Region / District",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kollam District HQ', 'id': 'id_edit_region'})
    )
    registered_location = forms.CharField(
        max_length=150, required=False, label="Registered Operational Base",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Range Forest Office', 'id': 'id_edit_location'})
    )
    latitude = forms.FloatField(
        required=False, label="Operational Base Latitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8.8932', 'step': 'any', 'id': 'id_edit_lat'})
    )
    longitude = forms.FloatField(
        required=False, label="Operational Base Longitude",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '76.6141', 'step': 'any', 'id': 'id_edit_lng'})
    )
    availability = forms.ChoiceField(
        choices=UserProfile.AVAILABILITY_CHOICES, required=False, label="Field Availability Status",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_edit_availability'})
    )
    account_status = forms.ChoiceField(
        choices=UserProfile.ACCOUNT_STATUS_CHOICES, required=False, label="Account Operational Status",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_edit_account_status'})
    )
    suspension_reason = forms.CharField(
        max_length=500, required=False, label="Suspension / Ban Rationale",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason for administrative suspension or ban...', 'id': 'id_edit_suspension_reason'})
    )
    is_active = forms.BooleanField(
        required=False, label="Account Active Status (Login Access)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_edit_is_active'})
    )
    new_password = forms.CharField(
        required=False, label="Reset Password (leave blank to keep existing password)",
        min_length=6,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password only if resetting', 'id': 'id_edit_password'})
    )

    def __init__(self, target_user, *args, admin_user=None, **kwargs):
        self.target_user = target_user
        self.admin_user = admin_user
        self.profile = getattr(target_user, 'profile', None)
        initial = kwargs.get('initial', {})
        initial.update({
            'full_name': (self.profile.full_name if self.profile and self.profile.full_name else target_user.get_full_name()) or target_user.username,
            'email': target_user.email,
            'phone_number': self.profile.phone_number if self.profile else '',
            'organization': self.profile.organization if self.profile else '',
            'assigned_region': self.profile.assigned_region if self.profile else '',
            'registered_location': self.profile.registered_location if self.profile else '',
            'latitude': self.profile.latitude if self.profile else None,
            'longitude': self.profile.longitude if self.profile else None,
            'availability': self.profile.availability if self.profile else UserProfile.AVAILABILITY_AVAILABLE,
            'account_status': self.profile.account_status if self.profile else UserProfile.ACCOUNT_ACTIVE,
            'suspension_reason': self.profile.suspension_reason if self.profile else '',
            'is_active': target_user.is_active,
        })
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.target_user.pk).exists():
            raise ValidationError(f"An account with email '{email}' already exists.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not re.match(r'^\+?[0-9][0-9\s\-().]{6,19}$', phone):
            raise ValidationError("Enter a valid phone number (digits, optional leading +, 7-20 chars).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        if self.profile and self.profile.role in [UserProfile.ROLE_AUTHORITY, UserProfile.ROLE_RANGER]:
            raise ValidationError(
                "Security Policy Violation: Platform Administrators are strictly prohibited from editing "
                "Authority or Ranger personal and operational profile details."
            )

        lat = cleaned_data.get('latitude')
        lng = cleaned_data.get('longitude')
        is_act = cleaned_data.get('is_active')
        acc_status = cleaned_data.get('account_status')
        susp_reason = cleaned_data.get('suspension_reason', '').strip()

        if lat is not None and (lat < -90.0 or lat > 90.0):
            self.add_error('latitude', "Latitude must be between -90.0 and 90.0 degrees.")
        if lng is not None and (lng < -180.0 or lng > 180.0):
            self.add_error('longitude', "Longitude must be between -180.0 and 180.0 degrees.")

        # Require a clear reason if suspending or banning
        if acc_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED] and not susp_reason:
            self.add_error('suspension_reason', "A documented reason is required when placing an account on Suspended or Banned status.")

        # Prevent admin self-deactivation/self-suspension
        if self.admin_user and self.admin_user.pk == self.target_user.pk:
            if not is_act:
                self.add_error('is_active', "Security Policy Violation: You cannot deactivate your own admin account.")
            if acc_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED]:
                self.add_error('account_status', "Security Policy Violation: You cannot suspend or ban your own admin account.")

        # Prevent deactivating the last active administrator
        if (not is_act or acc_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED]) and (self.target_user.is_superuser or (self.profile and self.profile.is_admin)):
            active_admins = User.objects.filter(is_active=True).filter(
                Q(is_superuser=True) | Q(profile__role=UserProfile.ROLE_ADMIN)
            ).filter(profile__account_status=UserProfile.ACCOUNT_ACTIVE).distinct().count()
            if active_admins <= 1:
                self.add_error('account_status', "Security Policy Violation: Cannot deactivate or suspend the last remaining active administrator.")

        return cleaned_data

    def save(self):
        from django.utils import timezone
        cd = self.cleaned_data
        self.target_user.email = cd['email']
        fn = cd.get('full_name', '').strip()
        if fn:
            parts = fn.split(' ', 1)
            self.target_user.first_name = parts[0]
            self.target_user.last_name = parts[1] if len(parts) > 1 else ''

        acc_status = cd.get('account_status', UserProfile.ACCOUNT_ACTIVE)
        susp_reason = cd.get('suspension_reason', '').strip() or None

        # If suspended or banned, login access is disabled
        if acc_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED]:
            self.target_user.is_active = False
        else:
            self.target_user.is_active = cd['is_active']

        new_pwd = cd.get('new_password')
        if new_pwd:
            self.target_user.set_password(new_pwd)
        self.target_user.save()

        if self.profile:
            prev_status = self.profile.account_status
            self.profile.full_name = fn or self.target_user.username
            self.profile.phone_number = cd['phone_number']
            self.profile.organization = cd.get('organization') or None
            self.profile.assigned_region = cd.get('assigned_region') or None
            self.profile.registered_location = cd.get('registered_location') or None
            self.profile.latitude = cd.get('latitude')
            self.profile.longitude = cd.get('longitude')
            if cd.get('availability'):
                self.profile.availability = cd['availability']

            self.profile.account_status = acc_status
            if acc_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED]:
                self.profile.suspension_reason = susp_reason
                self.profile.suspended_by = self.admin_user
                self.profile.suspended_at = timezone.now()
            elif prev_status in [UserProfile.ACCOUNT_SUSPENDED, UserProfile.ACCOUNT_BANNED] and acc_status == UserProfile.ACCOUNT_ACTIVE:
                self.profile.suspension_reason = None
                self.profile.suspended_by = None
                self.profile.suspended_at = None

            self.profile.save()

            # Record audit log if status changed
            if prev_status != acc_status:
                action_name = 'ACCOUNT_REINSTATED' if acc_status == UserProfile.ACCOUNT_ACTIVE else ('ACCOUNT_BANNED' if acc_status == UserProfile.ACCOUNT_BANNED else 'ACCOUNT_SUSPENDED')
                AuditLog.record(
                    actor=self.admin_user,
                    action=action_name,
                    target_type='UserProfile',
                    target_id=self.profile.pk,
                    target_repr=f"User {self.target_user.username} ({self.profile.get_role_display()})",
                    details=f"Status transitioned from {prev_status} to {acc_status}. Rationale: {susp_reason}"
                )
                Notification.send(
                    recipient=self.target_user,
                    actor=self.admin_user,
                    title=f"Account Status Update: {acc_status}",
                    message=f"Your account status has been updated to {acc_status} by platform administration.{' Reason: ' + susp_reason if susp_reason else ''}",
                    notification_type=Notification.TYPE_DANGER if acc_status != UserProfile.ACCOUNT_ACTIVE else Notification.TYPE_SUCCESS
                )

        return self.target_user


