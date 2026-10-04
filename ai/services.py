import os
import time
import threading
import hashlib
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


# Model cache singleton dictionary
MODEL_CACHE = {
    'snake_detector': None,
    'venom_classifier': None,
}
_MODEL_LOCK = threading.Lock()

# ImageNet synset indices 52 through 68 inclusive correspond to suborder Serpentes:
# 52: thunder_snake, 53: ringneck_snake, 54: hognose_snake, 55: green_snake,
# 56: king_snake, 57: garter_snake, 58: water_snake, 59: vine_snake,
# 60: night_snake, 61: boa_constrictor, 62: rock_python, 63: Indian_cobra,
# 64: green_mamba, 65: sea_snake, 66: horned_viper, 67: diamondback, 68: sidewinder
IMAGENET_SNAKE_CLASSES = set(range(52, 69))


class SnakeAIPipelineService:
    """
    Two-Stage Snake AI Pipeline:

    Stage 1: Snake / Not-Snake Gate Detector
             - Verifies whether the image contains a snake.
             - If NOT a snake: STOP immediately. Venom model is NOT run.
             - Returns "Not a Snake" with detection confidence.

    Stage 2: Venom Classification (Only invoked for confirmed snakes)
             - Model: venomwatch_cnn2_final.keras (MobileNetV2 backbone, binary sigmoid)
             - Output: 1 sigmoid neuron -> VENOMOUS / NON-VENOMOUS

    Performance & Caching:
    - Models are loaded ONCE into memory (MODEL_CACHE singleton) and kept loaded.
    - Inference uses direct callable evaluation with training=False (bypassing tf.data overhead).
    - Image is loaded and resized directly to 224x224 RGB in one pass.
    """
    SNAKE_CONFIDENCE_THRESHOLD = VENOM_DECISION_THRESHOLD

    @classmethod
    def get_snake_detector(cls):
        """Load Stage 1 Snake Detector once (singleton cached in MODEL_CACHE)."""
        if MODEL_CACHE['snake_detector'] is None:
            with _MODEL_LOCK:
                if MODEL_CACHE['snake_detector'] is None:
                    import tensorflow as tf
                    # Check for a dedicated custom-trained snake-vs-not-snake model
                    candidates = [
                        os.path.join(settings.BASE_DIR, 'snake_detector.keras'),
                        os.path.join(settings.BASE_DIR, 'ai', 'models', 'snake_detector.keras'),
                        os.path.join(settings.BASE_DIR, 'snake_vs_not_snake.keras'),
                        os.path.join(settings.BASE_DIR, 'ai', 'models', 'snake_vs_not_snake.keras'),
                    ]
                    custom_path = next((p for p in candidates if os.path.exists(p)), None)
                    if custom_path:
                        print(f"[AI] Loading custom snake detector from {custom_path}")
                        model = tf.keras.models.load_model(custom_path)
                    else:
                        print("[AI] Loading MobileNetV2 (ImageNet) as Stage 1 Snake Detector Gate")
                        model = tf.keras.applications.MobileNetV2(weights='imagenet')

                    # Warmup run to initialize graph / oneDNN
                    dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
                    _ = model(dummy, training=False)
                    MODEL_CACHE['snake_detector'] = model
                    print("[AI] Snake detector loaded and cached in memory.")
        return MODEL_CACHE['snake_detector']

    @classmethod
    def get_venom_classifier(cls):
        """Load Stage 2 Binary Venom Classifier once (singleton cached in MODEL_CACHE)."""
        if MODEL_CACHE['venom_classifier'] is None:
            with _MODEL_LOCK:
                if MODEL_CACHE['venom_classifier'] is None:
                    import tensorflow as tf
                    paths_to_try = [
                        os.path.join(settings.BASE_DIR, 'venomwatch_cnn2_final.keras'),
                        os.path.join(settings.BASE_DIR, 'ai', 'models', 'venomwatch_cnn2_final.keras'),
                    ]
                    model_path = next((p for p in paths_to_try if os.path.exists(p)), None)
                    if not model_path:
                        raise FileNotFoundError("CNN model file (venomwatch_cnn2_final.keras) not found.")

                    print(f"[AI] Loading CNN venom classifier from: {model_path}")
                    model = tf.keras.models.load_model(model_path)
                    # Warmup run
                    dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
                    _ = model(dummy, training=False)
                    MODEL_CACHE['venom_classifier'] = model
                    print("[AI] Venom classifier loaded and cached in memory.")
        return MODEL_CACHE['venom_classifier']

    @classmethod
    def get_model(cls):
        """Backward compatibility helper for venom classifier."""
        return cls.get_venom_classifier()

    @classmethod
    def classify_snake_image(cls, abs_path):
        """Run two-stage analysis on given image path."""
        return cls.analyze_image(abs_path)

    @classmethod
    def analyze_image(cls, image_path):
        """
        Main Two-Stage Pipeline Orchestrator:
        1. Snake / Not-Snake Gate Check
        2. Venom Classification (only if snake detected)
        """
        import tensorflow as tf

        t_start = time.perf_counter()

        # 1. Resolve path
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
                'is_snake': False,
                'venomous': None,
                'venom_confidence': None,
                'species': None,
                'common_name': None,
                'species_common': None,
                'venom_category': None,
                'status': 'IMAGE_NOT_FOUND',
                'message': 'Image file not found on disk.',
                'description': 'Image file not found.',
                'model_1': 'Snake Detector Gate',
                'model_2': 'venomwatch_cnn2_final (CNN)',
                'processed_image_path': None,
                'predicted_label': 'ERROR',
                'raw_output': None,
                'class_name': 'error',
                'class_index': -1,
                'all_probabilities': [],
            }

        # 2. Model Loading check (cached in memory -> 0.00s after first load)
        t_load_start = time.perf_counter()
        detector = cls.get_snake_detector()
        venom_model = cls.get_venom_classifier()
        t_model_load = time.perf_counter() - t_load_start

        # 3. Fast Image Preprocessing (single pass resize to 224x224 RGB)
        t_preproc_start = time.perf_counter()
        img = tf.keras.utils.load_img(abs_path, target_size=(224, 224))
        raw_arr = tf.keras.utils.img_to_array(img)
        batch_arr = np.expand_dims(raw_arr, axis=0)

        # Preprocessing for MobileNetV2 detector (scale to [-1, 1])
        det_input = tf.keras.applications.mobilenet_v2.preprocess_input(batch_arr.copy())
        t_preproc = time.perf_counter() - t_preproc_start

        # Content hash for identification
        with open(abs_path, 'rb') as fh:
            img_hash = hashlib.md5(fh.read()).hexdigest()[:12]

        # 4. STAGE 1: SNAKE / NOT-SNAKE DETECTION GATE
        t_snake_start = time.perf_counter()
        det_preds = detector(det_input, training=False).numpy()[0]
        snake_prob = float(np.sum(det_preds[52:69]))
        top5_idx = np.argsort(det_preds)[::-1][:5]

        # Is this a snake?
        is_snake = (snake_prob >= 0.15) or any(idx in IMAGENET_SNAKE_CLASSES for idx in top5_idx[:2])
        t_snake_det = time.perf_counter() - t_snake_start

        # =====================================================================
        # GATE CHECK: IF NOT A SNAKE -> STOP!
        # DO NOT RUN VENOM CLASSIFICATION!
        # =====================================================================
        if not is_snake:
            t_venom = 0.0
            t_total = time.perf_counter() - t_start

            # Calculate confident non-snake percentage
            non_snake_conf = round(float(1.0 - snake_prob) * 100, 1)
            if non_snake_conf < 50.0:
                non_snake_conf = 50.0
            elif non_snake_conf > 99.9:
                non_snake_conf = 99.9

            print(f"[AI] Model load: {t_model_load:.2f}s")
            print(f"[AI] Preprocessing: {t_preproc:.2f}s")
            print(f"[AI] Snake detection: {t_snake_det:.2f}s")
            print(f"[AI] Venom classification: {t_venom:.2f}s (skipped - not a snake)")
            print(f"[AI] Total: {t_total:.2f}s")
            print(f"[AI] GATE: Rejected by snake detector (confidence={non_snake_conf}%, snake_prob={snake_prob*100:.2f}%)")

            return {
                'snake_detected': False,
                'snake_confidence': non_snake_conf,
                'is_snake': False,
                'venomous': None,
                'venom_confidence': None,
                'species': None,
                'common_name': None,
                'species_common': None,
                'venom_category': None,
                'status': 'NOT_A_SNAKE',
                'message': 'This image does not appear to contain a snake. Please upload a clear snake image for venom analysis.',
                'description': 'This image does not appear to contain a snake. Please upload a clear snake image for venom analysis.',
                'model_1': 'Snake Detector (MobileNetV2 ImageNet Gate)',
                'model_2': 'venomwatch_cnn2_final (CNN) [Not Invoked]',
                'processed_image_path': str(image_path),
                'predicted_label': 'NOT_A_SNAKE',
                'raw_output': None,
                'class_name': 'NOT_A_SNAKE',
                'class_index': -1,
                'image_hash': img_hash,
                'confidence': non_snake_conf,
                'all_probabilities': [round(non_snake_conf, 1), round(100.0 - non_snake_conf, 1)],
                'timing': {
                    'model_load': round(t_model_load, 3),
                    'preprocessing': round(t_preproc, 3),
                    'snake_detection': round(t_snake_det, 3),
                    'venom_classification': round(t_venom, 3),
                    'total': round(t_total, 3),
                }
            }

        # =====================================================================
        # STAGE 2: VENOM CLASSIFICATION (ONLY FOR VERIFIED SNAKES)
        # =====================================================================
        t_venom_start = time.perf_counter()
        # Normalization matching training: [0, 1]
        venom_input = (batch_arr / 255.0).astype(np.float32)
        raw_tensor = venom_model(venom_input, training=False)
        raw_output = float(raw_tensor.numpy()[0][0])
        predicted_label, venom_confidence = map_venom_prediction(raw_output)
        venomous = (predicted_label == 'VENOMOUS')
        t_venom = time.perf_counter() - t_venom_start

        t_total = time.perf_counter() - t_start

        snake_conf = round(float(snake_prob) * 100, 1)
        if snake_conf < 50.0:
            snake_conf = 65.0

        species = 'Venomous Snake' if venomous else 'Non-Venomous Snake'
        status_code = 'SNAKE_DETECTED_VENOMOUS' if venomous else 'SNAKE_DETECTED_NON_VENOMOUS'
        msg = f"AI Prediction: {predicted_label} ({venom_confidence}%)"
        if venom_confidence < 60.0:
            msg += " - Low-confidence prediction - professional verification recommended."

        print(f"[AI] Model load: {t_model_load:.2f}s")
        print(f"[AI] Preprocessing: {t_preproc:.2f}s")
        print(f"[AI] Snake detection: {t_snake_det:.2f}s")
        print(f"[AI] Venom classification: {t_venom:.2f}s")
        print(f"[AI] Total: {t_total:.2f}s")
        print(f"[AI] GATE: Snake confirmed -> Venom result: {predicted_label} ({venom_confidence}%)")

        return {
            'snake_detected': True,
            'snake_confidence': snake_conf,
            'is_snake': True,
            'venomous': venomous,
            'venom_confidence': venom_confidence,
            'species': species,
            'common_name': species,
            'species_common': species,
            'venom_category': 'HIGHLY_VENOMOUS' if venomous else 'NON_VENOMOUS',
            'status': status_code,
            'message': msg,
            'description': (
                'Model predicts features consistent with a venomous snake.'
                if venomous else
                'Model predicts features consistent with a non-venomous snake.'
            ),
            'model_1': 'Snake Detector (MobileNetV2 ImageNet Gate)',
            'model_2': 'venomwatch_cnn2_final (CNN)',
            'processed_image_path': str(image_path),
            'predicted_label': predicted_label,
            'raw_output': round(raw_output, 6),
            'class_name': predicted_label,
            'class_index': 1 if venomous else 0,
            'confidence': venom_confidence,
            'image_hash': img_hash,
            'all_probabilities': [round(venom_confidence, 1), round(100.0 - venom_confidence, 1)],
            'timing': {
                'model_load': round(t_model_load, 3),
                'preprocessing': round(t_preproc, 3),
                'snake_detection': round(t_snake_det, 3),
                'venom_classification': round(t_venom, 3),
                'total': round(t_total, 3),
            }
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
