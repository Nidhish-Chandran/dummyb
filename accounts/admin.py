from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, AccountApplication, Notification, AuditLog

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Profile & Role Management'
    fields = (
        'role', 'phone_number', 'registered_location', 'assigned_region',
        'latitude', 'longitude', 'availability', 'account_status', 'suspension_reason'
    )

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_availability', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'profile__role', 'profile__availability', 'profile__account_status')

    def get_role(self, obj):
        return getattr(obj, 'profile', None).get_role_display() if hasattr(obj, 'profile') else '—'
    get_role.short_description = 'Role'

    def get_availability(self, obj):
        return getattr(obj, 'profile', None).get_availability_display() if hasattr(obj, 'profile') else '—'
    get_availability.short_description = 'Availability'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'account_status', 'phone_number', 'registered_location', 'assigned_region', 'availability')
    list_filter = ('role', 'availability', 'account_status')
    search_fields = ('user__username', 'user__email', 'phone_number', 'registered_location', 'assigned_region')
    fieldsets = (
        ('User Association', {
            'fields': ('user',)
        }),
        ('Role & Account Status', {
            'fields': ('role', 'account_status', 'suspension_reason', 'suspended_by', 'suspended_at')
        }),
        ('Contact & Operational Base', {
            'fields': ('phone_number', 'registered_location', 'assigned_region', 'latitude', 'longitude')
        }),
        ('Status', {
            'fields': ('availability',)
        }),
    )

@admin.register(AccountApplication)
class AccountApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'requested_role', 'organization', 'status', 'submitted_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('requested_role', 'status')
    search_fields = ('user__username', 'user__email', 'organization', 'full_name')

    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            if obj.status == AccountApplication.STATUS_APPROVED:
                obj.user.is_active = True
                obj.user.save(update_fields=['is_active'])
                if hasattr(obj.user, 'profile'):
                    obj.user.profile.role = obj.requested_role
                    obj.user.profile.account_status = UserProfile.ACCOUNT_ACTIVE
                    obj.user.profile.save()
            elif obj.status == AccountApplication.STATUS_REJECTED:
                obj.user.is_active = False
                obj.user.save(update_fields=['is_active'])
        super().save_model(request, obj, form, change)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title', 'message')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'actor', 'action', 'target_type', 'target_id')
    list_filter = ('action', 'target_type')
    search_fields = ('actor__username', 'action', 'target_repr', 'details')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
