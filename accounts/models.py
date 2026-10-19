from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta


class UserProfile(models.Model):
    ROLE_CITIZEN = 'citizen'
    ROLE_RANGER = 'ranger'
    ROLE_AUTHORITY = 'authority'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_CITIZEN, 'Citizen / General Public'),
        (ROLE_RANGER, 'Forest Ranger (Field Responder)'),
        (ROLE_AUTHORITY, 'Authority Officer (Dispatch & Verification)'),
        (ROLE_ADMIN, 'Platform Administrator'),
    ]

    # Roles a visitor may apply/register for
    SELF_SERVICE_ROLES = [ROLE_CITIZEN, ROLE_RANGER, ROLE_AUTHORITY]

    AVAILABILITY_AVAILABLE = 'AVAILABLE'
    AVAILABILITY_BUSY = 'BUSY'
    AVAILABILITY_OFFLINE = 'OFFLINE'

    AVAILABILITY_CHOICES = [
        (AVAILABILITY_AVAILABLE, 'Available'),
        (AVAILABILITY_BUSY, 'Busy (on active assignment)'),
        (AVAILABILITY_OFFLINE, 'Offline'),
    ]

    ACCOUNT_ACTIVE = 'ACTIVE'
    ACCOUNT_SUSPENDED = 'SUSPENDED'
    ACCOUNT_BANNED = 'BANNED'

    ACCOUNT_STATUS_ACTIVE = ACCOUNT_ACTIVE
    ACCOUNT_STATUS_SUSPENDED = ACCOUNT_SUSPENDED
    ACCOUNT_STATUS_BANNED = ACCOUNT_BANNED

    ACCOUNT_STATUS_CHOICES = [
        (ACCOUNT_ACTIVE, 'Active'),
        (ACCOUNT_SUSPENDED, 'Suspended'),
        (ACCOUNT_BANNED, 'Banned'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CITIZEN)
    full_name = models.CharField(max_length=150, blank=True, null=True,
                                 help_text="Full name as per official records")
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

    # --- Account Administrative Status & Ban/Suspension Controls ---
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default=ACCOUNT_ACTIVE)
    suspension_reason = models.TextField(blank=True, null=True, help_text="Reason for suspension or ban")
    suspended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='suspended_users')
    suspended_at = models.DateTimeField(null=True, blank=True)

    @property
    def display_name(self):
        full = self.user.get_full_name().strip() or (self.full_name or '').strip()
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
        """Platform Administrator (superuser or explicit admin role)."""
        return self.effective_role == self.ROLE_ADMIN

    @property
    def is_authority_officer(self):
        """Authority officer role — dispatch & verification console."""
        return self.effective_role == self.ROLE_AUTHORITY

    # --- Backwards-compatible aliases used across reports/hotspots/dashboard ---
    @property
    def is_authority(self):
        """Anyone allowed on the Authority console: admins + authority officers.
        Rangers are NOT authority — they have their own isolated console."""
        return self.is_admin or self.is_authority_officer

    @property
    def is_responder(self):
        return self.is_ranger or self.is_admin

    @property
    def phone(self):
        return self.phone_number or ''

    @property
    def is_operational(self):
        """Checks if account is approved, active, and not suspended or banned."""
        if not self.user.is_active:
            return False
        if self.account_status != self.ACCOUNT_ACTIVE:
            return False
        if self.is_citizen or self.is_admin:
            return True
        if hasattr(self.user, 'application'):
            return self.user.application.status == AccountApplication.STATUS_APPROVED
        return True

    @property
    def is_approved(self):
        return self.is_operational


class AccountApplication(models.Model):
    """
    Registration application for official Authority and Ranger roles.
    Requires administrative verification of supporting documents before account activation.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_NEEDS_INFO = 'NEEDS_INFO'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved & Activated'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_NEEDS_INFO, 'Additional Information Requested'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='application')
    requested_role = models.CharField(max_length=20, choices=[
        (UserProfile.ROLE_AUTHORITY, 'Authority Officer (Dispatch & Verification)'),
        (UserProfile.ROLE_RANGER, 'Forest Ranger (Field Responder)'),
    ])
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    organization = models.CharField(max_length=150, blank=True, null=True,
                                   help_text="Department, Division, Wildlife Sanctuary, or Agency")
    assigned_region = models.CharField(max_length=150, blank=True, null=True,
                                       help_text="Operational District / Division")
    registered_location = models.CharField(max_length=150, blank=True, null=True,
                                           help_text="Operational Base Location (e.g. Kollam)")
    latitude = models.FloatField(null=True, blank=True, help_text="Operational base latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="Operational base longitude")
    supporting_document = models.FileField(upload_to='verification_docs/',
                                           help_text="Official Department ID or Authorization Letter (PDF/JPG/PNG)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reviewed_applications')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True,
                                        help_text="Explanation provided to applicant if rejected or needs more info")

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Application #{self.pk} - {self.user.username} ({self.get_requested_role_display()}) [{self.status}]"


class Notification(models.Model):
    """
    In-app persistent notification for key workflow events across all user roles.
    """
    TYPE_INFO = 'INFO'
    TYPE_SUCCESS = 'SUCCESS'
    TYPE_WARNING = 'WARNING'
    TYPE_DANGER = 'DANGER'

    TYPE_OUTCOME_VERIFIED = TYPE_SUCCESS
    TYPE_ASSIGNMENT_CREATED = TYPE_INFO
    TYPE_ASSIGNMENT_ACCEPTED = TYPE_SUCCESS
    TYPE_ACCOUNT_SUSPENDED = TYPE_DANGER
    TYPE_ACCOUNT_BANNED = TYPE_DANGER
    TYPE_APPLICATION_REJECTED = TYPE_DANGER

    TYPE_CHOICES = [
        (TYPE_INFO, 'Information'),
        (TYPE_SUCCESS, 'Success / Resolved'),
        (TYPE_WARNING, 'Warning / Attention Needed'),
        (TYPE_DANGER, 'Alert / Urgent'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='triggered_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_INFO)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"

    @classmethod
    def send(cls, recipient, title, message, notification_type=TYPE_INFO, link=None, actor=None):
        """Send notification with 2-minute deduplication window to avoid duplicate entries."""
        if not recipient:
            return None
        recent_cutoff = timezone.now() - timedelta(minutes=2)
        duplicate_exists = cls.objects.filter(
            recipient=recipient,
            title=title,
            message=message,
            created_at__gte=recent_cutoff
        ).exists()
        if duplicate_exists:
            return None
        return cls.objects.create(
            recipient=recipient,
            actor=actor,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )


class AuditLog(models.Model):
    """
    Immutable audit trail for sensitive administrative and operational actions:
    - Application review (approve / reject)
    - Account ban / suspension / reinstatement
    - Ranger assignment / reassignment / decline
    - Ranger outcome submission
    - Authority outcome verification / rejection / clarification
    """
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='audit_entries')
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100, blank=True, null=True)
    target_repr = models.CharField(max_length=255, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {actor_name} -> {self.action} on {self.target_type} #{self.target_id}"

    @classmethod
    def record(cls, actor, action, target_type, target_id=None, target_repr=None, details=None, ip_address=None):
        return cls.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            target_repr=str(target_repr)[:255] if target_repr else None,
            details=details,
            ip_address=ip_address
        )


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
