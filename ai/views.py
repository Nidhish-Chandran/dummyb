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
from .services import SnakeAIPipelineService, SnakebiteScreeningService, WoundScreeningService

from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

@method_decorator(never_cache, name='dispatch')
class SnakeAIAnalysisAPIView(APIView):
    """
    REST API endpoint for CNN-based AI snake image analysis.
    Accepts POST with 'image' file.
    Runs single-stage CNN classification (venomwatch_cnn2_final).
    Returns: is_snake, species, venomous status, confidence.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        if 'image' not in request.FILES:
            return Response({'error': 'No image file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        image_file = request.FILES['image']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            return Response({'error': 'Unsupported file format. Please upload JPG, PNG, or WEBP image.'}, status=status.HTTP_400_BAD_REQUEST)

        unique_name = f"temp_ai_{uuid.uuid4().hex}{ext}"
        
        try:
            saved_path = default_storage.save(f"temp_uploads/{unique_name}", ContentFile(image_file.read()))
            full_path = default_storage.path(saved_path)
            
            analysis_result = SnakeAIPipelineService.analyze_image(full_path)
            
            # Clean up temp file
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
    Accepts wound photo upload, runs SnakebiteScreeningService (EfficientNetB0),
    displays results with mandatory medical disclaimer.

    Every analysis is stateless: each uploaded photo is re-run through the model,
    and only the current POST's result is ever rendered (no session caching).
    """
    result = None
    error = None

    if request.method == 'POST' and request.FILES.get('wound_image'):
        image_file = request.FILES['wound_image']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            error = 'Unsupported file format. Please upload a JPG, PNG, or WEBP image.'
        else:
            unique_name = f"wound_{uuid.uuid4().hex}{ext}"
            saved_path = None
            full_path = None

            try:
                saved_path = default_storage.save(f"wounds/{unique_name}", ContentFile(image_file.read()))
                full_path = default_storage.path(saved_path)

                # Fresh inference on THIS image only - never reuse a previous result
                result = SnakebiteScreeningService.analyze_wound_image(full_path)
            except Exception as e:
                error = f"Error processing wound image: {str(e)}"
            finally:
                # Clean up the temp upload so no stale files linger
                try:
                    if saved_path and default_storage.exists(saved_path):
                        default_storage.delete(saved_path)
                except Exception:
                    pass

    response = render(request, 'ai/wound_check.html', {
        'result': result,
        'error': error,
        'analysis_id': uuid.uuid4().hex if result else None,
    })
    # Belt-and-suspenders: forbid any browser/proxy caching of this page so
    # a back-navigation / refresh can never show a previous report.
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
