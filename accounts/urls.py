from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('provision/', views.admin_provision_account_view, name='admin_provision'),
    path('manage/<int:user_id>/detail/', views.admin_account_detail_view, name='admin_account_detail'),
    path('manage/<int:user_id>/edit/', views.admin_account_edit_view, name='admin_account_edit'),
    path('applications/<int:app_id>/', views.admin_application_detail_view, name='admin_application_detail'),
    path('applications/<int:app_id>/document/', views.admin_application_document_view, name='admin_application_document'),
    path('applications/<int:app_id>/approve/', views.admin_application_approve_view, name='admin_application_approve'),
    path('applications/<int:app_id>/reject/', views.admin_application_reject_view, name='admin_application_reject'),
    path('notifications/', views.notifications_list_view, name='notifications_list'),
    path('notifications/<int:pk>/read/', views.mark_notification_read_view, name='notification_read'),
]
