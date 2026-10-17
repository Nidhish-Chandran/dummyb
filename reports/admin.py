from django.contrib import admin
from .models import SightingReport, RangerAssignment

@admin.register(SightingReport)
class SightingReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'species_predicted', 'venom_category', 'location_name',
        'status', 'response_status', 'duplicate_flag', 'spam_flag', 'created_at'
    )
    list_filter = (
        'status', 'venom_category', 'response_status',
        'duplicate_flag', 'spam_flag', 'ai_detected'
    )
    search_fields = ('species_predicted', 'location_name', 'notes', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'duplicate_score', 'duplicate_reason', 'spam_reason')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'original_image', 'processed_image', 'location_name', 'latitude', 'longitude')
        }),
        ('Status & Verification', {
            'fields': ('status', 'verified_by', 'authority_notes')
        }),
        ('AI Analysis Metadata', {
            'fields': ('species_predicted', 'common_name', 'venom_category', 'venomous', 'venom_confidence', 'ai_confidence', 'model_1_name')
        }),
        ('Duplicate & Spam Analytics', {
            'fields': ('duplicate_flag', 'duplicate_of', 'duplicate_score', 'duplicate_reason', 'spam_flag', 'spam_reason')
        }),
        ('Incident Task Assignment', {
            'fields': ('assigned_responder', 'response_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(RangerAssignment)
class RangerAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'sighting', 'ranger', 'status', 'outcome',
        'review_decision', 'assigned_at', 'completed_at'
    )
    list_filter = ('status', 'outcome', 'review_decision')
    search_fields = ('ranger__username', 'sighting__location_name', 'notes', 'review_notes')
    readonly_fields = ('assigned_at', 'responded_at', 'outcome_submitted_at', 'completed_at', 'reviewed_at')
