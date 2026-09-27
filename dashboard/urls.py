from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.landing_page_view, name='home'),
]

# Named alias for the Authority surveillance dashboard (same view as '')
from django.urls import path as _path
urlpatterns.insert(0, _path('authority/', views.dashboard_home_view, name='surveillance'))
