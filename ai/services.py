import os
import numpy as np
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Snake Species Database with Venom Status Mapping
# Based on actual CNN training classes (15 classes total)
# Class index mapping is alphabetical: black, boa, cat, cobra, common, keelback, krait, kukri, pit, python, racer, rat, russell, saw, wolf
SNAKE_SPECIES_DATABASE = {
    'black': {
        'species_name': 'Black-headed Royal Snake',
        'common_name': 'Black-headed Python',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Non-venomous python species found in India.'
    },
    'boa': {
        'species_name': 'Indian Boa',
        'common_name': 'Common Indian Boa',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Large non-venomous constrictor snake.'
    },
    'cobra': {
        'species_name': 'Indian Cobra (Naja naja)',
        'common_name': 'Spectacled Cobra',
        'venomous': True,
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Highly venomous elapid snake. One of the Big Four snakes of India.'
    },
    'common': {
        'species_name': 'Common Trinket Snake',
        'common_name': 'Trinket Snake',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Harmless non-venomous colubrid snake.'
    },
    'keelback': {
        'species_name': 'Keelback Water Snake',
        'common_name': 'Asiatic Water Snake',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Mildly venomous but generally harmless to humans.'
    },
    'krait': {
        'species_name': 'Common Krait (Bungarus caeruleus)',
        'common_name': 'Indian Krait',
        'venomous': True,
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Highly venomous elapid. One of the Big Four snakes of India. Nocturnal.'
    },
    'kukri': {
        'species_name': 'Kukri Snake',
        'common_name': 'Common Kukri Snake',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Small non-venomous colubrid snake.'
    },
    'pit': {
        'species_name': 'Pit Viper',
        'common_name': 'Himalayan Pit Viper',
        'venomous': True,
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Venomous pit viper species.'
    },
    'python': {
        'species_name': 'Indian Python',
        'common_name': 'Rock Python',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Large non-venomous constrictor. Protected species.'
    },
    'racer': {
        'species_name': 'Racer Snake',
        'common_name': 'Yellow-throated Racer',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Fast-moving non-venomous colubrid snake.'
    },
    'rat': {
        'species_name': 'Indian Rat Snake (Ptyas mucosa)',
        'common_name': 'Dhaman',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Large non-venomous snake commonly found near human settlements.'
    },
    'russell': {
        'species_name': "Russell's Viper (Daboia russelii)",
        'common_name': "Russell's Viper",
        'venomous': True,
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Highly venomous viper. One of the Big Four snakes of India.'
    },
    'saw': {
        'species_name': 'Saw-scaled Viper (Echis carinatus)',
        'common_name': 'Saw-scaled Viper',
        'venomous': True,
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Highly venomous small viper. One of the Big Four snakes of India.'
    },
    'wolf': {
        'species_name': 'Wolf Snake',
        'common_name': 'Common Wolf Snake',
        'venomous': False,
        'venom_category': 'NON_VENOMOUS',
        'description': 'Small non-venomous colubrid snake, often mistaken for kraits.'
    }
}

# Class indices that represent SNAKES (not 'cat')
# Alphabetical order: black=0, boa=1, cat=2, cobra=3, common=4, keelback=5, krait=6, kukri=7, pit=8, python=9, racer=10, rat=11, russell=12, saw=13, wolf=14
SNAKE_CLASS_INDICES = {0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}
NON_SNAKE_CLASS_INDICES = {2}  # Class index 2 is 'cat' - used as proxy for non-snake

CLASS_NAMES = ['black', 'boa', 'cat', 'cobra', 'common', 'keelback', 'krait', 'kukri', 'pit', 'python', 'racer', 'rat', 'russell', 'saw', 'wolf']


