# VenomWatch — Complete Project Structure and Architecture Audit

**Project:** VenomWatch — AI-Assisted Snake Incident Surveillance & Rapid Response Management System  
**Academic Level:** Master of Computer Applications (MCA) Final Project  
**Author / Lead Architect:** Senior Software Architect Source-Code Audit  
**Target Repository:** `VenomWatch` (Django 4.x / Python 3.10+ / SQLite3 / TensorFlow / Scikit-Learn)  
**Document Classification:** Final Technical Reference & Academic Architecture Specification  
**File Location:** `docs/venomwatch_final_architecture_audit.md`  

---

## 1. Executive Summary of the Final Implemented System

**VenomWatch** is an enterprise-grade, multi-role environmental intelligence and emergency management web application developed using the Django framework. The primary objective of the system is to mitigate human-snake conflict, accelerate medical response to snakebites, and provide wildlife conservation authorities with real-time geospatial surveillance.

The system is organized around four distinct user roles:
1. **Citizen (General Public):** Submits geo-referenced snake sightings with image uploads, screens suspected snakebite wound images using deep learning, accesses a live directory of anti-venom-equipped hospitals sorted by geodesic distance, and initiates one-touch Emergency SOS distress broadcasts.
2. **Authority Officer (Dispatch & Verification):** Exercises centralized command over incoming reports, verifies sighting authenticity, inspects duplicate and spam telemetry, tracks incidents on an operational GIS Leaflet map, executes algorithmic location-based dispatch of Forest Rangers, and conducts formal review/approval of field outcomes.
3. **Forest Ranger (Field Responder):** Operates within an isolated, security-hardened mobile-first console. Rangers review only assignments explicitly dispatched to them, update response milestones (`ACCEPTED` $\rightarrow$ `ON_THE_WAY` $\rightarrow$ `AT_LOCATION` $\rightarrow$ `OUTCOME_SUBMITTED`), capture field evidence photos, and record intervention results (`SNAKE_CAPTURED`, `SNAKE_RELOCATED`, etc.). Rangers cannot self-complete incidents; all closures require Authority sign-off.
4. **Platform Administrator:** Maintains governance over operational accounts, reviews official Authority and Ranger registration applications with private supporting credential verification, manages account security states (`ACTIVE`, `SUSPENDED`, `BANNED`), and maintains the regional hospital and anti-venom vial registry.

### Core Architectural Reality vs. Legacy Presentation Discrepancies
A critical finding of this source-code audit is that earlier presentations and project pitch decks described prospective or legacy components that **do not match the actual codebase**:
- **No YOLO Detection Model in Execution:** An unused 3 MB file (`ai/models/best.pt`) exists on the filesystem, but **no YOLO model is loaded, imported, or executed** anywhere in the active Python runtime or views.
- **No 15-Class Species Classifier:** Legacy variables (`SNAKE_SPECIES_DATABASE = {}`, `CLASS_NAMES = ['NON-VENOMOUS', 'VENOMOUS']`) exist only as dormant stubs in `ai/services.py`. There is no multi-class species model in active use.
- **True AI Pipeline 1 (Snake & Venom Classification):** The active pipeline is a **Two-Stage Gate Architecture**. Stage 1 executes an ImageNet-pretrained `MobileNetV2` model as an entrance gate checking synset classes 52–68 (Suborder *Serpentes*). If an image fails the gate, it is rejected immediately as `NOT_A_SNAKE` without invoking Stage 2. Stage 2 executes `venomwatch_cnn2_final.keras` (23.68 MB, MobileNetV2 backbone with a single sigmoid output) performing binary classification: `p >= 0.5` $\rightarrow$ `VENOMOUS`, `p < 0.5` $\rightarrow$ `NON-VENOMOUS`.
- **True AI Pipeline 2 (Snakebite Wound Screening):** An operational `EfficientNetB0` binary classifier (`venom_watch_snakebite_efficientnetb0.keras`, 35.35 MB) accepts 224x224 RGB wound photographs and predicts whether characteristic fang puncture patterns exist (`p >= 0.5` $\rightarrow$ `Possible Snakebite Pattern Detected`), supplemented by an explicit uncertainty band `[0.4, 0.6]` and mandatory non-diagnostic disclaimers.
- **Dynamic DBSCAN Geospatial Clustering:** Spatial clustering is **not stored in database tables**. The service `DBSCANHotspotService` dynamically executes `sklearn.cluster.DBSCAN` with the Haversine spherical distance metric (`algorithm='ball_tree'`) at runtime over active, non-duplicate sightings, grouping incidents into four risk states: Red (High Risk), Orange (Caution), Yellow (Cooldown), and Green (Safe Retention).

---

## 2. Complete Project Directory and Django Application Structure

The codebase adheres strictly to Django's modular application architecture, with clear separation of concerns across accounts, incident reporting, deep learning inference, spatial analytics, emergency logistics, and responder field operations.

```
d:\dummyb\
├── manage.py                          # Django CLI management script
├── db.sqlite3                         # SQLite runtime database
├── requirements.txt                   # Project dependency manifest
├── venomwatch_cnn2_final.keras        # Deployed Model 1 (Binary Venom Classifier, 23.68 MB)
├── venom_watch_snakebite_efficientnetb0.keras # Deployed Model 2 (Wound Classifier, 35.35 MB)
│
├── venomwatch/                        # Project Root Configuration
│   ├── __init__.py
│   ├── asgi.py                        # ASGI entrypoint
│   ├── wsgi.py                        # WSGI production server entrypoint
│   ├── settings.py                    # Global configuration, installed apps, media/static
│   └── urls.py                        # Top-level URL routing and protected media gates
│
├── accounts/                          # Authentication, Roles, Applications & Audit
│   ├── models.py                      # UserProfile, AccountApplication, Notification, AuditLog
│   ├── views.py                       # Login, Register, Admin Console, Application Review, Document Serving
│   ├── forms.py                       # UserRegistrationForm, UserProfileForm, Provisioning Forms
│   ├── decorators.py                  # @authority_required, @ranger_required, @admin_required
│   ├── urls.py                        # Auth routes, admin dashboard, application workflow
│   ├── tests.py                       # 33 unit tests covering accounts, security, and approval flows
│   └── admin.py                       # Django standard admin integration
│
├── reports/                           # Citizen Sighting & Incident Management
│   ├── models.py                      # SightingReport, RangerAssignment
│   ├── views.py                       # create_report_view, list_reports_view, detail, verify, assign, GIS map
│   ├── forms.py                       # SightingReportForm, AssignmentUpdateForm
│   ├── services.py                    # DuplicateSpamDetectionService (Haversine & temporal scoring)
│   ├── dispatch.py                    # Location-based candidate ranger dispatch engine
│   ├── urls.py                        # Sighting endpoints, public risk zones, authority operations map
│   └── tests.py                       # 54 KB comprehensive test suite for reporting lifecycle
│
├── ai/                                # Deep Learning Inference Engine
│   ├── models/                        # Serialized weights and artifacts
│   │   ├── best.pt                    # Inactive YOLO weight artifact (not used in runtime)
│   │   ├── venomwatch_cnn2_final.keras # Backup copy of venom classifier
│   │   └── snake_detector.keras       # Optional custom detector candidate
│   ├── services.py                    # SnakeAIPipelineService, SnakebiteScreeningService
│   ├── views.py                       # SnakeAIAnalysisAPIView, wound_checker_view
│   ├── urls.py                        # REST API /ai/api/analyze/, /ai/wound-check/
│   └── tests.py                       # AI service validation tests
│
├── hotspots/                          # Geospatial Density Clustering & Radar
│   ├── models.py                      # (Empty: all clustering is dynamic and calculated on the fly)
│   ├── services.py                    # DBSCANHotspotService (DBSCAN + Haversine 4-state lifecycle)
│   ├── views.py                       # hotspots_view, hotspots_api_view
│   ├── urls.py                        # /hotspots/, /hotspots/api/
│   └── tests.py                       # Spatial clustering test cases
│
├── ranger/                            # Isolated Forest Ranger Field Console
│   ├── views.py                       # ranger_dashboard_view, assignment_list, detail, update
│   ├── urls.py                        # /ranger/, /ranger/assignments/, /ranger/profile/
│   └── tests.py                       # 11 KB test suite verifying ranger lifecycle and object security
│
├── emergency/                         # Emergency SOS & Hospital Registry
│   ├── models.py                      # Hospital, EmergencySOSEvent
│   ├── views.py                       # assistance_view, sos_trigger_api, sos_feed_api, admin CRUD
│   ├── forms.py                       # HospitalForm
│   ├── urls.py                        # /emergency/, /emergency/api/sos/, /emergency/manage/
│   └── tests.py                       # 15 unit tests covering emergency assistance and hospital management
│
├── dashboard/                         # Surveillance Hub & Landing Routing
│   ├── views.py                       # landing_page_view, dashboard_home_view
│   └── urls.py                        # /, /dashboard/authority/
│
├── templates/                         # Modular HTML5 Templates
│   ├── base.html                      # Global responsive master layout
│   ├── landing.html                   # Public landing page
│   ├── accounts/                      # Auth, profile, admin console, application review
│   ├── reports/                       # Incident create, list, detail, authority_map, risk_zones
│   ├── ranger/                        # Ranger mobile-first dashboard, assignments, outcome modal
│   ├── emergency/                     # Assistance directory, hospital manager, emergency SOS
│   ├── ai/                            # Wound checker screening interface
│   └── hotspots/                      # Authority hotspot radar interface
│
├── static/                            # Static Assets
│   ├── css/                           # styles.css, custom design systems
│   └── js/                            # Leaflet integrations, dynamic UI helpers
│
└── media/                             # Runtime User Uploads
    ├── sightings/                     # Citizen snake upload photos
    ├── assignment_outcomes/           # Ranger field evidence photos
    ├── verification_docs/             # Protected official ID documents (blocked from public HTTP)
    └── wounds/                        # Transient wound screening uploads
```

