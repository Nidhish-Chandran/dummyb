# Project Audit Summary — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Academic Context:** Master of Computer Applications (MCA), Department of Computer Applications, TKM College of Engineering, Kollam  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  
**Repository Working Tree:** `https://github.com/Nidhish-Chandran/dummyb` (Branch: `master`)  
**Audit Nature:** Rigorous Source-Code Inspection & Execution Evidence Verification (Read-Only)  

---

## 1. Verified Architecture

VenomWatch is implemented as a multi-tier, modular web application built on the Django web framework. The system coordinates environmental intelligence, citizen science, deep learning inference, geospatial surveillance, and rapid incident response across four authenticated user roles.

### Architectural Tiers:
1. **Client Tier:**
   - Responsive HTML5/CSS3/JavaScript web interface.
   - GIS Mapping: Leaflet.js (v1.9+) utilizing CartoDB Positron and Esri World Street Map tile providers with OpenStreetMap fallbacks.
   - HTML5 Geolocation API for coordinate capture, supplemented by manual pin placement.
2. **Application Tier (Django Framework):**
   - **URL Routing & Middleware:** Centralized dispatcher in `venomwatch/urls.py` enforcing session authentication, CSRF validation, cache prevention (`@never_cache`), and protected media gateways.
   - **Role-Based Access Control (RBAC):** Decorators (`@authority_required`, `@ranger_required`, `@admin_required`) enforcing authorization boundaries at the view level.
   - **Core Application Modules:**
     - `accounts`: User profiles, role hierarchy, official application review, document inspection, notifications, audit logging.
     - `reports`: Citizen sighting submissions, duplicate scoring, location-based ranger dispatch, outcome review.
     - `ai`: Two-stage snake/venom inference pipeline and snakebite wound screening.
     - `hotspots`: Scikit-learn DBSCAN spatial density clustering and community risk zones.
     - `ranger`: Mobile-first field responder console with object-level security.
     - `emergency`: Anti-venom hospital registry, geodesic distance sorting, Emergency SOS distress broadcast.
     - `dashboard`: Surveillance metric aggregation and role-based landing redirection.
3. **Machine Learning Inference Subsystem:**
   - **Pipeline 1 (Active Snake Sighting & Venom Analysis):**
     - *Stage 1 Gate:* MobileNetV2 pretrained on ImageNet-1k filtering ImageNet synsets 52–68 (*Serpentes*). Short-circuits non-snake images immediately as `NOT_A_SNAKE`.
     - *Stage 2 Venom Classifier:* `venomwatch_cnn2_final.keras` (MobileNetV2 feature extractor backbone with a single sigmoid neuron). Predicts `VENOMOUS` ($p \ge 0.50$) or `NON-VENOMOUS` ($p < 0.50$).
   - **Pipeline 2 (Active Snakebite Wound Screening):**
     - `venom_watch_snakebite_efficientnetb0.keras` (EfficientNetB0 binary classifier). Evaluates bite mark patterns with an uncertainty band ($0.40 \le p \le 0.60$) and non-diagnostic disclaimers.
   - **Archived / Inactive Artifact:**
     - `ai/models/best.pt` (Ultralytics YOLOv8n-cls 15-class classifier). Preserved from an earlier Google Colab training experiment; **not loaded or executed in active runtime**.
4. **Data & Storage Tier:**
   - **Database:** SQLite 3 (`db.sqlite3`), relational schema managed via Django ORM migrations.
   - **Media Storage:** File-system storage under `media/`:
     - `sightings/`: Citizen snake uploads.
     - `assignment_outcomes/`: Ranger field evidence photos.
     - `verification_docs/`: Official ID credentials (strictly blocked from public HTTP access).
     - `wounds/`: Transient wound screening uploads (purged immediately post-inference).

---

## 2. Module-by-Module Implementation Status

| Application Module | Primary Responsibilities | Implemented Models | Key Views / Services | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **`accounts`** | User registration, authentication, RBAC, official applications, account status, notifications, audit logs. | `UserProfile`, `AccountApplication`, `Notification`, `AuditLog` | `CustomLoginView`, `register_view`, `admin_provision_account_view`, `admin_application_document_view` | **Fully Verified & Implemented** (33 unit tests passing) |
| **`reports`** | Citizen sighting submission, image binding, duplicate/spam scoring, ranger dispatch, outcome review. | `SightingReport`, `RangerAssignment` | `create_report_view`, `list_reports_view`, `authority_map_view`, `review_assignment_outcome_view`, `DuplicateSpamDetectionService`, `get_candidate_rangers` | **Fully Verified & Implemented** (24 unit tests passing) |
| **`ai`** | Two-stage deep learning inference, model caching, wound image screening. | *(No DB models; stateless)* | `SnakeAIPipelineService`, `SnakebiteScreeningService`, `SnakeAIAnalysisAPIView`, `wound_checker_view` | **Fully Verified & Implemented** (Execution confirmed) |
| **`hotspots`** | DBSCAN spatial density clustering, community risk zone classification. | *(No DB models; dynamic)* | `DBSCANHotspotService`, `hotspots_view`, `hotspots_api_view` | **Fully Verified & Implemented** (Haversine DBSCAN verified) |
| **`ranger`** | Isolated responder console, assignment acceptance, linear status advancement, outcome notes & photo evidence. | Uses `RangerAssignment` from `reports` | `ranger_dashboard_view`, `assignment_list_view`, `assignment_detail_view`, `assignment_update_view` | **Fully Verified & Implemented** (4 unit tests passing) |
| **`emergency`** | Anti-venom hospital registry, Haversine distance search, Emergency SOS trigger and feed. | `Hospital`, `EmergencySOSEvent` | `assistance_view`, `sos_trigger_api`, `sos_feed_api`, `admin_hospital_manage_view` | **Fully Verified & Implemented** (14 unit tests passing) |
| **`dashboard`** | Role-based landing router, authority surveillance metrics. | Aggregates data from `reports`, `hotspots` | `landing_page_view`, `dashboard_home_view` | **Fully Verified & Implemented** |