class SnakeAIPipelineService:
    """
    CNN-based Snake Identification Pipeline (Single-Stage):
    
    Model: venomwatch_cnn2_final.keras (MobileNetV2-based CNN)
    Input: 224x224 RGB images
    Classes: 15 (14 snake species + 1 non-snake proxy 'cat')
    
    Pipeline:
    USER UPLOADS IMAGE
            ↓
        CNN MODEL
            ↓
    ┌───────┴────────┐
    ↓                ↓
NOT SNAKE          SNAKE
    ↓                ↓
  STOP           SPECIES
                     ↓
             VENOMOUS STATUS
                     ↓
               CONFIDENCE
                     ↓
         OPTIONAL USER REPORT
    
    This service does NOT use YOLO or any object detection.
    It performs direct image classification using a trained CNN.
    """
    _model = None
    
    # Confidence threshold for reliable snake detection
    SNAKE_CONFIDENCE_THRESHOLD = getattr(settings, 'SNAKE_DETECTION_THRESHOLD', 0.50)
    
    @classmethod
    def get_model(cls):
        """Load the CNN model once (lazy loading)."""
        if cls._model is None:
            try:
                import tensorflow as tf
                paths_to_try = [
                    os.path.join(settings.BASE_DIR, 'venomwatch_cnn2_final.keras'),
                    os.path.join(settings.BASE_DIR, 'ai', 'models', 'venomwatch_cnn2_final.keras'),
                ]
                model_path = None
                for p in paths_to_try:
                    if os.path.exists(p):
                        model_path = p
                        break
                if model_path is None:
                    raise FileNotFoundError("CNN model file (venomwatch_cnn2_final.keras) not found.")
                
                print(f"[AI] Loading CNN model from: {model_path}")
                cls._model = tf.keras.models.load_model(model_path)
                print(f"[AI] CNN model loaded successfully")
                print(f"[AI] Model input shape: {cls._model.input_shape}")
                print(f"[AI] Model output shape: {cls._model.output_shape}")
            except Exception as e:
                logger.error(f"[AI] Failed to load CNN model: {e}")
                raise
        return cls._model
    
    @classmethod
    def classify_snake_image(cls, abs_path):
        """
        Single-stage CNN classification for snake identification.
        
        Returns dict with:
          - is_snake: bool
          - species: str or None
          - species_common: str or None
          - venomous: bool or None
          - venom_category: str or None ('HIGHLY_VENOMOUS' or 'NON_VENOMOUS')
          - description: str or None
          - confidence: float (0-100)
          - class_index: int
          - class_name: str (raw class name from model)
          - all_probabilities: list (for debugging)
        """
        filename = os.path.basename(abs_path)
        file_size = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0
        
        print(f"[AI] Received image: {filename}")
        print(f"[AI] Image path: {abs_path}")
        print(f"[AI] File size: {file_size} bytes")
        print(f"[AI] CNN inference started")
        
        try:
            import tensorflow as tf
            
            model = cls.get_model()
            
            # Load and preprocess image (matching training preprocessing)
            img = tf.keras.utils.load_img(abs_path, target_size=(224, 224))
            img_array = tf.keras.utils.img_to_array(img)
            
            # Expand dimensions for batch (1, 224, 224, 3)
            img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
            
            # Normalize to [0, 1] range (MobileNetV2 preprocessing)
            img_array = img_array / 255.0
            
            # Run inference
            predictions = model.predict(img_array, verbose=0)[0]
            
            # Get top prediction
            class_index = int(np.argmax(predictions))
            confidence = float(np.max(predictions))
            class_name = CLASS_NAMES[class_index]
            
            print(f"[AI] CNN raw output: class_index={class_index}, class_name='{class_name}', confidence={confidence*100:.1f}%")
            print(f"[AI] All probabilities: {[f'{p*100:.1f}%' for p in predictions]}")
            
            # Check if predicted class is a snake or non-snake (cat)
            is_snake = class_index in SNAKE_CLASS_INDICES
            
            if is_snake:
                species_info = SNAKE_SPECIES_DATABASE.get(class_name, {})
                result = {
                    'is_snake': True,
                    'species': species_info.get('species_name', f'{class_name.capitalize()} Snake'),
                    'species_common': species_info.get('common_name', class_name.capitalize()),
                    'venomous': species_info.get('venomous', False),
                    'venom_category': species_info.get('venom_category', 'NON_VENOMOUS'),
                    'description': species_info.get('description', ''),
                    'confidence': round(confidence * 100, 1),
                    'class_index': class_index,
                    'class_name': class_name,
                    'all_probabilities': [round(p * 100, 1) for p in predictions]
                }
                print(f"[AI] SNAKE DETECTED: {result['species']} ({result['venom_category']}) - Confidence: {result['confidence']}%")
            else:
                # Non-snake detected (class 'cat' or other non-snake proxy)
                result = {
                    'is_snake': False,
                    'species': None,
                    'species_common': None,
                    'venomous': None,
                    'venom_category': None,
                    'description': 'No snake detected in the image.',
                    'confidence': round(confidence * 100, 1),
                    'class_index': class_index,
                    'class_name': class_name,
                    'all_probabilities': [round(p * 100, 1) for p in predictions]
                }
                print(f"[AI] NOT A SNAKE: {class_name} - Confidence: {result['confidence']}%")
            
            print(f"[AI] CNN inference completed")
            return result
            
        except Exception as e:
            logger.error(f"[AI] CNN classification error: {e}")
            print(f"[AI] CNN classification exception: {e}")
            return {
                'is_snake': False,
                'species': None,
                'species_common': None,
                'venomous': None,
                'venom_category': None,
                'description': f'Error processing image: {str(e)}',
                'confidence': 0.0,
                'class_index': -1,
                'class_name': 'error',
                'all_probabilities': []
            }
    
    @classmethod
    def analyze_image(cls, image_path):
        """
        Main pipeline orchestrator for CNN-based snake identification.
        
        This method replaces the old two-stage YOLO+CNN pipeline.
        Now uses single-stage CNN classification only.
        
        Args:
            image_path: Path to the uploaded image file
            
        Returns:
            Dict with standardized fields for backward compatibility:
            - snake_detected: bool (same as is_snake)
            - snake_confidence: float (0-100)
            - venomous: bool or None
            - venom_confidence: float or None (same as snake_confidence for now)
            - species: str or None
            - venom_category: str or None
            - status: str
            - message: str
            - model_1: str (now CNN model name)
            - model_2: None (removed)
            - processed_image_path: str
        """
        # Resolve absolute path
        path_str = str(image_path)
        if os.path.isabs(path_str):
            abs_path = path_str
        elif os.path.exists(os.path.abspath(path_str)):
            abs_path = os.path.abspath(path_str)
        else:
            abs_path = os.path.join(settings.MEDIA_ROOT, path_str)
        
        if not os.path.exists(abs_path):
            return {
                'snake_detected': False,
                'snake_confidence': 0.0,
                'venomous': None,
                'venom_confidence': None,
                'species': None,
                'venom_category': None,
                'status': 'IMAGE_NOT_FOUND',
                'message': 'Image file not found on disk.',
                'model_1': 'venomwatch_cnn2_final (CNN)',
                'model_2': None,
                'processed_image_path': None,
                'is_snake': False,
                'class_name': None,
                'class_index': -1,
                'description': 'Image file not found.'
            }
        
        # Run CNN classification
        try:
            cnn_result = cls.classify_snake_image(abs_path)
        except Exception as e:
            logger.error(f"[AI] Pipeline error: {e}")
            return {
                'snake_detected': False,
                'snake_confidence': 0.0,
                'venomous': None,
                'venom_confidence': None,
                'species': None,
                'venom_category': None,
                'status': 'CNN_ERROR',
                'message': f'CNN classification error: {str(e)}',
                'model_1': 'venomwatch_cnn2_final (CNN)',
                'model_2': None,
                'processed_image_path': str(image_path),
                'is_snake': False,
                'class_name': None,
                'class_index': -1,
                'description': f'Error: {str(e)}'
            }
        
        # Map CNN result to legacy format for backward compatibility
        is_snake = cnn_result['is_snake']
        
        if is_snake:
            if cnn_result['venomous']:
                status_code = 'SNAKE_DETECTED_VENOMOUS'
                msg = f"AI Prediction: {cnn_result['species']} - VENOMOUS ({cnn_result['confidence']}%)"
                if cnn_result['confidence'] < 60.0:
                    msg += " — Low-confidence prediction — professional verification recommended."
            else:
                status_code = 'SNAKE_DETECTED_NON_VENOMOUS'
                msg = f"AI Prediction: {cnn_result['species']} - NON-VENOMOUS ({cnn_result['confidence']}%)"
                if cnn_result['confidence'] < 60.0:
                    msg += " — Low-confidence prediction — professional verification recommended."
        else:
            status_code = 'NO_SNAKE_DETECTED'
            msg = f"No snake detected in the image (CNN classified as '{cnn_result['class_name']}' with {cnn_result['confidence']}% confidence)."
        
        return {
            'snake_detected': is_snake,
            'snake_confidence': cnn_result['confidence'] if is_snake else 0.0,
            'venomous': cnn_result['venomous'],
            'venom_confidence': cnn_result['confidence'] if is_snake and cnn_result['venomous'] is not None else None,
            'species': cnn_result['species'],
            'venom_category': cnn_result['venom_category'],
            'status': status_code,
            'message': msg,
            'model_1': 'venomwatch_cnn2_final (CNN)',
            'model_2': None,
            'processed_image_path': str(image_path),
            # Additional detailed fields
            'is_snake': is_snake,
            'class_name': cnn_result['class_name'],
            'class_index': cnn_result['class_index'],
            'species_common': cnn_result['species_common'],
            'description': cnn_result['description'],
            'all_probabilities': cnn_result.get('all_probabilities', [])
        }