---

## 3. Role and Permission Matrix

The application enforces strict **server-side role-based access control (RBAC)** and **object-level security** across views, API endpoints, and static file serving. Role membership is determined by `UserProfile.role` (`accounts/models.py`), reinforced by custom decorators in `accounts/decorators.py` and explicit query filtering.

### User Roles Overview
- **Citizen (`citizen`):** Self-registered member of the general public.
- **Authority (`authority`):** Verified wildlife officer or dispatch supervisor. Requires approved registration application or direct administrator provisioning.
- **Ranger (`ranger`):** Field responder responsible for physical snake rescue and containment. Operates exclusively within assigned geographic radius.
- **Administrator (`admin`):** System administrator (superuser or explicit admin profile) with full administrative governance.

### Server-Enforced Permission Matrix

| Functional Capability | Citizen | Authority | Ranger | Administrator | Enforcing Source File & Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Self-Registration (Immediate Active)** | Yes | No | No | No | `accounts/views.py`: `register_view()` auto-activates only citizens. |
| **Official Role Application (Pending Approval)** | N/A | Yes | Yes | N/A | `accounts/models.py`: `AccountApplication` required; `is_active=False`. |
| **Submit Snake Sighting Report** | Yes | Yes | No | Yes | `reports/views.py`: `create_report_view()`. |
| **View Own Sighting Reports** | Yes | Yes | Yes | Yes | `reports/views.py`: `list_reports_view()` (`user=request.user`). |
| **View All Sighting Reports Across Region** | No | Yes | No | Yes | `reports/views.py`: `list_reports_view()` gated by `profile.is_authority`. |
| **Access Dedicated Ranger Console (`/ranger/`)** | No | No | Yes | No | `ranger/views.py`: `@ranger_required` decorator. |
| **Accept / Decline Assigned Incident** | No | No | Yes | No | `ranger/views.py`: `assignment_update_view()` (filtered by `ranger=user`). |
| **Advance Field Response Status (`ON_THE_WAY`, `AT_LOCATION`)** | No | No | Yes | No | `ranger/views.py`: `assignment_update_view()` transitions. |
| **Submit Outcome Notes & Evidence Photo** | No | No | Yes | No | `ranger/views.py`: `assignment_update_view()` (`STATUS_OUTCOME_SUBMITTED`). |
| **Self-Verify & Complete Sighting** | No | No | **Forbidden** | Yes | `reports/models.py`: `RangerAssignment.ALLOWED_TRANSITIONS` blocks ranger completion. |
| **Dispatch / Assign Ranger to Incident** | No | Yes | No | Yes | `reports/views.py`: `assign_responder_view()` + `get_candidate_rangers()`. |
| **Cancel / Reassign Active Ranger** | No | Yes | No | Yes | `reports/views.py`: `cancel_assignment_view()`. |
| **Review Ranger Outcome (Approve/Reject/Clarify)** | No | Yes | No | Yes | `reports/views.py`: `review_assignment_outcome_view()`. |
| **Mark Sighting Verified / Closed** | No | Yes | No | Yes | `reports/views.py`: `verify_report_view()`, `review_assignment_outcome_view()`. |
| **View Authority Operations Map (`/reports/map/`)** | No | Yes | No | Yes | `reports/views.py`: `@authority_required` on `authority_map_view()`. |
| **View Public Risk Zones Map (`/reports/risk-zones/`)** | Yes | Yes | Yes | Yes | `reports/views.py`: `risk_zones_public_view()` (privacy-preserving). |
| **Access DBSCAN Hotspot Radar (`/hotspots/`)** | No | Yes | No | Yes | `hotspots/views.py`: `@authority_required` on `hotspots_view()`. |
| **Screen Snakebite Wound Image** | Yes | Yes | Yes | Yes | `ai/views.py`: `wound_checker_view()`. |
| **Trigger Emergency SOS Distress Broadcast** | Yes | Yes | Yes | Yes | `emergency/views.py`: `sos_trigger_api()`. |
| **Acknowledge / Resolve Emergency SOS** | No | Yes | No | Yes | `emergency/views.py`: `sos_acknowledge_api()` (`@authority_required`). |
| **Manage Hospital & Anti-Venom Registry (CRUD)** | No | No | No | Yes | `emergency/views.py`: `@admin_required` on `admin_hospital_manage_view()`. |
| **Review Registration Applications Queue** | No | No | No | Yes | `accounts/views.py`: `admin_provision_account_view()`. |
| **Approve / Reject Operational Application** | No | No | No | Yes | `accounts/views.py`: `admin_provision_account_view()` (atomic transaction). |
| **Inspect Protected Verification Documents** | No | No | No | Yes | `accounts/views.py`: `admin_application_document_view()`. |
| **Block Direct Public Document URLs** | Enforced | Enforced | Enforced | Enforced | `accounts/views.py`: `protected_media_block_view()` returns 403 on `/media/verification_docs/`. |
| **Suspend / Ban / Reinstate Accounts** | No | No | No | Yes | `accounts/views.py`: `admin_provision_account_view()` (records `AuditLog`). |

---

## 4. Verified AI Models and Their Exact Responsibilities

The system implements two independent, operational deep learning pipelines. A thorough review of `ai/services.py`, `ai/views.py`, and the model storage artifacts confirms their architectural specifications:

