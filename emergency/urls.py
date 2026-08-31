from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    path('', views.assistance_view, name='assistance'),
    path('api/sos/', views.sos_trigger_api, name='api_sos'),
]
