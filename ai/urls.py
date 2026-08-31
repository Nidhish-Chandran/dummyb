from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('api/analyze/', views.SnakeAIAnalysisAPIView.as_view(), name='api_analyze'),
    path('wound-check/', views.wound_checker_view, name='wound_check'),
]
