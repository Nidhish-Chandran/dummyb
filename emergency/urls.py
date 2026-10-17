from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    path('', views.assistance_view, name='assistance'),
    path('api/sos/', views.sos_trigger_api, name='api_sos'),
    path('api/sos/feed/', views.sos_feed_api, name='api_sos_feed'),
    path('api/sos/<int:pk>/ack/', views.sos_acknowledge_api, name='api_sos_ack'),
]
