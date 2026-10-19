from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    path('', views.assistance_view, name='assistance'),
    path('manage/', views.admin_hospital_manage_view, name='hospital_manage'),
    path('manage/<int:pk>/edit/', views.admin_hospital_edit_view, name='hospital_edit'),
    path('manage/<int:pk>/delete/', views.admin_hospital_delete_view, name='hospital_delete'),
    path('api/sos/', views.sos_trigger_api, name='api_sos'),
    path('api/sos/feed/', views.sos_feed_api, name='api_sos_feed'),
    path('api/sos/<int:pk>/ack/', views.sos_acknowledge_api, name='api_sos_ack'),
]