---

## 3. Active AI Pipeline Summary

```
                               ┌─────────────────────────────┐
                               │     Uploaded Image File     │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │ Single-pass RGB 224x224     │
                               │ Input Tensor Normalization  │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │    STAGE 1: GATE CHECK      │
                               │ MobileNetV2 (ImageNet)      │
                               │ Synsets 52-68 (Serpentes)   │
                               └──────────────┬──────────────┘
                                              │
                              Is snake_prob >= 0.15 or in top-2?
                               ├── NO ──► STOP: Return "NOT_A_SNAKE"
                               │          (Stage 2 bypassed completely)
                               └── YES
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  STAGE 2: VENOM CLASSIFIER  │
                               │ venomwatch_cnn2_final.keras │
                               │ (MobileNetV2 Backbone)      │
                               └──────────────┬──────────────┘
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

- **Gate Rejection:** Non-snake images (e.g., domestic animals, objects) are filtered before invoking the specialized venom model, preventing false venomous predictions on non-reptilian subjects.
- **Model Storage:** Both active `.keras` models are versioned directly in the project root (`venomwatch_cnn2_final.keras`, 23.68 MB and `venom_watch_snakebite_efficientnetb0.keras`, 35.35 MB).
- **Inference Time:** In-memory model caching via thread-safe singleton (`MODEL_CACHE`) yields warm-start inference times under 50 ms.

---

## 4. Key Implementation Findings

1. **Strict Object-Level Security on Field Assignments:**
   - A Ranger can only view and update assignments where `assignment.ranger == request.user`. Attempting to access another ranger's assignment returns an HTTP 404/403.
   - Rangers are prohibited from marking an assignment `COMPLETED`. Only an Authority Officer reviewing the submitted outcome can verify and resolve an incident.
2. **Algorithmic Location-Based Dispatch:**
   - Candidate rangers are filtered server-side: account must be active, role `ranger`, status `ACTIVE`, application `APPROVED`, availability `AVAILABLE`, and located within a 30 km Haversine radius of the sighting coordinates.
3. **Multi-Signal Duplicate & Spam Engine:**
   - Calculates a documented composite score ($0-100$) based on distance ($\le 500$ m), temporal proximity ($\le 6$ h), and species/venom consistency. High-confidence duplicates ($\ge 75$) are automatically linked to the canonical incident, preventing redundant field dispatches.
4. **Dynamic DBSCAN Geospatial Risk Zones:**
   - Community risk sectors are computed dynamically at runtime using spherical Haversine DBSCAN. A 4-state lifecycle (Red, Orange, Yellow, Green) categorizes geographic risk while protecting citizen privacy by rendering circular sectors rather than exact incident coordinates.
5. **Security Gates on Verification Documents:**
   - Direct HTTP access to `/media/verification_docs/` is blocked by an explicit Django URL route returning HTTP 403 Forbidden. Documents are served exclusively through an audited view requiring administrator privileges.

---

## 5. Limitations and Unresolved Questions

1. **Origin of `best.pt`:** A 3.0 MB PyTorch YOLOv8n-cls checkpoint trained on 15 classes exists in `ai/models/`, containing full 50-epoch training metrics in its metadata dictionary. However, the runtime codebase transitioned to the binary MobileNetV2 model. The exact timeline of this transition is documented in git commit history (`5b682110`), but training scripts for the binary model are external.
2. **Keras Training Histories:** The binary models (`venomwatch_cnn2_final.keras` and `venom_watch_snakebite_efficientnetb0.keras`) were compiled and saved in external Google Colab GPU sessions. Their weights, configs, and layers are fully intact, but epoch-by-epoch loss/accuracy CSV logs are not stored in the repository.
3. **No External SMS Gateway:** The Emergency SOS system persists distress events and alerts Authority officers in real time via database feeds, but does not connect to an external cellular SMS gateway (e.g., Twilio).
4. **Production Server Configuration:** The repository contains development configuration (`DEBUG = True`, SQLite3); deployment configurations (Gunicorn, Nginx, PostgreSQL) are not present in source control.
