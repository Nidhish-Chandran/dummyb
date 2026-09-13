import os
import cv2
import numpy as np
import random
from django.conf import settings
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

# Snake AI Species & Venom Knowledge Base for Display Context
SNAKE_DATABASE = [
    {
        'species_name': 'Indian Cobra (Naja naja)',
        'common_name': 'Spectacled Cobra',
        'venom_category': 'HIGHLY_VENOMOUS',
        'description': 'Highly venomous elapid snake. AI Prediction: Venomous.'
    },
    {
        'species_name': 'Indian Rat Snake (Ptyas mucosa)',
        'common_name': 'Dhaman',
        'venom_category': 'NON_VENOMOUS',
        'description': 'Harmless non-venomous snake. AI Prediction: Non-Venomous.'
    }
]


class SnakeAIPipelineService:
    """
    Two-Stage AI Inference Pipeline with Server-Side Gate:
    Stage 1: Snake Detection (YOLOv8 - Snake Detection.v2-model_snake-detection-2.yolov8)
             Determines whether the uploaded photo contains a snake with reliable confidence.
    Stage 2: Venom Classification (Keras CNN - venom_watch_cnn2_keras)
             EXECUTED ONLY WHEN Stage 1 reliably confirms a snake (Confidence >= 70%).
             Classifies snake as Venomous vs Non-Venomous.
    """
    _model_1 = None
    _model_2 = None

    # Threshold required for Model #1 to reliably confirm a snake
    DETECTION_THRESHOLD = getattr(settings, 'SNAKE_DETECTION_THRESHOLD', 0.35)

    SNAKE_CLASS_INDICES = {0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}
    NON_SNAKE_CLASS_INDICES = {2}  # Class index 2 is 'cat'

    @classmethod
    def get_model_1(cls):
        if cls._model_1 is None:
            from ultralytics import YOLO
            paths_to_try = [
                os.path.join(settings.BASE_DIR, 'Snake Detection.v2-model_snake-detection-2.yolov8', 'best.pt'),
                os.path.join(settings.BASE_DIR, 'ai', 'models', 'best.pt'),
                os.path.join(settings.BASE_DIR, 'best.pt'),
            ]
            model_path = None
            for p in paths_to_try:
                if os.path.exists(p):
                    model_path = p
                    break
            if model_path is None:
                raise FileNotFoundError("Model #1 weights (best.pt for Snake Detection) not found.")
            
            print(f"[AI] Loading Model #1 from: {model_path}")
            cls._model_1 = YOLO(model_path)
            print(f"[AI] Model #1 class mapping: {cls._model_1.names}")
        return cls._model_1

    @classmethod
    def get_model_2(cls):
        if cls._model_2 is None:
            import keras
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
                raise FileNotFoundError("Model #2 file (venomwatch_cnn2_final.keras) not found.")
            
            print(f"[AI] Loading Model #2 from: {model_path}")
            cls._model_2 = keras.models.load_model(model_path)
        return cls._model_2

    @classmethod
    def detect_snake(cls, abs_path):
        """
        Stage 1: YOLOv8 Classification Model (15-class: 14 snake species + cat)
        Returns dict with snake_detected (bool), snake_confidence (float), predicted_label (str).
        """
        filename = os.path.basename(abs_path)
        file_size = os.path.getsize(abs_path) if os.path.exists(abs_path) else 0

        print(f"[AI] Received image: {filename}")
        print(f"[AI] Image path: {abs_path}")
        print(f"[AI] File size: {file_size} bytes")
        print(f"[AI] Model #1 inference started")

        model = cls.get_model_1()
        results = model(abs_path, verbose=False)

        print(f"[AI] Model #1 inference completed")

        if not results or not hasattr(results[0], 'probs') or results[0].probs is None:
            print("[AI] Model #1 raw output: No classification probabilities returned.")
            return {
                'snake_detected': False,
                'snake_confidence': 0.0,
                'predicted_label': 'unknown'
            }

        probs = results[0].probs.data.cpu().numpy()
        top1 = int(results[0].probs.top1)
        top1_conf = float(results[0].probs.top1conf)
        top1_name = model.names.get(top1, 'unknown')

        sum_snake_probs = float(np.sum(probs[list(cls.SNAKE_CLASS_INDICES)]))
        cat_prob = float(probs[2]) if len(probs) > 2 else 0.0

        print(f"[AI] Model #1 raw output: top1={top1} ({top1_name}), top1_conf={top1_conf*100:.1f}%, sum_snake_probs={sum_snake_probs*100:.1f}%, cat_prob={cat_prob*100:.1f}%")

        # GATING RULE: Requires top predicted class to be a snake species AND top-1 species confidence >= 35% AND total snake probability >= 85%
        is_snake = (top1 in cls.SNAKE_CLASS_INDICES) and (top1_conf >= cls.DETECTION_THRESHOLD) and (sum_snake_probs >= 0.85)

        # Confidence displayed for snake detection: combined snake species probability when snake detected, else top1 conf
        display_conf = round(sum_snake_probs * 100, 1) if is_snake else round(top1_conf * 100, 1)

        if is_snake:
            print(f"[AI] Snake gate: PASS (Top species: {top1_name} {top1_conf*100:.1f}%, Combined Snake Confidence: {display_conf}% >= {cls.DETECTION_THRESHOLD*100:.0f}%)")
            return {
                'snake_detected': True,
                'snake_confidence': display_conf,
                'predicted_label': top1_name
            }
        else:
            print(f"[AI] Snake gate: FAIL (Top species: {top1_name} {top1_conf*100:.1f}% < {cls.DETECTION_THRESHOLD*100:.0f}% threshold or non-snake class)")
            return {
                'snake_detected': False,
                'snake_confidence': display_conf,
                'predicted_label': top1_name if top1 in cls.NON_SNAKE_CLASS_INDICES else 'no snake'
            }

    @classmethod
    def classify_venom(cls, abs_path):
        """
        Stage 2: Keras CNN Venomous Classification
        Executed ONLY when Stage 1 reliably confirms a snake.
        Returns dict with venomous (bool), venom_confidence (float).
        """
        print("[AI] Model #2 inference started")
        model = cls.get_model_2()
        
        img = cv2.imread(abs_path)
        if img is None:
            print("[AI] Model #2 inference completed: Could not read image.")
            return {'venomous': False, 'venom_confidence': 50.0}

        img_resized = cv2.resize(img, (224, 224))
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        arr = np.expand_dims(img_rgb / 255.0, axis=0)

        pred = float(model.predict(arr, verbose=0)[0][0])
        
        # Sigmoid binary classification: >= 0.5 is Venomous
        if pred >= 0.5:
            venomous = True
            conf = round(pred * 100, 1)
        else:
            venomous = False
            conf = round((1.0 - pred) * 100, 1)

        print(f"[AI] Model #2 inference completed: venomous={venomous}, confidence={conf}%")
        return {
            'venomous': venomous,
            'venom_confidence': conf
        }

    @classmethod
    def analyze_image(cls, image_path):
        """
        Full Two-Stage Pipeline Orchestrator with Strict Server-Side Gate.
        """
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
                'status': 'NO_RELIABLE_SNAKE_DETECTED',
                'message': 'Image file not found on disk.',
                'model_1': 'Snake Detection.v2-model_snake-detection-2.yolov8',
                'model_2': None,
                'processed_image_path': None
            }

        # --- STAGE 1: SNAKE DETECTION ---
        try:
            stage1 = cls.detect_snake(abs_path)
        except Exception as e:
            print(f"[AI] Snake Detection Exception: {e}")
            return {
                'snake_detected': False,
                'snake_confidence': 0.0,
                'venomous': None,
                'venom_confidence': None,
                'status': 'NO_RELIABLE_SNAKE_DETECTED',
                'message': f'Snake Detection error: {str(e)}',
                'model_1': 'Snake Detection.v2-model_snake-detection-2.yolov8',
                'model_2': None,
                'processed_image_path': str(image_path)
            }

        # STRICT SERVER-SIDE GATE: IF NO RELIABLE SNAKE DETECTED, RETURN IMMEDIATELY & SKIP MODEL #2
        if not stage1['snake_detected']:
            print("[AI] Model #2: SKIPPED (Snake gate failed)")
            return {
                'snake_detected': False,
                'snake_confidence': stage1['snake_confidence'],
                'venomous': None,
                'venom_confidence': None,
                'status': 'NO_RELIABLE_SNAKE_DETECTED',
                'message': f"Unable to reliably confirm a snake in the image (Detection Confidence: {stage1['snake_confidence']}%).",
                'model_1': 'Snake Detection.v2-model_snake-detection-2.yolov8',
                'model_2': None,
                'processed_image_path': str(image_path)
            }

        # --- STAGE 2: VENOM CLASSIFICATION (RUNS ONLY IF STAGE 1 GATE PASSED) ---
        try:
            stage2 = cls.classify_venom(abs_path)
        except Exception as e:
            print(f"[AI] Venom Classification Exception: {e}")
            stage2 = {'venomous': False, 'venom_confidence': 50.0}

        is_venom = stage2['venomous']
        venom_conf = stage2['venom_confidence']

        if is_venom:
            status_code = 'SNAKE_DETECTED_VENOMOUS'
            msg = f"AI Prediction: Venomous ({venom_conf}%)"
            if venom_conf < 60.0:
                msg += " — Low-confidence prediction — professional verification recommended."
        else:
            status_code = 'SNAKE_DETECTED_NON_VENOMOUS'
            msg = f"AI Prediction: Non-Venomous ({venom_conf}%)"
            if venom_conf < 60.0:
                msg += " — Low-confidence prediction — professional verification recommended."

        return {
            'snake_detected': True,
            'snake_confidence': stage1['snake_confidence'],
            'venomous': is_venom,
            'venom_confidence': venom_conf,
            'status': status_code,
            'message': msg,
            'species': f"{stage1.get('predicted_label', 'Snake').capitalize()} Snake",
            'venom_category': 'HIGHLY_VENOMOUS' if is_venom else 'NON_VENOMOUS',
            'model_1': 'Snake Detection.v2-model_snake-detection-2.yolov8',
            'model_2': 'venom_watch_cnn2_keras',
            'processed_image_path': str(image_path)
        }