```
                                 ========================================
                                 VENOMWATCH DEEP LEARNING INFERENCE SUITE
                                 ========================================

   [ PIPELINE 1: Snake Sighting & Venom Analysis ]          [ PIPELINE 2: Snakebite Wound Screening ]
   
                     User Upload Image                                         User Upload Photo
                             │                                                         │
                             ▼                                                         ▼
              Single-pass RGB 224x224 resize                            Single-pass RGB 224x224 resize
                             │                                                         │
                             ▼                                                         ▼
                ┌─────────────────────────┐                               ┌─────────────────────────┐
                │     STAGE 1: GATE       │                               │   EfficientNetB0 Model  │
                │  MobileNetV2 (ImageNet) │                               │ venom_watch_snakebite_  │
                │   Classes 52-68 Check   │                               │  efficientnetb0.keras   │
                └────────────┬────────────┘                               └────────────┬────────────┘
                             │                                                         │
              Is snake_prob >= 0.15 or top-2?                                          ▼
                   ├── NO ───► STOP: Return NOT_A_SNAKE                      Raw Sigmoid Output p
                   │           (Skip Stage 2 completely)                               │
                   └── YES                                                ┌────────────┼────────────┐
                             │                                            ▼            ▼            ▼
                             ▼                                         p < 0.40   0.40<=p<=0.60   p > 0.60
                ┌─────────────────────────┐                            (Negative)  (Uncertain)   (Positive)
                │    STAGE 2: VENOM CNN   │                                │           │            │
                │ venomwatch_cnn2_final   │                                ▼           ▼            ▼
                │   (MobileNetV2 Backbone)│                            No Pattern   Inconclusive   Possible Bite
                └────────────┬────────────┘                            Detected      Screening      Detected
                             │
                             ▼
                    Raw Sigmoid Output p
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
          p >= 0.50                      p < 0.50
        [ VENOMOUS ]                 [ NON-VENOMOUS ]
   (Confidence = p * 100)        (Confidence = (1-p) * 100)
```

### Detailed AI Model Specifications

#### Model 1: Snake & Venom Classification Pipeline (`SnakeAIPipelineService`)
- **Stage 1 (Snake / Not-Snake Gate Detector):**
  - **Backbone Architecture:** MobileNetV2 pretrained on ImageNet-1k (`tf.keras.applications.MobileNetV2(weights='imagenet')`).
  - **Input Preprocessing:** 224x224 RGB image, normalized to $[-1, 1]$ using `tf.keras.applications.mobilenet_v2.preprocess_input`.
  - **Detection Logic:** Evaluates predicted class probabilities for ImageNet synsets 52 through 68 inclusive (Suborder *Serpentes*, encompassing cobras, vipers, boas, pythons, mambas, garter snakes, etc.).
  - **Gate Threshold:** A snake is confirmed if cumulative $\sum_{i=52}^{68} P_i \ge 0.15$ OR if any of the top 2 overall ImageNet predictions fall within the snake synset range.
  - **Short-Circuit Behavior:** If `is_snake == False`, inference **terminates immediately**. The system returns `status: 'NOT_A_SNAKE'` with a confidence score of $(1.0 - \text{snake\_prob}) \times 100$. The venom classifier is bypassed entirely, preventing invalid classifications on inanimate objects or domestic pets.
- **Stage 2 (Binary Venom Classifier):**
  - **Artifact Path:** `venomwatch_cnn2_final.keras` (located in root directory and `ai/models/`, size: 24,834,082 bytes $\approx 23.68$ MB).
  - **Architecture:** Keras Sequential model: Input layer ($224 \times 224 \times 3$) $\rightarrow$ MobileNetV2 feature extractor backbone $\rightarrow$ GlobalAveragePooling2D $\rightarrow$ Dropout $\rightarrow$ Dense(128, activation='relu') $\rightarrow$ Dropout $\rightarrow$ Dense(1, activation='sigmoid').
  - **Input Preprocessing:** 224x224 RGB image, normalized to $[0, 1]$ by scaling pixel values: `batch_arr / 255.0`.
  - **Prediction Output:** A single scalar sigmoid neuron $p \in [0.0, 1.0]$.
  - **Decision Mapping:**
    - If $p \ge 0.50 \implies \text{VENOMOUS}$, Confidence $= p \times 100\%$, Category: `HIGHLY_VENOMOUS`.
    - If $p < 0.50 \implies \text{NON-VENOMOUS}$, Confidence $= (1.0 - p) \times 100\%$, Category: `NON_VENOMOUS`.
  - **Runtime Caching:** Thread-safe singleton dictionary `MODEL_CACHE` with warmup execution to ensure warm-start inference times of $< 50$ ms.

#### Model 2: Snakebite Wound Screening Service (`SnakebiteScreeningService`)
- **Artifact Path:** `venom_watch_snakebite_efficientnetb0.keras` (located in root directory, size: 37,073,598 bytes $\approx 35.35$ MB).
- **Architecture:** EfficientNetB0 transfer learning architecture adapted for clinical dermatological pattern recognition.
- **Input Preprocessing:** 224x224 RGB image, float32 tensor conversion.
- **Prediction Output:** A single sigmoid neuron $p \in [0.0, 1.0]$.
- **Thresholds & Clinical Safety Band:**
  - $p \ge 0.50 \implies$ `result_label: 'Snake Bite'`, `status_title: 'Possible Snakebite Pattern Detected'`.
  - $p < 0.50 \implies$ `result_label: 'Not Snake Bite'`, `status_title: 'No Snakebite Pattern Detected'`.
  - **Uncertainty Region:** If $0.40 \le p \le 0.60$, the flag `uncertain: True` is raised, overriding the status title to `'Unable to Confidently Classify'` and instructing immediate professional medical triage.
  - **Mandatory Medical Disclaimer:** Enforced on every response payload: *"This is an AI-assisted screening tool and is NOT a medical diagnosis. If a snakebite is suspected, seek emergency medical care immediately."*
- **Stateless Lifecycle:** Evaluated statelessly via `ai/views.py:wound_checker_view()`. Uploaded temporary files are deleted from storage immediately upon completion, and responses include strict `no-cache, no-store` HTTP headers to prevent accidental cross-session data leakage.

#### Disconfirmed / Dormant Artifacts
- `ai/models/best.pt` (3.0 MB): PyTorch YOLO format file. **Completely inactive.** No imports of `ultralytics` or `torch` exist in the web application runtime.
- Multi-class Species Classifiers (15 classes): Stubs exist in legacy code comments, but no 15-class model artifact exists in the repository.

---

## 5. Citizen Reporting and Image-Screening Workflows

The citizen-facing module (`reports/views.py`, `ai/views.py`, `emergency/views.py`) facilitates self-service reporting, rapid automated screening, and personal incident tracking.

### Workflow 1: Snake Sighting Submission and Automated Processing
1. **Initiation:** Authenticated citizen navigates to `/reports/create/`.
2. **Form Input:** Citizen provides report title, upload photo (`original_image`), location description (`location_name`), observer notes, and GPS coordinates (`latitude`, `longitude`). Initial coordinates are auto-populated from browser Geolocation API or user profile defaults.
3. **Model Pipeline Execution:**
   - Server saves initial `SightingReport` record (`status = 'PENDING'`).
   - Invokes `SnakeAIPipelineService.analyze_image(path)`.
   - Stage 1 Gate evaluates snake probability. If negative, marks `snake_detected=False`, `species_predicted='Not a Snake'`.
   - If positive, Stage 2 predicts venom status and confidence percentage, setting `venom_category` to `HIGHLY_VENOMOUS` or `NON_VENOMOUS`.
4. **Duplicate & Spam Evaluation:**
   - Server immediately passes saved report to `DuplicateSpamDetectionService.evaluate_and_flag(report)`.
   - **Spam Check:** If user has submitted $> 3$ reports in the last 5 minutes, `spam_flag = True`, `spam_reason` recorded.
   - **Multi-Signal Duplicate Score ($0 - 100$):** Searches unresolved reports created within 6 hours:
     - Distance $\le 50$ m: $+50$ pts; $\le 200$ m: $+35$ pts; $\le 500$ m: $+20$ pts ($> 500$ m disqualified).
     - Temporal window $\le 30$ mins: $+30$ pts; $\le 2$ hours: $+15$ pts; $\le 6$ hours: $+5$ pts.
     - Species / venom class consistency: $+10$ to $+20$ pts.
     - Same citizen re-submission: $+10$ pts.
   - **Decision:**
     - Score $\ge 75$: Automatically links `duplicate_of` to canonical parent, flags `duplicate_flag=True`.
     - $45 \le \text{Score} < 75$: Flags `duplicate_flag=True` for Authority manual verification without blocking operations.
     - Score $< 45$: Classified as an independent incident.
