from django.contrib import admin
from .models import Hospital, EmergencySOSEvent

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'anti_venom_available', 'anti_venom_stock_vials', 'has_icu', 'operating_hours')
    list_filter = ('anti_venom_available', 'has_icu')
    search_fields = ('name', 'address', 'phone_number')

@admin.register(EmergencySOSEvent)
class EmergencySOSEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone_number', 'location_name', 'status', 'created_at', 'acknowledged_by')
    list_filter = ('status', 'emergency_type', 'created_at')
    search_fields = ('phone_number', 'location_name', 'description', 'user__username')
    readonly_fields = ('created_at', 'acknowledged_at', 'resolved_at')
