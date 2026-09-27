from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.list_reports_view, name='list'),
    path('create/', views.create_report_view, name='create'),
    path('risk-zones/', views.risk_zones_public_view, name='risk_zones'),
    path('api/map-reports/', views.authority_map_reports_api, name='map_reports_api'),
    path('api/report-panel/<int:pk>/', views.authority_report_panel_api, name='report_panel_api'),
    path('<int:pk>/', views.report_detail_view, name='detail'),
    path('<int:pk>/verify/', views.verify_report_view, name='verify'),
    path('<int:pk>/assign/', views.assign_responder_view, name='assign_responder'),
    path('<int:pk>/response-status/', views.update_response_status_view, name='update_response_status'),
    path('assignments/<int:pk>/cancel/', views.cancel_assignment_view, name='cancel_assignment'),
]
