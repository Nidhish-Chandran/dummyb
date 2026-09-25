from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CITIZEN = 'citizen'
    ROLE_RANGER = 'ranger'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_CITIZEN, 'Citizen / General Public'),
        (ROLE_RANGER, 'Forest Ranger / Wildlife Authority'),
        (ROLE_ADMIN, 'Platform Administrator'),
    ]

    # Roles a visitor may self-register for. Ranger/Admin accounts are
    # provisioned by an existing administrator (Django admin or seed script).
    SELF_SERVICE_ROLES = [ROLE_CITIZEN]

    AVAILABILITY_AVAILABLE = 'AVAILABLE'
    AVAILABILITY_BUSY = 'BUSY'
    AVAILABILITY_OFFLINE = 'OFFLINE'

    AVAILABILITY_CHOICES = [
        (AVAILABILITY_AVAILABLE, 'Available'),
        (AVAILABILITY_BUSY, 'Busy (on active assignment)'),
        (AVAILABILITY_OFFLINE, 'Offline'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CITIZEN)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    organization = models.CharField(max_length=100, blank=True, null=True, help_text="Department, Hospital, or Agency")
    assigned_region = models.CharField(max_length=100, blank=True, null=True, help_text="Operational District/Region")

    # --- Ranger operational base (location-based dispatch) ---
    registered_location = models.CharField(max_length=150, blank=True, null=True,
                                           help_text="Ranger's registered operational town/city (e.g. Kollam)")
    latitude = models.FloatField(null=True, blank=True, help_text="Ranger base latitude (decimal degrees)")
    longitude = models.FloatField(null=True, blank=True, help_text="Ranger base longitude (decimal degrees)")
    availability = models.CharField(max_length=10, choices=AVAILABILITY_CHOICES,
                                    default=AVAILABILITY_AVAILABLE)

    @property
    def display_name(self):
        full = self.user.get_full_name().strip()
        return full or self.user.username

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def effective_role(self):
        """Superusers are always treated as Platform Administrators."""
        if self.user.is_superuser:
            return self.ROLE_ADMIN
        return self.role

    @property
    def is_citizen(self):
        return self.effective_role == self.ROLE_CITIZEN

    @property
    def is_ranger(self):
        return self.effective_role == self.ROLE_RANGER

    @property
    def is_admin(self):
        return self.effective_role == self.ROLE_ADMIN

    # --- Backwards-compatible aliases used across reports/hotspots/dashboard ---
    @property
    def is_authority(self):
        return self.is_ranger or self.is_admin

    @property
    def is_responder(self):
        return self.is_ranger or self.is_admin


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
