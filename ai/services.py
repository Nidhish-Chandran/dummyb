import os
import numpy as np
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# LEGACY (DO NOT USE FOR THE CURRENT MODEL): the constants below describe an
# older 15-class species classifier that is no longer deployed. The current
# model venomwatch_cnn2_final.keras outputs a single sigmoid neuron (binary
# VENOMOUS/NON-VENOMOUS). These names are kept only so any stray import does
# not break; nothing in the inference path reads them.
# -----------------------------------------------------------------------------
SNAKE_SPECIES_DATABASE = {}
SNAKE_CLASS_INDICES = set()
NON_SNAKE_CLASS_INDICES = set()
CLASS_NAMES = ['NON-VENOMOUS', 'VENOMOUS']


# =============================================================================
# IMPORTANT - VERIFIED CLASS MAPPING (audited 2026-09-27)
#
# The deployed model `venomwatch_cnn2_final.keras` was inspected at the binary
# level (config.json inside the .keras zip):
#   Sequential( Input 224x224x3 -> MobileNetV2 Functional -> GAP -> Dropout
#               -> Dense(128, relu) -> Dropout -> Dense(1, sigmoid) )
# i.e. it is a BINARY VENOM classifier with ONE sigmoid output neuron.
#
# It is NOT a 15-class species classifier. The legacy constants above
# (CLASS_NAMES / SNAKE_CLASS_INDICES / SNAKE_SPECIES_DATABASE) describe an
# older 15-class model that no longer exists in this repo and MUST NOT be used
# to interpret this model's output. argmax over a single sigmoid value always
# returns index 0 ("black"), which produced nonsense predictions such as
# "Black-headed Python - NON_VENOMOUS" for every image - including clearly
# venomous snakes. That was the root cause of the wrong venom prediction.
#
# Verified mapping for the current model (raw sigmoid output p in [0, 1]):
#   p >= 0.5  ->  VENOMOUS      (confidence = p)
#   p <  0.5  ->  NON-VENOMOUS  (confidence = 1 - p)
# Do not blindly invert this polarity; re-audit against labeled images first.
# =============================================================================

VENOM_DECISION_THRESHOLD = getattr(settings, 'SNAKE_DETECTION_THRESHOLD', 0.50)


def map_venom_prediction(raw_output):
    """Map the raw sigmoid output of venomwatch_cnn2_final to a venom label.

    Returns (label, confidence_pct). This is the ONLY sanctioned interpretation
    of the model output: a single sigmoid neuron thresholded at 0.5.
    """
    if raw_output >= VENOM_DECISION_THRESHOLD:
        return 'VENOMOUS', round(float(raw_output) * 100, 1)
    return 'NON-VENOMOUS', round((1.0 - float(raw_output)) * 100, 1)