# Backward compatibility alias
SnakeAIDetectionService = SnakeAIPipelineService


class SnakebiteScreeningService:
    """
    AI-assisted Snakebite Wound Image Screening using EfficientNetB0.
    
    Model: venom_watch_snakebite_efficientnetb0.keras
    Input: 224x224 RGB images
    Output: Binary classification (sigmoid activation)
      - Output < 0.5: No Snakebite Pattern Detected
      - Output >= 0.5: Possible Snakebite Pattern Detected
    
    This is an AI-assisted screening tool, NOT a medical diagnostic system.
    Always seek professional medical evaluation for suspected snakebites.
    """
    
    _model = None
    
    MODEL_PATH = os.path.join(settings.BASE_DIR, 'venom_watch_snakebite_efficientnetb0.keras')
    DECISION_THRESHOLD = 0.5
    UNCERTAINTY_RANGE = (0.4, 0.6)  # Predictions in this range are considered uncertain
    
    MANDATORY_DISCLAIMER = (
        "This is an AI-assisted screening tool and is NOT a medical diagnosis. "
        "If a snakebite is suspected, seek emergency medical care immediately."
    )
    
    @classmethod
    def get_model(cls):
        """Load the EfficientNetB0 snakebite screening model once (lazy loading)."""
        if cls._model is None:
            try:
                import tensorflow as tf
                if not os.path.exists(cls.MODEL_PATH):
                    raise FileNotFoundError(f"Snakebite model not found at: {cls.MODEL_PATH}")
                print(f"[Snakebite] Loading EfficientNetB0 model from: {cls.MODEL_PATH}")
                cls._model = tf.keras.models.load_model(cls.MODEL_PATH)
                print(f"[Snakebite] Model loaded successfully")
            except Exception as e:
                logger.error(f"[Snakebite] Failed to load model: {e}")
                raise
        return cls._model
    
    @classmethod
    def analyze_wound_image(cls, image_path):
        """
        Analyze a wound image using the trained EfficientNetB0 model.
        
        Returns dict with:
          - is_snake_bite: bool
          - result_label: str ('Snake Bite' or 'Not Snake Bite')
          - status_title: str
          - confidence: float (0-100)
          - recommendation: str
          - disclaimer: str
          - method_label: str
          - raw_output: float (raw sigmoid output for debugging)
          - uncertain: bool
        """
        abs_path = os.path.join(settings.MEDIA_ROOT, str(image_path)) if not os.path.isabs(str(image_path)) else str(image_path)
        
        # Check file exists
        if not os.path.exists(abs_path):
            return {
                'is_snake_bite': False,
                'result_label': 'Not Snake Bite',
                'status_title': 'Image Not Found',
                'confidence': None,
                'recommendation': 'Image file not found on disk. Please upload a valid photo of the affected area.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'AI-Assisted Screening (EfficientNetB0)',
                'raw_output': None,
                'uncertain': False,
                'processed_image_path': None
            }
        
        # Try to load and analyze with EfficientNetB0
        try:
            import tensorflow as tf
            
            model = cls.get_model()
            
            # Load image with TensorFlow to ensure proper preprocessing
            img = tf.keras.utils.load_img(abs_path, target_size=(224, 224))
            img_array = tf.keras.utils.img_to_array(img)
            
            # Expand dimensions for batch (1, 224, 224, 3)
            img_array = np.expand_dims(img_array, axis=0).astype(np.float32)
            
            # Run inference
            raw_output = float(model.predict(img_array, verbose=0)[0][0])
            
            # Log raw output for debugging
            print(f"[Snakebite] Raw model output: {raw_output:.6f}")
            print(f"[Snakebite] Threshold: {cls.DECISION_THRESHOLD}")
            print(f"[Snakebite] Uncertainty range: {cls.UNCERTAINTY_RANGE}")
            
            # Determine if prediction is uncertain
            uncertain = cls.UNCERTAINTY_RANGE[0] <= raw_output <= cls.UNCERTAINTY_RANGE[1]
            
            # Classify based on threshold
            if raw_output >= cls.DECISION_THRESHOLD:
                is_snake_bite = True
                confidence = round(raw_output * 100, 1)
                result_label = 'Snake Bite'
                status_title = 'Possible Snakebite Pattern Detected'
                recommendation = (
                    'AI screening detected patterns consistent with a snakebite. '
                    'Immobilize the limb, keep the patient calm, and seek emergency medical care immediately.'
                )
            else:
                is_snake_bite = False
                confidence = round((1.0 - raw_output) * 100, 1)
                result_label = 'Not Snake Bite'
                status_title = 'No Snakebite Pattern Detected'
                recommendation = (
                    'AI screening did not detect characteristic snakebite patterns. '
                    'However, a negative result does not rule out a snakebite. '
                    'If symptoms persist or a bite is suspected, seek medical attention immediately.'
                )
            
            # Override for uncertain predictions
            if uncertain:
                status_title = 'Unable to Confidently Classify'
                recommendation = (
                    'The AI model could not confidently classify this image. '
                    'Professional medical evaluation is strongly recommended if a snakebite is suspected.'
                )
            
            print(f"[Snakebite] Result: {status_title}, Confidence: {confidence}%, Uncertain: {uncertain}")
            
            return {
                'is_snake_bite': is_snake_bite,
                'result_label': result_label,
                'status_title': status_title,
                'confidence': confidence,
                'recommendation': recommendation,
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'AI-Assisted Screening (EfficientNetB0)',
                'raw_output': raw_output,
                'uncertain': uncertain,
                'processed_image_path': str(image_path)
            }
            
        except Exception as e:
            logger.error(f"[Snakebite] Inference error: {e}")
            return {
                'is_snake_bite': False,
                'result_label': 'Not Snake Bite',
                'status_title': 'Analysis Error',
                'confidence': None,
                'recommendation': 'Unable to analyze this image. Please upload a valid JPG or PNG image.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'AI-Assisted Screening (EfficientNetB0)',
                'raw_output': None,
                'uncertain': False,
                'processed_image_path': None
            }


# Legacy heuristic-based service (deprecated, kept for backward compatibility)
class WoundScreeningService:
    """
    DEPRECATED: Legacy heuristic-based wound screening.
    Use SnakebiteScreeningService (EfficientNetB0) instead.
    """
    
    MANDATORY_DISCLAIMER = SnakebiteScreeningService.MANDATORY_DISCLAIMER
    
    @classmethod
    def analyze_wound_image(cls, image_path):
        """Legacy heuristic analysis - deprecated."""
        # Delegate to new EfficientNetB0-based service
        return SnakebiteScreeningService.analyze_wound_image(image_path)
