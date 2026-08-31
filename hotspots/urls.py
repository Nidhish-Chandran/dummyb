from django.urls import path
from . import views

app_name = 'hotspots'

urlpatterns = [
    path('', views.hotspots_view, name='view'),
    path('api/clusters/', views.hotspots_api_view, name='api_clusters'),
]
