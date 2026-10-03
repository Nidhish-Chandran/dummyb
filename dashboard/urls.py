from django.urls import path
from . import views

app_name = 'dashboard'

from reports import views as reports_views

urlpatterns = [
    path('authority/', views.dashboard_home_view, name='surveillance'),
    path('authority/map/', reports_views.authority_map_view, name='authority_map_alias'),
    path('', views.landing_page_view, name='home'),
]
