from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & Role Management'
    fields = (
        'role', 'phone_number', 'registered_location', 'assigned_region',
        'latitude', 'longitude', 'availability'
    )

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_availability', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'profile__role', 'profile__availability')

    def get_role(self, obj):
        return getattr(obj, 'profile', None).get_role_display() if hasattr(obj, 'profile') else '—'
    get_role.short_description = 'Role'

    def get_availability(self, obj):
        return getattr(obj, 'profile', None).get_availability_display() if hasattr(obj, 'profile') else '—'
    get_availability.short_description = 'Availability'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'registered_location', 'assigned_region', 'availability', 'latitude', 'longitude')
    list_filter = ('role', 'availability')
    search_fields = ('user__username', 'user__email', 'phone_number', 'registered_location', 'assigned_region')
    fieldsets = (
        ('User Association', {
            'fields': ('user',)
        }),
        ('Role Management', {
            'fields': ('role',)
        }),
        ('Contact & Operational Base', {
            'fields': ('phone_number', 'registered_location', 'assigned_region', 'latitude', 'longitude')
        }),
        ('Status', {
            'fields': ('availability',)
        }),
    )

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