5. **Output & Notification:** User redirected to `/reports/<id>/` displaying permanent report reference (e.g., `VW-0012`), submission index, AI prediction details, and current lifecycle state.

### Workflow 2: Citizen Snakebite Wound Screening
1. **Initiation:** Citizen opens `/ai/wound-check/`.
2. **Input:** Uploads photo of puncture mark or affected limb (`wound_image`).
3. **Execution:** `ai/views.py:wound_checker_view()` processes image through `SnakebiteScreeningService.analyze_wound_image()`.
4. **Inference & Triage:** EfficientNetB0 evaluates puncture features against decision threshold $0.5$ and uncertainty range $[0.4, 0.6]$.
5. **Output:** Renders immediate visual feedback card with color-coded severity, safety recommendation, direct hotline buttons (`108` Emergency Ambulance, `1926` Forest Rescue), and prominent medical disclaimer. File is purged immediately from server storage.

---

## 6. Authority–Ranger Incident Response Lifecycle

The core operational engine links Wildlife Authority Officers and Forest Rangers in an auditable dispatch-and-response loop.

```
 [ Sighting Submitted ] ──► Status: PENDING, Response: UNASSIGNED
           │
           ▼
 ┌───────────────────────────────────────────────┐
 │ Authority Review & Verification               │
 │ Endpoint: /reports/<id>/verify/               │
 │ Decision: Update Status (VERIFIED / REJECTED) │
 └───────────────────────┬───────────────────────┘
                         │
                         ▼
 ┌───────────────────────────────────────────────┐
 │ Algorithmic Ranger Selection & Dispatch       │
 │ Module: reports/dispatch.py                   │
 │ Filters: ROLE_RANGER, is_active, APPROVED,    │
 │          AVAILABILITY_AVAILABLE, dist <= 30km │
 │ Action: Create RangerAssignment (ASSIGNED)    │
 └───────────────────────┬───────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
 [ Ranger Declines ]             [ Ranger Accepts ]
 Status: DECLINED                Status: ACCEPTED, Ranger: BUSY
 (Authority reassigns)                   │
                                         ▼
                                 [ En Route: ON_THE_WAY ]
                                         │
                                         ▼
                                 [ On Scene: AT_LOCATION ]
                                         │
                                         ▼
                                 [ Outcome Submitted ]
                                 Status: OUTCOME_SUBMITTED
                                 Outcome: CAPTURED / RELOCATED
                                 Evidence photo uploaded
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               [ Authority Rejects ]           [ Authority Approves ]
               Decision: REJECTED              Decision: APPROVED
               Status: AT_LOCATION             Status: COMPLETED
               (Ranger re-intervenes)          Incident: RESOLVED / CLOSED
                                               Ranger: AVAILABLE
                                               AuditLog & Notifications sent
```

### Response Lifecycle State Transitions

#### 1. Authority Review & Verification
- **Route:** `POST /reports/<pk>/verify/` (Guarded by `@authority_required`).
- Authority inspects sighting image, AI prediction, coordinates, duplicate likelihood score, and submitter notes.
- Status updated to `VERIFIED` or `REJECTED`. Creates entry in `AuditLog`.

#### 2. Ranger Selection & Dispatch
- **Route:** `POST /reports/<pk>/assign/` (Guarded by `@authority_required`).
- Server executes `reports/dispatch.py:get_candidate_rangers()`:
  - Account must have `profile.role == 'ranger'`, `profile.account_status == 'ACTIVE'`, `is_active == True`.
  - Registration `AccountApplication` must be `APPROVED`.
  - Must have `availability == 'AVAILABLE'` (no conflicting active assignments in `RangerAssignment.ACTIVE_STATUSES`).
  - Spatial Relevance: Haversine distance between ranger base (`latitude`, `longitude`) and sighting coordinates must be $\le 30.0$ km, or registered operational base must match sighting locality.
- Creates formal `RangerAssignment` record (`status = 'ASSIGNED'`).
- Sends `Notification` to ranger; marks `report.response_status = 'ASSIGNED'`.

#### 3. Ranger Field Operations
- **Console:** `/ranger/assignments/<id>/` (Guarded by `@ranger_required` and object ownership check: `ranger = request.user`).
- Ranger receives incoming assignment, marks as read, reviews GPS coordinates, victim contact, and notes.
- Permitted linear status transitions (`RangerAssignment.ALLOWED_TRANSITIONS`):
  - `ASSIGNED` $\rightarrow$ `ACCEPTED` (Availability becomes `BUSY`) or `DECLINED` (Returns incident to unassigned pool).
  - `ACCEPTED` $\rightarrow$ `ON_THE_WAY` (En route).
  - `ON_THE_WAY` $\rightarrow$ `AT_LOCATION` (Arrived on scene).
  - `AT_LOCATION` $\rightarrow$ `OUTCOME_SUBMITTED` (Field intervention complete).
- Submitting outcome requires selecting an outcome type (`SNAKE_CAPTURED`, `SNAKE_RELOCATED`, `SNAKE_ESCAPED`, `UNRESOLVED`, `OTHER`), entering detailed field notes, and optionally uploading an outcome evidence photograph.
- **Critical Enforcement:** The Ranger **cannot** set the assignment status to `COMPLETED`. The outcome remains pending verification.

#### 4. Authority Outcome Review & Incident Closure
- **Route:** `POST /reports/assignments/<pk>/review/` (Guarded by `@authority_required`).
- Authority Officer reviews submitted field notes and outcome photograph:
  - **`APPROVED`:** Sets assignment status to `COMPLETED`, records `reviewed_by` and `completed_at`. Recomputes ranger availability to `AVAILABLE`. Sets `SightingReport.status = 'RESOLVED'`, `response_status = 'RESOLVED'`. Generates success notifications to both Citizen reporter and Ranger responder. Logs `AuditLog` action `'VERIFY_OUTCOME'`.
  - **`REJECTED`:** Requires mandatory explanation notes. Reverts assignment status to `AT_LOCATION` so the ranger can perform follow-up intervention or rectify reporting.
  - **`CLARIFICATION_REQUESTED`:** Keeps status at `OUTCOME_SUBMITTED` while notifying ranger of questions.

---

## 7. GIS, DBSCAN and Hotspot Analysis

VenomWatch incorporates two separate geospatial engines: an **Operational GIS Leaflet Mapping Engine** for tactical incident response and a **Dynamic DBSCAN Geospatial Clustering Engine** for public risk zone awareness and authority surveillance.

### 1. Mapping Framework & Tile Layer
- **Client Library:** Leaflet.js (v1.9+).
- **Tile Providers:** CartoDB Positron (`https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`) for clean, high-contrast operational rendering, with OpenStreetMap fallback.
- **Coordinate Precision:** WGS84 decimal degrees (`latitude`, `longitude`).

### 2. Operational Authority Map (`/reports/map/`)
- **Access Control:** Restricted strictly to Authority and Platform Administrators (`@authority_required`).
- **Data Endpoint:** `GET /reports/api/map-reports/` (dynamically loads real database records with valid coordinates).
- **Marker Color-Coding:**
  - Red Marker: Unassigned venomous snake sighting (Priority 1 dispatch target).
  - Amber / Orange Marker: Non-venomous unassigned sighting.
  - Blue Marker: Active ranger intervention underway (`ACCEPTED`, `ON_THE_WAY`, `AT_LOCATION`, `OUTCOME_SUBMITTED`).
  - Green / Muted Marker: Resolved and closed incident.
- **Interactive Dispatch Drawer:** Clicking any marker triggers `GET /reports/api/report-panel/<id>/`, loading incident photos, AI telemetry, duplicate probability, and an inline candidate ranger dropdown sorted by ascending Haversine distance.

