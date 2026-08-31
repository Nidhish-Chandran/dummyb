from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CITIZEN = 'citizen'
    ROLE_AUTHORITY = 'authority'
    ROLE_RESPONDER = 'responder'
    
    ROLE_CHOICES = [
        (ROLE_CITIZEN, 'Citizen / General Public'),
        (ROLE_AUTHORITY, 'Forest Officer / Wildlife Authority'),
        (ROLE_RESPONDER, 'Medical / Emergency Responder'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CITIZEN)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    organization = models.CharField(max_length=100, blank=True, null=True, help_text="Department, Hospital, or Agency")
    assigned_region = models.CharField(max_length=100, blank=True, null=True, help_text="Operational District/Region")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_authority(self):
        return self.role == self.ROLE_AUTHORITY or self.user.is_superuser

    @property
    def is_responder(self):
        return self.role in [self.ROLE_RESPONDER, self.ROLE_AUTHORITY] or self.user.is_superuser


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
