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

    def clean(self):
        # Override only the message text; keep Django's own flow intact.
        return super().clean()


class UserRegistrationForm(UserCreationForm):
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
        max_length=150, required=False, label="First name (optional)",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150, required=False, label="Last name (optional)",
        widget=forms.TextInput(attrs={'class': 'auth-form-control', 'placeholder': 'Last name'})
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial=UserProfile.ROLE_CITIZEN,
        label="Account type",
        help_text="Ranger and Administrator accounts are created by an administrator.",
        widget=forms.Select(attrs={"class": "auth-form-control auth-form-select"})
    )
    phone_number = forms.CharField(
        max_length=20, required=False, label="Phone number",
        help_text="Optional contact number for emergency verification.",
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

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if phone and not re.match(r'^\+?[0-9][0-9\s\-().]{5,19}$', phone):
            raise ValidationError(
                "Enter a valid phone number (digits only, optional leading +, 6-20 characters)."
            )
        return phone

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in UserProfile.SELF_SERVICE_ROLES:
            raise ValidationError(
                "Only Citizen accounts can self-register. Ranger and Administrator "
                "accounts must be created by a platform administrator."
            )
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data.get('role', UserProfile.ROLE_CITIZEN)
        profile.phone_number = self.cleaned_data.get('phone_number') or None
        profile.organization = self.cleaned_data.get('organization') or None
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