# Backward compatibility alias
class SnakeAIDetectionService(SnakeAIPipelineService):
    pass


class WoundScreeningService:
    """
    Dedicated Binary Snakebite Wound Image Checker.
    Performs visual feature screening (Dual Fang Puncture Pair & Localized Erythema Analysis).
    Binary Output ONLY: "Snake Bite" (Possible Snake Bite Pattern Detected) vs "Not Snake Bite" (No Snake-Bite Pattern Detected).
    Clearly labeled as prototype/heuristic screening method (Dataset model training in progress).
    Does NOT diagnose severity, venom type, species, treatment, or medical condition.
    Includes mandatory emergency medical disclaimer.
    """

    MANDATORY_DISCLAIMER = (
        "This is an AI-assisted screening tool and is NOT a medical diagnosis. "
        "If a snakebite is suspected, seek emergency medical care immediately."
    )

    @classmethod
    def analyze_wound_image(cls, image_path):
        abs_path = os.path.join(settings.MEDIA_ROOT, str(image_path)) if not os.path.isabs(str(image_path)) else str(image_path)

        if not os.path.exists(abs_path):
            return {
                'is_snake_bite': False,
                'result_label': 'Not Snake Bite',
                'status_title': 'No Snake-Bite Pattern Detected',
                'recommendation': 'Image file not found on disk. Please upload a valid photo of the affected area.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'Prototype / Heuristic Visual Feature Screening (Dataset Model Training In Progress)',
                'processed_image_path': None
            }

        img = cv2.imread(abs_path)
        if img is None:
            return {
                'is_snake_bite': False,
                'result_label': 'Not Snake Bite',
                'status_title': 'Invalid / Non-Image File Uploaded',
                'recommendation': 'The uploaded file could not be decoded as a valid photo. Please upload a valid JPG or PNG image.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'Prototype / Heuristic Visual Feature Screening (Dataset Model Training In Progress)',
                'processed_image_path': None
            }

        height, width, _ = img.shape

        # 1. Erythema / Redness Ratio Analysis in HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 40, 40])
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 40, 40])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 | mask2

        red_ratio = np.sum(red_mask > 0) / float(height * width)

        # 2. Dual Fang Puncture Contour Detection within Redness Region
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Binary thresholding for sharp dark puncture marks
        _, thresh = cv2.threshold(blurred, 90, 255, cv2.THRESH_BINARY_INV)
        
        # Restrict contour search to inflamed/redness region (dilated for boundary coverage)
        kernel = np.ones((15, 15), np.uint8)
        dilated_red = cv2.dilate(red_mask, kernel, iterations=2)
        masked_thresh = cv2.bitwise_and(thresh, thresh, mask=dilated_red)

        contours, _ = cv2.findContours(masked_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        puncture_centers = []
        annotated_img = img.copy()

        for c in contours:
            area = cv2.contourArea(c)
            if 8 < area < 500: # Tight size filter for fang punctures
                perimeter = cv2.arcLength(c, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if circularity > 0.25: # Circular/oval shape
                        (x, y), radius = cv2.minEnclosingCircle(c)
                        puncture_centers.append((int(x), int(y), radius))

        # Check for at least ONE valid pair of puncture marks separated by realistic fang distance (15px - 150px)
        has_fang_pair = False
        for i in range(len(puncture_centers)):
            for j in range(i + 1, len(puncture_centers)):
                x1, y1, r1 = puncture_centers[i]
                x2, y2, r2 = puncture_centers[j]
                dist = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                if 15 <= dist <= 150: # Valid fang distance in pixels
                    has_fang_pair = True
                    cv2.circle(annotated_img, (x1, y1), int(r1) + 4, (0, 0, 255), 2)
                    cv2.circle(annotated_img, (x2, y2), int(r2) + 4, (0, 0, 255), 2)
                    cv2.line(annotated_img, (x1, y1), (x2, y2), (0, 165, 255), 2)

        # Decision rule: Requires localized erythema AND an identified fang puncture pair
        is_snake_bite = (has_fang_pair or red_ratio >= 0.08) if (has_fang_pair and red_ratio >= 0.02) else False

        # Save annotated wound screening image
        processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed_wounds')
        os.makedirs(processed_dir, exist_ok=True)
        base_name = os.path.basename(abs_path)
        processed_filename = f"wound_ai_{base_name}"
        processed_file_path = os.path.join(processed_dir, processed_filename)
        cv2.imwrite(processed_file_path, annotated_img)

        rel_processed_path = f"processed_wounds/{processed_filename}"

        if is_snake_bite:
            return {
                'is_snake_bite': True,
                'result_label': 'Snake Bite',
                'status_title': 'Possible Snake Bite Pattern Detected',
                'recommendation': 'Dual puncture mark geometry and localized erythema detected. Immobilize limb, keep patient calm, and seek emergency hospital care immediately.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'Prototype / Heuristic Visual Feature Screening (Dataset Model Training In Progress)',
                'processed_image_path': rel_processed_path
            }
        else:
            return {
                'is_snake_bite': False,
                'result_label': 'Not Snake Bite',
                'status_title': 'No Snake-Bite Pattern Detected',
                'recommendation': 'Characteristic dual puncture fang pattern was not identified in the uploaded image.',
                'disclaimer': cls.MANDATORY_DISCLAIMER,
                'method_label': 'Prototype / Heuristic Visual Feature Screening (Dataset Model Training In Progress)',
                'processed_image_path': rel_processed_path
            }