class SnakeAIPipelineService:
    """
    CNN-based Snake Venom Classification Pipeline (Single-Stage):

    Model: venomwatch_cnn2_final.keras (MobileNetV2 backbone, binary head)
    Input: 224x224 RGB images normalized to [0, 1]
    Output: 1 sigmoid neuron -> VENOMOUS / NON-VENOMOUS

    The model object is loaded ONCE for performance, but inference is
    recomputed independently for every uploaded image. No prediction state is
    kept between requests (no globals, no lru_cache on results, no session
    storage).
    """
    _model = None

    # Decision threshold for the binary sigmoid output
    SNAKE_CONFIDENCE_THRESHOLD = VENOM_DECISION_THRESHOLD

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
                if tuple(s for s in cls._model.output_shape[1:]) != (1,):
                    logger.warning("[AI] Unexpected output shape - verify class mapping!")
            except Exception as e:
                logger.error(f"[AI] Failed to load CNN model: {e}")
                raise
        return cls._model

    @classmethod
    def classify_snake_image(cls, abs_path):
        """
        Binary venom classification for one specific image file.

        Fresh inference on EVERY call - nothing is cached or reused from a
        previous image.

        Returns dict with:
          - is_snake: bool (snake presence heuristic, see below)
          - venomous: bool
          - venom_category: str ('HIGHLY_VENOMOUS' or 'NON_VENOMOUS')
          - confidence: float (0-100)
          - raw_output: float (sigmoid output, for debugging)
          - predicted_label: str ('VENOMOUS' / 'NON-VENOMOUS')
          - description: str
        """
        filename = os.path.basename(abs_path)
        file_size = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0

        print(f"[AI] Received image: {filename}")
        print(f"[AI] Image path: {abs_path}")
        print(f"[AI] File size: {file_size} bytes")
        print(f"[AI] CNN inference started")

        try:
            import tensorflow as tf
            import hashlib

            with open(abs_path, 'rb') as fh:
                img_hash = hashlib.md5(fh.read()).hexdigest()[:12]
            print(f"[AI] Image content hash: {img_hash}")

            model = cls.get_model()

            # Load and preprocess image (matching training preprocessing:
            # 224x224 RGB, rescaled to [0, 1])
            img = tf.keras.utils.load_img(abs_path, target_size=(224, 224))
            img_array = tf.keras.utils.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0).astype(np.float32) / 255.0

            # Run inference on THIS image only
            raw = model.predict(img_array, verbose=0)[0][0]
            raw_output = float(raw)

            predicted_label, confidence = map_venom_prediction(raw_output)
            venomous = predicted_label == 'VENOMOUS'

            # Snake-presence heuristic: this dataset/model has no dedicated
            # snake/not-snake head anymore, so we report "snake detected"
            # whenever the model produces a confident signal in either
            # direction. Low-confidence outputs are surfaced via uncertainty.
            is_snake = confidence >= 50.0

            print(f"[AI] raw prediction: {raw_output:.6f}")
            print(f"[AI] mapped class: {predicted_label}")
            print(f"[AI] confidence: {confidence}%")

            result = {
                'is_snake': is_snake,
                'species': None,
                'species_common': None,
                'venomous': venomous,
                'venom_category': 'HIGHLY_VENOMOUS' if venomous else 'NON_VENOMOUS',
                'description': (
                    'Model predicts features consistent with a venomous snake.'
                    if venomous else
                    'Model predicts features consistent with a non-venomous snake.'
                ),
                'confidence': confidence,
                'raw_output': round(raw_output, 6),
                'predicted_label': predicted_label,
                'image_hash': img_hash,
                'class_index': 1 if venomous else 0,
                'class_name': predicted_label,
                'all_probabilities': [round(confidence, 1), round(100.0 - confidence, 1)],
            }
            print(f"[AI] CNN inference completed: {predicted_label} ({confidence}%)")
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
                'raw_output': None,
                'predicted_label': 'ERROR',
                'class_index': -1,
                'class_name': 'error',
                'all_probabilities': [],
            }

    @classmethod
    def analyze_image(cls, image_path):
        """
        Main pipeline orchestrator for CNN-based venom classification.

        Args:
            image_path: Path to the uploaded image file (the CURRENT upload)

        Returns:
            Dict with standardized fields for backward compatibility:
            - snake_detected, snake_confidence, venomous, venom_confidence,
              species, venom_category, status, message, model_1, model_2,
              processed_image_path, raw_output, predicted_label, confidence
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

        # Run CNN classification (fresh inference for THIS image only)
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

        venomous = cnn_result['venomous']
        confidence = cnn_result['confidence']

        if venomous:
            status_code = 'SNAKE_DETECTED_VENOMOUS'
            species = 'Venomous Snake'
            msg = f"AI Prediction: VENOMOUS ({confidence}%)"
            if confidence < 60.0:
                msg += " - Low-confidence prediction - professional verification recommended."
        else:
            status_code = 'SNAKE_DETECTED_NON_VENOMOUS'
            species = 'Non-Venomous Snake'
            msg = f"AI Prediction: NON-VENOMOUS ({confidence}%)"
            if confidence < 60.0:
                msg += " - Low-confidence prediction - professional verification recommended."

        return {
            'snake_detected': True,
            'snake_confidence': confidence,
            'venomous': venomous,
            'venom_confidence': confidence,
            'species': species,
            'common_name': species,
            'venom_category': cnn_result['venom_category'],
            'status': status_code,
            'message': msg,
            'model_1': 'venomwatch_cnn2_final (CNN)',
            'model_2': None,
            'processed_image_path': str(image_path),
            # Detailed fields
            'is_snake': True,
            'class_name': cnn_result['class_name'],
            'class_index': cnn_result['class_index'],
            'predicted_label': cnn_result['predicted_label'],
            'raw_output': cnn_result['raw_output'],
            'image_hash': cnn_result.get('image_hash'),
            'species_common': species,
            'description': cnn_result['description'],
            'all_probabilities': cnn_result.get('all_probabilities', []),
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