### 3. DBSCAN Hotspot Clustering (`hotspots/services.py`)
Clustering is **dynamically executed at runtime** and is **never persisted in database tables**. The service exposes two complementary spatial methods:

#### A. Public Community Risk Zones (`compute_community_risk_zones()`)
- **Target Audience:** Public citizens (`/reports/risk-zones/`).
- **Privacy Preservation:** Exact coordinates and reporter personal identities are obscured. Reports within a cluster are aggregated into a circular geographic sector defined by centroid $(\bar{\phi}, \bar{\lambda})$ and radius $R = \max(500\text{ m}, \text{max\_dist} + 250\text{ m})$.
- **Clustering Algorithm:**
  ```python
  coords_rad = np.radians([[r.latitude, r.longitude] for r in valid_incidents])
  kms_per_radian = 6371.0
  epsilon = 1.5 / kms_per_radian  # 1.5 km neighborhood
  db = DBSCAN(eps=epsilon, min_samples=1, metric='haversine', algorithm='ball_tree')
  ```
- **Four-State Incident Lifecycle:**
  - **RED (High Risk):** $\ge 3$ distinct active snake incidents within the zone.
  - **ORANGE (Caution):** 1–2 distinct active snake incidents.
  - **YELLOW (Recently Resolved):** Incidents verified resolved within a 24-hour cooldown period (`RESOLVED_COOLDOWN_HOURS = 24`).
  - **GREEN (No Recent Active Incidents):** Cleared incidents retained for 48 hours post-cooldown (`GREEN_RETENTION_HOURS = 48`) before the zone safely expires.
- **Duplicate Exclusion:** Multiple citizen reports linked via `duplicate_of` are collapsed and count as **one single distinct incident**, preventing duplicate reporting from falsely inflating risk levels.

#### B. Authority Surveillance Radar (`compute_hotspots()`)
- **Target Audience:** Authority Officers (`/hotspots/view/`).
- **Parameters:** Evaluates reports submitted within the last 48 hours (`hours=48`), neighborhood radius $\epsilon = 1.0\text{ km}$, minimum core samples `min_samples = 2`.
- **Classification:** Groups density clusters into `HIGH_ALERT` (clusters containing verified venomous sightings) and `GREEN_ZONE` (clusters with non-venomous sightings only). Outlier points ($label = -1$) are analyzed individually to flag isolated venomous threats as `MEDIUM_ALERT`.

---

## 8. Administrator, Hospital, Anti-Venom and SOS Functionality

The administration and emergency systems provide platform governance, verified credential management, and lifesaving medical logistics.

### 1. Platform Administration & Role Governance (`accounts/views.py`)
- **Role Provisioning & Review Queue:** Admin monitors pending `AccountApplication` submissions submitted by prospective Authority Officers and Forest Rangers.
- **Document Verification:** Supporting departmental credentials uploaded during registration are stored under `media/verification_docs/`. Direct HTTP access is blocked by `protected_media_block_view()`. Administrators inspect documents via `admin_application_document_view()` which enforces session checks before streaming files.
- **Application Decision:**
  - **Approve:** Atomic transaction activates user account (`is_active = True`), configures operational base coordinates, updates role in `UserProfile`, creates `AuditLog` entry, and dispatches notification.
  - **Reject:** Sets status to `REJECTED`, records mandatory rejection rationale, and notifies applicant.
- **Account Security Controls:** Admin can toggle operational status: `SUSPENDED` or `BANNED`. Security policies explicitly forbid suspending or deleting the last active platform administrator. Admin edits of operational fields (GPS coordinates, availability) are strictly blocked to protect responder autonomy.

### 2. Hospital & Anti-Venom Directory (`emergency/models.py`, `emergency/views.py`)
- **Model Entities:** `Hospital` tracks facility name, contact phone, 24/7 operating hours, emergency department presence, ICU/ventilator capacity, anti-venom vial inventory count (`anti_venom_stock_vials`), anti-venom notes, and GPS coordinates.
- **Geodesic Distance Sorting:** When a citizen accesses `/emergency/`, the view calculates spherical distance in kilometers using the Haversine formula from citizen GPS coordinates:
  $$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)$$
  Hospitals are rendered dynamically, sorted nearest first, with visual indicators for anti-venom availability and ICU readiness.
- **Administrative Maintenance:** Platform Administrators maintain the hospital database via `/emergency/manage/` with full Create, Read, Update, and Delete (CRUD) operations.

### 3. Emergency SOS Distress System (`EmergencySOSEvent`)
- **Broadcast Trigger:** Citizen presses "Activate Emergency SOS" on the mobile interface, sending a POST request to `/emergency/api/sos/` containing device coordinates and contact number.
- **Throttling & Deduplication:** Prevents duplicate alarms by checking if an active SOS event already exists within a 0.001-degree bounding box ($\approx 110$ m) created within the last 2 minutes.
- **Operational Response:** Persists an `EmergencySOSEvent` record (`status = 'ACTIVE'`). Authority Officers monitor real-time distress events via `/emergency/api/sos/feed/` and acknowledge or resolve events via `/emergency/api/sos/<id>/ack/`.

---

## 9. Major Data Entities and Their Relationships

The data layer is built on Django's Object-Relational Mapping (ORM) backed by SQLite3. The following conceptual schema represents the genuine, verified database models and relational constraints:

```
                      ┌────────────────────────┐
                      │    auth.models.User    │
                      └───────────┬────────────┘
                                  │ 1:1
                                  ▼
                      ┌────────────────────────┐
                      │  accounts.UserProfile  │
                      │  role, status, coords  │
                      └───────────┬────────────┘
                                  │ 1:1
                                  ▼
                      ┌────────────────────────┐
                      │   AccountApplication   │
                      │  status, ID document   │
                      └────────────────────────┘

     User (Citizen)                       User (Authority)         User (Ranger)
           │ 1:N                                │ 1:N                    │ 1:N
           ▼                                    ▼                        ▼
┌──────────────────────┐              ┌────────────────────┐    ┌────────────────────┐
│    SightingReport    │ 1:N          │      AuditLog      │    │  RangerAssignment  │
│ coords, AI telemetry,├─────────────►│ actor, action,     │◄───┤ status, milestones,│
│ duplicate & spam info│              │ target, timestamp  │    │ outcome, evidence  │
└──────────┬───────────┘              └────────────────────┘    └────────────────────┘
           │
           │ Self-referential (1:N)
           ▼
 [ duplicate_of ForeignKey ]
 (Links redundant reports to root incident)

   User (Citizen / Any)                User (Admin / Authority)
           │ 1:N                                │ 1:N
           ▼                                    ▼
┌──────────────────────┐              ┌────────────────────┐
│  EmergencySOSEvent   │              │      Hospital      │
│ coords, phone, status│              │ vials, ICU, coords │
└──────────────────────┘              └────────────────────┘
```

### Entity Attribute Details
1. **`UserProfile` (`accounts/models.py`):**
   - Extends standard Django `User`.
   - Fields: `role` (`citizen`, `authority`, `ranger`, `admin`), `account_status` (`ACTIVE`, `SUSPENDED`, `BANNED`), `availability` (`AVAILABLE`, `BUSY`, `OFFLINE`), `registered_location`, `latitude`, `longitude`, `phone_number`, `organization`, `assigned_region`.
2. **`AccountApplication` (`accounts/models.py`):**
   - Fields: `user` (OneToOne), `requested_role`, `supporting_document` (FileField), `status` (`PENDING`, `APPROVED`, `REJECTED`, `NEEDS_INFO`), `rejection_reason`, `reviewed_by` (FK User), `submitted_at`, `reviewed_at`.
