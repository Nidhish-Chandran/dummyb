from django.urls import path
from . import views

app_name = 'ranger'

urlpatterns = [
    path('', views.ranger_dashboard_view, name='dashboard'),
    path('assignments/', views.assignment_list_view, name='assignments'),
    path('assignments/<int:pk>/', views.assignment_detail_view, name='assignment_detail'),
    path('assignments/<int:pk>/update/', views.assignment_update_view, name='assignment_update'),
    path('profile/', views.ranger_profile_view, name='profile'),
]
