from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import render
from django.contrib import messages
import uuid
import os
from .services import SnakeAIDetectionService, WoundScreeningService

class SnakeAIAnalysisAPIView(APIView):
    """
    REST API endpoint for real-time AI snake image analysis.
    Accepts POST with 'image' file.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        if 'image' not in request.FILES:
            return Response({'error': 'No image file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        image_file = request.FILES['image']
        ext = os.path.splitext(image_file.name)[1]
        unique_name = f"temp_ai_{uuid.uuid4().hex}{ext}"
        
        saved_path = default_storage.save(f"temp_uploads/{unique_name}", ContentFile(image_file.read()))
        full_path = default_storage.path(saved_path)

        try:
            analysis_result = SnakeAIDetectionService.analyze_image(full_path)
            if default_storage.exists(saved_path):
                default_storage.delete(saved_path)
                
            return Response(analysis_result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f"AI Analysis failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache

@login_required
@never_cache
def wound_checker_view(request):
    """
    Snakebite Wound Image Checker view for citizens.
    Accepts wound photo upload, runs WoundScreeningService binary screening,
    displays results with mandatory medical disclaimer.
    """
    result = None
    if request.method == 'POST' and request.FILES.get('wound_image'):
        image_file = request.FILES['wound_image']
        ext = os.path.splitext(image_file.name)[1]
        unique_name = f"wound_{uuid.uuid4().hex}{ext}"
        
        saved_path = default_storage.save(f"wounds/{unique_name}", ContentFile(image_file.read()))
        full_path = default_storage.path(saved_path)

        try:
            result = WoundScreeningService.analyze_wound_image(full_path)
        except Exception as e:
            messages.error(request, f"Error processing wound image: {str(e)}")

    return render(request, 'ai/wound_check.html', {'result': result})