3. **`SightingReport` (`reports/models.py`):**
   - Fields: `user` (FK User, nullable), `original_image`, `processed_image`, `latitude`, `longitude`, `location_name`, `status` (`PENDING`, `VERIFIED`, `REJECTED`, `RESOLVED`), `response_status` (`UNASSIGNED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`), `assigned_responder` (FK User, nullable), `verified_by` (FK User, nullable).
   - AI Metadata: `snake_detected` (bool), `snake_confidence` (float), `venomous` (bool), `venom_confidence` (float), `species_predicted` (str), `venom_category` (`HIGHLY_VENOMOUS`, `VENOMOUS`, `NON_VENOMOUS`).
   - Duplicate & Spam: `duplicate_flag` (bool), `duplicate_of` (FK Self, nullable), `duplicate_score` (int $0-100$), `duplicate_reason` (str), `spam_flag` (bool), `spam_reason` (str).
4. **`RangerAssignment` (`reports/models.py`):**
   - Fields: `sighting` (FK SightingReport), `ranger` (FK User), `assigned_by` (FK User), `assigned_at`, `responded_at`, `outcome_submitted_at`, `completed_at`, `status` (`ASSIGNED`, `ACCEPTED`, `ON_THE_WAY`, `AT_LOCATION`, `OUTCOME_SUBMITTED`, `COMPLETED`, `DECLINED`, `CANCELLED`), `distance_km` (float), `outcome` (`SNAKE_CAPTURED`, `SNAKE_RELOCATED`, `SNAKE_ESCAPED`, `UNRESOLVED`, `OTHER`), `notes` (TextField), `outcome_image` (ImageField), `is_read` (bool).
   - Authority Verification: `reviewed_by` (FK User), `reviewed_at`, `review_decision` (`APPROVED`, `REJECTED`, `CLARIFICATION_REQUESTED`), `review_notes` (TextField).
5. **`Hospital` (`emergency/models.py`):**
   - Fields: `name`, `phone_number`, `address`, `latitude`, `longitude`, `anti_venom_available` (bool), `anti_venom_stock_vials` (int), `has_icu` (bool), `emergency_department` (bool), `anti_venom_notes`, `district`.
6. **`EmergencySOSEvent` (`emergency/models.py`):**
   - Fields: `user` (FK User, nullable), `phone_number`, `latitude`, `longitude`, `location_name`, `status` (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`), `acknowledged_by` (FK User), `created_at`.
7. **`Notification` & `AuditLog` (`accounts/models.py`):**
   - System-wide in-app notification queue and immutable security event ledger.

---

## 10. Source-Code Evidence Table

| Component / Subsystem | Primary Source File | Key Class, Function, or Model | Concrete Code Observation |
| :--- | :--- | :--- | :--- |
| **Project Settings** | `venomwatch/settings.py` | `INSTALLED_APPS` | Configures `accounts`, `reports`, `ai`, `hotspots`, `dashboard`, `emergency`, `ranger`, `rest_framework`. |
| **URL Root & Gate** | `venomwatch/urls.py` | `protected_media_block_view` | Explicit route intercepts `/media/verification_docs/<path>` and denies direct HTTP access. |
| **User Profile & RBAC** | `accounts/models.py` | `UserProfile` | Defines 4 roles (`citizen`, `ranger`, `authority`, `admin`) and account status choices (`ACTIVE`, `SUSPENDED`, `BANNED`). |
| **Role Decorators** | `accounts/decorators.py` | `@authority_required`, `@ranger_required`, `@admin_required` | Inspects authenticated user's `profile.effective_role` and raises `PermissionDenied` on violation. |
| **Official Applications** | `accounts/models.py` | `AccountApplication` | Requires supporting document upload; status choices `PENDING`, `APPROVED`, `REJECTED`, `NEEDS_INFO`. |
| **Application Review** | `accounts/views.py` | `admin_provision_account_view` | Atomic transaction updates application, activates user, configures coordinates, and writes `AuditLog`. |
| **Secure Doc Serving** | `accounts/views.py` | `admin_application_document_view` | Verifies admin privileges before reading `supporting_document` stream; blocks unauthorized users. |
| **Sighting Reports** | `reports/models.py` | `SightingReport` | Stores original/processed images, coordinates, AI predictions, duplicate flags, and responder links. |
| **Ranger Assignments** | `reports/models.py` | `RangerAssignment` | Enforces `ALLOWED_TRANSITIONS`; rangers cannot set `STATUS_COMPLETED`; requires Authority review. |
| **Ranger Dispatch Engine** | `reports/dispatch.py` | `get_candidate_rangers`, `haversine_km` | Filters eligible, approved, available rangers within 30 km radius via Haversine great-circle calculation. |
| **Duplicate Detection** | `reports/services.py` | `DuplicateSpamDetectionService` | Multi-signal score ($0-100$) based on distance ($\le 500$ m), time ($\le 6$ h), and species/venom consistency. |
| **Sighting Submission** | `reports/views.py` | `create_report_view` | Coordinates image save, invokes `SnakeAIPipelineService`, executes duplicate check, and redirects. |
| **Authority Map API** | `reports/views.py` | `authority_map_reports_api` | Returns JSON marker data with status colors and dispatch states; excludes fake or hard-coded coordinates. |
| **Outcome Verification** | `reports/views.py` | `review_assignment_outcome_view` | Handles `APPROVED` (closes incident, frees ranger), `REJECTED`, and `CLARIFICATION_REQUESTED`. |
| **Ranger Console** | `ranger/views.py` | `assignment_detail_view`, `assignment_update_view` | Enforces object-level security (`ranger=request.user`) and controls linear milestone updates. |
| **Snake AI Pipeline** | `ai/services.py` | `SnakeAIPipelineService` | Stage 1 ImageNet MobileNetV2 gate + Stage 2 `venomwatch_cnn2_final.keras` binary classifier ($p \ge 0.5$). |
| **Wound Screening** | `ai/services.py` | `SnakebiteScreeningService` | Deploys `venom_watch_snakebite_efficientnetb0.keras` with decision threshold $0.5$ and uncertainty range $[0.4, 0.6]$. |
| **Wound Checker View** | `ai/views.py` | `wound_checker_view` | Stateless upload processing with immediate file deletion and strict `Cache-Control: no-store` headers. |
| **DBSCAN Clustering** | `hotspots/services.py` | `DBSCANHotspotService` | Executes `sklearn.cluster.DBSCAN(eps=..., min_samples=..., metric='haversine', algorithm='ball_tree')`. |
| **Risk Zones View** | `reports/views.py` | `risk_zones_public_view` | Renders 4-state lifecycle (Red, Orange, Yellow, Green) community sectors without exposing private GPS points. |
| **Hospital Registry** | `emergency/models.py` | `Hospital` | Manages stock vials, ICU status, and executes Haversine `distance_from()` to sort nearest facilities. |
| **Emergency SOS API** | `emergency/views.py` | `sos_trigger_api`, `sos_acknowledge_api` | Rate-limits distress alarms to 1 per 2 minutes, logs `EmergencySOSEvent`, and broadcasts to Authority feed. |

---

## 11. Implemented, Partially Implemented, Unverified and Planned Features

### Fully Implemented and Verified in Source Code
1. Four-tier user role hierarchy (`citizen`, `authority`, `ranger`, `admin`) with server-side decorator enforcement.
2. Official registration application queue with private supporting document verification.
3. Protected media route blocking unauthenticated/public HTTP access to verification files.
4. Administrative account suspension, ban, reinstatement, and immutable audit logging.
5. Citizen snake sighting submission with GPS coordinate capture and metadata storage.
6. Two-stage snake AI pipeline: MobileNetV2 ImageNet gate detector + `venomwatch_cnn2_final.keras` binary venom classifier.
7. Automated multi-signal duplicate detection scoring ($0-100$) and rate-limiting spam detection.
8. Location-based candidate ranger dispatch engine with Haversine distance ranking ($\le 30$ km).
9. Dedicated, isolated Ranger mobile console with strict object-level security.
10. Multi-stage Ranger response milestone progression (`ASSIGNED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `ON_THE_WAY` $\rightarrow$ `AT_LOCATION` $\rightarrow$ `OUTCOME_SUBMITTED`).
11. Ranger field evidence photo upload and outcome reporting.
12. Authority outcome review workflow (`APPROVED`, `REJECTED`, `CLARIFICATION_REQUESTED`) with automated incident resolution.
13. Interactive Authority GIS Operations Map with color-coded status markers and dynamic assignment drawer.
14. Scikit-learn DBSCAN dynamic spatial density clustering with Haversine metric and BallTree algorithm.
15. Privacy-preserving Public Community Risk Zones map with 4-state lifecycle (Red, Orange, Yellow, Green).
16. AI-assisted snakebite wound screening using `venom_watch_snakebite_efficientnetb0.keras` with uncertainty handling and medical disclaimers.
17. Emergency SOS distress broadcast API with geographic deduplication throttling.
18. Anti-venom hospital registry with live Haversine distance calculation and Admin CRUD management.

