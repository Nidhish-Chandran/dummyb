from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Used for emergency notifications.")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, initial=UserProfile.ROLE_CITIZEN, help_text="Select your primary platform role.")
    phone_number = forms.CharField(max_length=20, required=False, help_text="Contact number for emergency verification.")
    organization = forms.CharField(max_length=100, required=False, help_text="Department, Hospital, or Agency (if applicable).")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data.get('role')
        profile.phone_number = self.cleaned_data.get('phone_number')
        profile.organization = self.cleaned_data.get('organization')
        profile.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'organization', 'assigned_region']
