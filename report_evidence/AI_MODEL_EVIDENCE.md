# AI Model Evidence Report — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-AI-EVIDENCE  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  
**Verification Standard:** Empirical Source-Code & Binary Header Extraction  

---

## 1. AI Pipeline Overview

The active VenomWatch application deploys two distinct, operational deep learning pipelines:
1. **Pipeline 1: Snake Encounter & Venom Classification Pipeline (`SnakeAIPipelineService`)**  
   A two-stage sequential gate system:
   - *Stage 1:* MobileNetV2 ImageNet Gate Detector (identifies if the image contains a snake).
   - *Stage 2:* `venomwatch_cnn2_final.keras` (classifies confirmed snakes into Venomous or Non-Venomous).
2. **Pipeline 2: Snakebite Wound Screening Service (`SnakebiteScreeningService`)**  
   An EfficientNetB0 binary classifier (`venom_watch_snakebite_efficientnetb0.keras`) evaluating puncture wound photographs for snakebite characteristics, incorporating an uncertainty safety interval.
3. **Archived / Inactive Artifact:**  
   `ai/models/best.pt` — an Ultralytics YOLOv8n-cls 15-class species classification model from earlier project research.

---

## 2. Model 1: Snake / Not-Snake Gate Detector

### 2.1 Technical Specification
- **Implementation Source:** [`ai/services.py:SnakeAIPipelineService.get_snake_detector()`](file:///d:/dummyb/ai/services.py#L97-L124) and `analyze_image()` (lines 205–285).
- **Architecture:** Pretrained `tf.keras.applications.MobileNetV2(weights='imagenet')`.
- **Input Dimensions:** $224 \times 224 \times 3$ RGB tensor.
- **Normalization:** Scaled to $[-1.0, 1.0]$ via `tf.keras.applications.mobilenet_v2.preprocess_input()`.
- **Target Synsets:** Evaluates ImageNet class indices 52 through 68 inclusive (Suborder *Serpentes*):
  - 52: thunder snake, 53: ringneck snake, 54: hognose snake, 55: green snake,
  - 56: king snake, 57: garter snake, 58: water snake, 59: vine snake,
  - 60: night snake, 61: boa constrictor, 62: rock python, 63: Indian cobra,
  - 64: green mamba, 65: sea snake, 66: horned viper, 67: diamondback, 68: sidewinder.
- **Decision Logic:**
  $$\text{snake\_prob} = \sum_{i=52}^{68} P_i$$
  $$\text{is\_snake} = (\text{snake\_prob} \ge 0.15) \lor (\text{any}(\text{top2\_indices} \in [52, 68]))$$
- **Gate Behavior:**
  - If `is_snake == False`: Execution terminates immediately. The function returns `status: 'NOT_A_SNAKE'` with a confidence score of $(1.0 - \text{snake\_prob}) \times 100$. The Stage 2 venom model is **not invoked**, preventing false classifications on non-reptilian images.
  - If `is_snake == True`: Image proceeds to Stage 2.
- **Operational Status:** **Active Production Gate** in the live reporting workflow.

---

## 3. Model 2: Binary Venom Classification Model

### 3.1 Technical Specification
- **Model Filename:** `venomwatch_cnn2_final.keras`
- **Physical Locations:** Root directory (`d:\dummyb\venomwatch_cnn2_final.keras`) and backup in `ai/models/`.
- **File Size:** 23,681,696 bytes (~22.58 MB).
- **Framework & Format:** Keras 3.13.2 / TensorFlow (`.keras` zip archive containing `config.json` and `model.weights.h5`).
- **Implementation Source:** [`ai/services.py:SnakeAIPipelineService.get_venom_classifier()`](file:///d:/dummyb/ai/services.py#L126-L148) and `map_venom_prediction()` (lines 50–59).

### 3.2 Verified Layer Architecture (Extracted from Binary Header)
```
Sequential(
  InputLayer(input_shape=(None, 224, 224, 3)),
  Functional('mobilenetv2_1.00_224', pre-trained feature extractor),
  GlobalAveragePooling2D(),
  Dropout(rate=0.30),
  Dense(units=128, activation='relu'),
  Dropout(rate=0.25),
  Dense(units=1, activation='sigmoid')
)
```
- **Total Output Neurons:** 1 (Single scalar sigmoid activation).
- **Input Preprocessing:** Scaled to $[0.0, 1.0]$ via pixel division: `batch_arr / 255.0`.
- **Decision Boundary:**
  - Raw output $p \in [0.0, 1.0]$.
  - $p \ge 0.50 \implies \text{VENOMOUS}$, Confidence $= p \times 100\%$, Category: `HIGHLY_VENOMOUS`.
  - $p < 0.50 \implies \text{NON-VENOMOUS}$, Confidence $= (1.0 - p) \times 100\%$, Category: `NON_VENOMOUS`.
- **Operational Status:** **Active Production Classifier**.

### 3.3 Training & Evaluation Evidence
- **Colab Checkpoint Metadata:** Saved on `2026-09-09 16:18:41 UTC` using Keras 3.13.2.
- **Training Logs:** No training epoch CSV history or TensorBoard log directory is stored in the repository.
- **Reported vs. Verified Status:** Model architecture, input shape, normalization, and inference behavior are **100% verified from active code and binary inspection**. Historical per-epoch training curves cannot be reconstructed from the weights file alone.

---

## 4. Model 3: Snakebite Wound Screening Model

### 4.1 Technical Specification
- **Model Filename:** `venom_watch_snakebite_efficientnetb0.keras`
- **Physical Location:** Root directory (`d:\dummyb\venom_watch_snakebite_efficientnetb0.keras`).
- **File Size:** 35,347,532 bytes (~33.71 MB).
- **Framework & Format:** Keras 3.13.2 / TensorFlow (`.keras` zip archive).
- **Implementation Source:** [`ai/services.py:SnakebiteScreeningService`](file:///d:/dummyb/ai/services.py#L359-L515) and [`ai/views.py:wound_checker_view`](file:///d:/dummyb/ai/views.py#L57-L106).

### 4.2 Verified Layer Architecture (Extracted from Binary Header)
```
Functional(
  InputLayer(input_shape=(None, 224, 224, 3)),
  Sequential('data_augmentation', layers=[RandomFlip, RandomRotation]),
  Functional('efficientnetb0', backbone feature extractor),
  GlobalAveragePooling2D(),
  Dense(units=128, activation='relu'),
  BatchNormalization(),
  Dropout(rate=0.40),
  Dense(units=1, activation='sigmoid')
)
```
- **Input Preprocessing:** $224 \times 224 \times 3$ RGB, float32 conversion.
- **Decision Thresholds & Safety Logic:**
  - Raw sigmoid output $p \in [0.0, 1.0]$.
  - $p \ge 0.50 \implies \text{Possible Snakebite Pattern Detected}$ (Confidence $= p \times 100\%$).
  - $p < 0.50 \implies \text{No Snakebite Pattern Detected}$ (Confidence $= (1.0 - p) \times 100\%$).
  - **Uncertainty Band:** If $0.40 \le p \le 0.60$, the system raises `uncertain = True`, overriding the title to `Unable to Confidently Classify` and recommending immediate medical consultation.
  - **Mandatory Non-Diagnostic Disclaimer:** Displayed on all views: *"This is an AI-assisted screening tool and is NOT a medical diagnosis. If a snakebite is suspected, seek emergency medical care immediately."*
- **Operational Status:** **Active Production Screening Tool**.

---

## 5. Inactive / Archived Model: YOLOv8n-cls Multi-Class Species Classifier

### 5.1 Technical Specification
- **Model Filename:** `best.pt`
- **Location:** `ai/models/best.pt`
- **File Size:** 3,000,584 bytes (~2.86 MB).
- **Framework:** PyTorch / Ultralytics YOLO 8.4.137.
- **Architecture:** `ultralytics.nn.tasks.ClassificationModel` (Backbone: Conv-C2f-SPPF, Head: Classify 15 classes).
- **Input Channels:** 3 (RGB), Image Size: 224.
- **Target Classes (15 Species):** `black`, `boa`, `cat`, `cobra`, `common`, `keelback`, `krait`, `kukri`, `pit`, `python`, `racer`, `rat`, `russell`, `saw`, `wolf`.
- **Runtime Status:** **Inactive / Not Executed**. No imports of `ultralytics` or `torch` exist in active web views.

### 5.2 Recovered Training Metrics from Checkpoint Binary
The checkpoint dictionary retained its complete 50-epoch training ledger under `train_results` and summary statistics under `train_metrics`:
- **Training Environment:** Google Colab GPU (Tesla T4).
- **Training Date:** September 1, 2026 (Duration: 307.34 seconds).
- **Selected Best Checkpoint:** **Epoch 10**
  - **Validation Loss:** `1.33766`
  - **Top-1 Accuracy:** **65.625%** (0.65625)
  - **Top-5 Accuracy:** **91.146%** (0.91146)
  - **Fitness Score:** `0.78385` ($\text{fitness} = 0.5 \times \text{Top-1} + 0.5 \times \text{Top-5}$)
- **Evidence Charts Plotted from Checkpoint Arrays:**
  - `docs/evidence/yolov8_training_validation_loss.png`
  - `docs/evidence/yolov8_validation_accuracy.png`

---

## 6. Dataset Provenance & Image Inventories

Historical dataset objects preserved in Git revision `5b6821101e21692ae0f17b165ffe173bb4484a5c` document the original species distributions:

### 6.1 Organized Split Dataset (969 Images)
- Total images: 969 (Train: 777, Validation: 192, Test: 0).
- Species distribution:
  - `black` (Black Headed Royal Snake): 56 train, 12 val (Total: 68) — Non-Venomous
  - `boa` (Indian Sand Boa): 56 train, 14 val (Total: 70) — Non-Venomous
  - `cat` (Indian Gamma / Cat Snake): 56 train, 14 val (Total: 70) — Mildly Venomous
  - `cobra` (Spectacled Cobra): 56 train, 14 val (Total: 70) — Highly Venomous
  - `common` (Common Trinket Snake): 47 train, 12 val (Total: 59) — Non-Venomous
  - `keelback` (Checkered Keelback): 48 train, 12 val (Total: 60) — Non-Venomous
  - `krait` (Common Krait): 48 train, 12 val (Total: 60) — Highly Venomous
  - `kukri` (Common Kukri Snake): 58 train, 14 val (Total: 72) — Non-Venomous
  - `pit` (Bamboo Pit Viper): 48 train, 12 val (Total: 60) — Venomous
  - `python` (Indian Rock Python): 48 train, 12 val (Total: 60) — Non-Venomous
  - `racer` (Banded Racer): 48 train, 12 val (Total: 60) — Non-Venomous
  - `rat` (Indian Rat Snake): 48 train, 12 val (Total: 60) — Non-Venomous
  - `russell` (Russell's Viper): 56 train, 14 val (Total: 70) — Highly Venomous
  - `saw` (Saw-scaled Viper): 56 train, 14 val (Total: 70) — Highly Venomous
  - `wolf` (Indian Wolf Snake): 48 train, 12 val (Total: 60) — Non-Venomous

### 6.2 Raw Uncurated Image Collection (2,927 Images)
Prior to balanced downsampling, the raw repository folder contained 2,927 raw images across the 15 categories.