### Partially Implemented / Architectural Compromises
1. **AI Output Terminology:** `SightingReport.species_predicted` stores `'Venomous Snake'` or `'Non-Venomous Snake'` rather than a granular species name, because the deployed model is a binary venom classifier rather than a species taxonomy classifier.
2. **Citizen Sighting Sequence Display:** `citizen_submission_number` is computed dynamically via a property query (`id__lte=self.id`) rather than stored in a dedicated database column.

### Unverified / Inactive Artifacts Present in Directory
1. **YOLO Model Artifact (`ai/models/best.pt`):** A 3.0 MB PyTorch weight file exists on disk, but has no imports, bindings, or references in any active Django view or service.
2. **15-Class Species Classifier Stubs:** `SNAKE_SPECIES_DATABASE` and legacy class index constants exist as empty dictionaries in `ai/services.py` for backward compatibility, but are unused.

### Planned / Not Implemented in Repository
1. SMS / WhatsApp gateway dispatch to offline field rangers (currently relies on in-app `Notification` models and browser polling).
2. Hardware edge deployment on drones or trail cameras (current architecture operates as a centralized web platform).

---

## 12. Recommended Components and Flows for the Final Architecture Diagram

To create the final black-and-white academic architecture diagram for the MCA project report, structure the layout into clear, numbered functional tiers:

1. **User Role Panels (Top & Bottom Boundaries):**
   - **Citizen:** Web/Mobile UI $\rightarrow$ Submit Sighting, Wound Screening, Emergency SOS, Hospital Lookup, Community Risk Zones.
   - **Authority Officer:** Surveillance Dashboard $\rightarrow$ Verify Sighting, GIS Incident Map, Dispatch Ranger, Verify Field Outcome, SOS Monitor.
   - **Forest Ranger:** Isolated Ranger Console $\rightarrow$ Accept/Decline, En Route Milestones, Submit Field Outcome & Photo Evidence.
   - **Platform Administrator:** Admin Hub $\rightarrow$ Application Document Verification, Account Governance, Hospital & Anti-Venom Registry.
2. **Central Application Core (Django Web Framework):**
   - HTTP Request Router (`urls.py`) & RBAC Security Middleware (`decorators.py`).
   - Major Functional Controllers:
     - `reports/views.py`: Sighting Manager & Dispatch Hub.
     - `ai/services.py`: Two-Stage Deep Learning Pipeline.
     - `hotspots/services.py`: DBSCAN Geospatial Clustering Engine.
     - `ranger/views.py`: Field Responder State Machine.
     - `emergency/views.py`: SOS Distress & Geodesic Hospital Matcher.
     - `accounts/views.py`: Application Queue & Audit Logger.
3. **Deep Learning Inference Subsystem:**
   - Clearly delineate **Pipeline 1** (MobileNetV2 Gate $\rightarrow$ `venomwatch_cnn2_final.keras` Binary Venom Classifier) from **Pipeline 2** (`venom_watch_snakebite_efficientnetb0.keras` Wound Screening).
   - Show the Gate Check decision diamond: "Snake Confirmed? (Yes $\rightarrow$ Model 2, No $\rightarrow$ Terminate & Return 'Not a Snake')".
4. **Data & Storage Layer:**
   - Relational Database (SQLite3): `UserProfile`, `AccountApplication`, `SightingReport`, `RangerAssignment`, `Hospital`, `EmergencySOSEvent`, `AuditLog`.
   - Media Storage: `sightings/`, `assignment_outcomes/`, and strictly protected `verification_docs/`.

---

## 13. Outstanding Questions That Cannot Be Resolved from the Repository

1. **Original Dataset Details for Model Training:** The repository contains the final serialized `.keras` models, but the original raw image training sets (e.g., number of training/validation splits, data augmentation strategies, loss curves) are not stored in the repository.
2. **Origin of `ai/models/best.pt`:** It cannot be determined from git commit history whether `best.pt` was an early experimental YOLOv8 test or a third-party baseline that was superseded by the MobileNetV2 pipeline.
3. **Production Deployment Target:** The repository is configured with `DEBUG = True` and SQLite3; production WSGI configurations (e.g., Nginx, Gunicorn, PostgreSQL, Redis) are not committed to source control.

---

## 14. Diagram Preparation Requirements (Monochrome Academic Infographic Specification)

This specification provides the structural layout, node designations, and directed data arrows required to generate the final **clean, high-contrast, black-and-white academic architecture and workflow diagram** for the MCA project presentation.

### Visual Styling Rules
- **Color Palette:** Strictly monochrome (White `#FFFFFF` background, solid Black `#000000` borders and text, light grey `#F4F4F4` node shading where required for container grouping).
- **Line Style:** 1.5px solid black connecting arrows with filled black arrowheads. Conditional decision branches use 1.5px dashed black lines.
- **Typography:** Clean sans-serif (Helvetica / Arial / Inter), bold structural headers, numbered process sequences.

### Layout Architecture & Workflow Block Specification

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                             VENOMWATCH SYSTEM ARCHITECTURE                                            │
├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                       │
│  [ PANEL 1: CITIZEN ACTOR ]                         [ PANEL 2: PLATFORM ADMINISTRATOR ACTOR ]                         │
│  ┌──────────────────────────────────────────────┐   ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1.1 Sighting Submission (Image + GPS)        │   │ 2.1 Official Role Application Review (Ranger / Authority)    │  │
│  │ 1.2 Wound Photo Screening Upload             │   │ 2.2 Secure Verification Document Inspection (PDF/ID)         │  │
│  │ 1.3 View Personal Report History (VW-XXXX)   │   │ 2.3 Account Governance (Activate / Suspend / Ban)            │  │
│  │ 1.4 Emergency SOS Distress Trigger           │   │ 2.4 Anti-Venom & Hospital Registry Management (CRUD)         │  │
│  │ 1.5 Hospital Geodesic Directory Lookup       │   └──────────────────────────────┬───────────────────────────────┘  │
│  │ 1.6 View Community Risk Zones (Public GIS)   │                                  │                                  │
│  └──────────────────────┬───────────────────────┘                                  │                                  │
│                         │                                                          │                                  │
├─────────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────┤
│                         ▼                                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                  DJANGO CORE APPLICATION FRAMEWORK & SECURITY                                   │  │
│  │  - URL Routing & Session Authentication          - Role-Based Access Control (@authority_required, etc.)        │  │
│  │  - Protected Media File Gate (/media/docs/)      - Immutable Administrative Audit Trail (AuditLog)              │  │
│  └──────────────────────┬──────────────────────────────────────────────────────────┬───────────────────────────────┘  │
│                         │                                                          │                                  │
├─────────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────┤
│                         │                                                          │                                  │
│  [ SUBSYSTEM A: DEEP LEARNING INFERENCE ]           [ SUBSYSTEM B: GEOSPATIAL & INCIDENT DISPATCH ]                   │
│                                                                                                                       │
│  PIPELINE 1: Snake & Venom Classification           3.1 Automated Multi-Signal Duplicate & Spam Engine                │
│  ┌────────────────────────────────────────┐         - Evaluates distance (<=500m), time (<=6h), venom consistency     │
│  │ Stage 1: MobileNetV2 (ImageNet) Gate   │         - Calculates Duplicate Score (0-100) & auto-links duplicate_of   │
│  │ Checks Synsets 52-68 (Serpentes)       │                                                                           │
│  └───────────────────┬────────────────────┘         3.2 Location-Based Ranger Dispatch Engine (dispatch.py)           │
│                      │                              - Filters: Approved, Available, Active Ranger Accounts            │
│         Snake Confirmed? (Prob >= 0.15)             - Calculates Haversine Distance (Radius <= 30.0 km)               │
│          ├── NO ──► Return "NOT_A_SNAKE"                                                                              │
│          └── YES                                    3.3 Dynamic Geospatial Clustering Engine (hotspots/services.py)   │
│                      │                              - Algorithm: Scikit-Learn DBSCAN (metric='haversine', ball_tree)  │
│                      ▼                              - Public Risk Zones: 4-State Lifecycle (Red, Orange, Yellow, Green)│
│  ┌────────────────────────────────────────┐         - Authority Surveillance: Density Hotspots (eps=1.0km, min_samp=2)│
│  │ Stage 2: venomwatch_cnn2_final.keras   │                                                                           │
│  │ MobileNetV2 Backbone + Sigmoid Output  │         3.4 Emergency SOS & Geodesic Hospital Directory Engine            │
│  │ p >= 0.50: VENOMOUS                    │         - Real-time SOS dispatch feed & 2-minute deduplication throttling │
│  │ p <  0.50: NON-VENOMOUS                │         - Haversine distance-sorted facility directory with ICU/vials     │
│  └────────────────────────────────────────┘                                                                           │
│                                                                                                                       │
│  PIPELINE 2: Snakebite Wound Screening                                                                                │
│  ┌────────────────────────────────────────┐                                                                           │
│  │ venom_watch_snakebite_                 │                                                                           │
│  │   efficientnetb0.keras                 │                                                                           │
│  │ Sigmoid Output + Uncertainty [0.4-0.6] │                                                                           │
│  │ Non-diagnostic Medical Disclaimers     │                                                                           │
│  └────────────────────────────────────────┘                                                                           │
│                         │                                                          │                                  │
├─────────────────────────┼──────────────────────────────────────────────────────────┼──────────────────────────────────┤
│                         │                                                          │                                  │
│                         ▼                                                          ▼                                  │
│  [ PANEL 3: WILDLIFE AUTHORITY OFFICER ACTOR ]      [ PANEL 4: FOREST RANGER FIELD RESPONDER ACTOR ]                  │
│  ┌──────────────────────────────────────────────┐   ┌──────────────────────────────────────────────────────────────┐  │
│  │ 4.1 Incident Verification & Triage Console   │   │ 5.1 Isolated Mobile Ranger Console (/ranger/)                │  │
│  │ 4.2 Tactical GIS Map & Candidate Dispatch    │──►│ 5.2 Review Assigned Incident (Distance, Coordinates, Notes)  │  │
│  │ 4.3 Cancel / Reassign Responders             │   │ 5.3 Accept / Decline Assignment                              │  │
│  │ 4.4 Review Ranger Field Notes & Evidence     │◄──│ 5.4 Update Status: ON_THE_WAY -> AT_LOCATION                 │  │
│  │ 4.5 Formal Outcome Approval & Incident Close │   │ 5.5 Submit Outcome (CAPTURED/RELOCATED) & Evidence Photo     │  │
│  │ 4.6 Emergency SOS Real-Time Monitoring Feed  │   │     (Strictly prohibited from self-verifying completion)     │  │
│  └──────────────────────────────────────────────┘   └──────────────────────────────────────────────────────────────┘  │
│                                                                                                                       │
├───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                          PERSISTENT RELATIONAL DATA LAYER                                             │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐              │
│  │  accounts_userprofile │ │ reports_sightingreport│ │reports_rangerassignment││  emergency_hospital   │              │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────────┘ └───────────────────────┘              │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐              │
│  │  account_application  │ │  emergency_sosevent   │ │ accounts_auditlog     │ │ accounts_notification │              │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────────┘ └───────────────────────┘              │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Directed Process Arrows and Numbered Data Sequences

1. **Reporting & Screening Sequence:**
   - $(1) \text{ Citizen } \xrightarrow{\text{Upload Photo \& GPS}} \text{Django View } (\texttt{create\_report\_view})$.
   - $(2) \text{ Django View } \xrightarrow{\text{RGB 224x224}} \text{Stage 1 Gate (MobileNetV2 ImageNet)}$.
   - $(3) \text{ If Snake Confirmed } \xrightarrow{\text{Normalized Tensor}} \text{Stage 2 Model } (\texttt{venomwatch\_cnn2\_final.keras})$.
   - $(4) \text{ Prediction \& Metadata } \xrightarrow{\text{Evaluate Multi-Signal}} \text{Duplicate Engine } (\texttt{DuplicateSpamDetectionService})$.
   - $(5) \text{ Sighting Persisted } \xrightarrow{\text{Database Save}} \text{Table } (\texttt{reports\_sightingreport})$.
2. **Authority Dispatch & Field Intervention Sequence:**
   - $(6) \text{ Authority } \xrightarrow{\text{Open Operations Map}} \text{API } (\texttt{authority\_map\_reports\_api})$.
   - $(7) \text{ Incident Marker Clicked } \xrightarrow{\text{Haversine Filter (<=30km)}} \text{Dispatch Helper } (\texttt{get\_candidate\_rangers})$.
   - $(8) \text{ Authority Assigns Ranger } \xrightarrow{\text{Create Record}} \text{Table } (\texttt{reports\_rangerassignment}, \text{status: ASSIGNED})$.
   - $(9) \text{ Notification Sent } \xrightarrow{\text{In-App Alert}} \text{Ranger Mobile Dashboard}$.
   - $(10) \text{ Ranger Accepts } \xrightarrow{\text{Linear State Progression}} \texttt{ACCEPTED} \rightarrow \texttt{ON\_THE\_WAY} \rightarrow \texttt{AT\_LOCATION}$.
   - $(11) \text{ Field Outcome Recorded } \xrightarrow{\text{Upload Evidence Photo}} \text{State: } \texttt{OUTCOME\_SUBMITTED}$.
3. **Authority Verification & Closure Sequence:**
   - $(12) \text{ Authority Reviews Evidence } \xrightarrow{\text{Review Decision}} \texttt{review\_assignment\_outcome\_view}$.
   - $(13a) \text{ If Approved } \implies \text{Assignment: } \texttt{COMPLETED}, \text{Report: } \texttt{RESOLVED}, \text{Ranger: } \texttt{AVAILABLE}, \text{Citizen Notified}$.
   - $(13b) \text{ If Rejected } \implies \text{Assignment reverted to } \texttt{AT\_LOCATION} \text{ with mandatory reviewer notes}$.
4. **Geospatial Surveillance & Public Risk Sequence:**
   - $(14) \text{ Verified Active Sighting Coordinates } \xrightarrow{\text{Dynamic Execution}} \text{DBSCAN Engine } (\texttt{DBSCANHotspotService})$.
   - $(15) \text{ Clusters Grouped } \xrightarrow{\text{Centroid \& Radius}} \text{Public Risk Zones Map } (\text{Red, Orange, Yellow, Green})$.
5. **Emergency Logistics Sequence:**
   - $(16) \text{ Distress Button Pressed } \xrightarrow{\text{POST GPS \& Phone}} \text{API } (\texttt{sos\_trigger\_api})$.
   - $(17) \text{ Duplicate Throttle Checked } \implies \text{Save } \texttt{EmergencySOSEvent} \rightarrow \text{Broadcast to Authority Feed}$.
   - $(18) \text{ Citizen Requests Hospital } \xrightarrow{\text{Haversine Geodesic Sort}} \text{Directory rendered nearest-first with vial counts}$.
