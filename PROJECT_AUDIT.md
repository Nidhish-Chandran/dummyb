# VENOMWATCH — COMPREHENSIVE PROJECT AUDIT REPORT

**Date:** October 2026  
**Auditors:** Nehmal N (25MCA043), Nidhish Chandran (25MCA044)  
**Project Guide:** Natheera Beevi S.  
**Institution:** Department of Computer Applications, TKM College of Engineering, Kollam  
**Repository:** `https://github.com/Nidhish-Chandran/dummyb`  
**Django Version:** 5.1 | **Python:** 3.11 | **TensorFlow:** 2.21.0 | **Keras:** 3.15.0  

---

## 1. Executive Summary

VenomWatch is an AI-powered snake-sighting surveillance, geographic risk monitoring, and coordinated wildlife-response platform designed for public safety and ecological protection in Kerala and similar high-biodiversity regions. 

The audit identified a solid foundation with several well-crafted modules (DBSCAN clustering, AI pipeline service, two-stage gate, and role separation), alongside specific gaps requiring targeted implementation to achieve full project completion:
1. **Emergency SOS Persistence:** SOS activations previously triggered only an ephemeral JSON response without persisting the incident to the database or providing an Authority review feed.
2. **Outcome Submission & Authority Verification Lifecycle:** When a Ranger marked a task complete, it resolved the incident immediately without formal Authority review (`OUTCOME_SUBMITTED` -> `UNDER_REVIEW` -> `COMPLETED`/`REJECTED`).
3. **Automated Duplicate Detection Refinements:** Proximity checks flagged duplicates, but did not prevent duplicate responder dispatch or calculate a documented multi-signal duplicate likelihood score.
4. **Admin Account Provisioning:** Authority and Ranger accounts must be created by platform administrators, but Django admin lacked `UserProfile` inline integration and a dedicated provisioning interface.
5. **Basemap Tile Configuration:** Leaflet maps in several templates required verified tile provider URLs and fallbacks.

---

## 2. Django Configuration & App Structure

| Application | Purpose | Status | Audit Findings |
|---|---|---|---|
| `venomwatch` | Project settings, root URL configuration, WSGI/ASGI | Working | Configured with SQLite, secure password validators, media/static handlers. |
| `accounts` | Authentication, UserProfile, role definitions, decorators | Functional | Clean role separation (`citizen`, `ranger`, `authority`, `admin`). Missing Admin inline in `admin.py`. |
| `reports` | Sighting submissions, Ranger assignments, dispatch | Core Working | Rich `SightingReport` and `RangerAssignment` models. Needs outcome review lifecycle. |
| `ai` | Two-stage snake identification, wound screening | Functional | Pre-trained `venomwatch_cnn2_final.keras` and `venom_watch_snakebite_efficientnetb0.keras` verified. |
| `ranger` | Isolated console for field responders | Functional | Object-level security properly isolates ranger assignments. Needs structured outcome form. |
| `dashboard` | Landing page, Authority map alias, surveillance overview | Functional | Authority Map correctly configured as primary operational dashboard. |
| `hotspots` | DBSCAN spatial clustering and community risk zones | Working | Mathematically sound spherical Haversine metric with temporal filtering. |
| `emergency` | Anti-venom hospital logistics and SOS endpoints | Incomplete | `Hospital` model and Haversine distance working; `EmergencySOS` persistence missing. |

---

## 3. Detailed Component Audit

### 3.1 AI Inference Pipeline
* **Snake Model (`venomwatch_cnn2_final.keras`):**
  - Architecture: MobileNetV2 feature extractor followed by GlobalAveragePooling2D, Dense(128, ReLU), and Dense(1, Sigmoid).
  - Task: Binary venom classifier (`VENOMOUS` if sigmoid >= 0.50, `NON-VENOMOUS` if sigmoid < 0.50).
  - Singleton caching in `ai/services.py` eliminates repetitive loading overhead (<0.08s inference).
* **Stage 1 Gate (Snake vs. Non-Snake):**
  - Uses MobileNetV2 ImageNet synsets 52–68 (Suborder Serpentes).
  - Images lacking snake characteristics (e.g. rats, dogs, domestic animals) are rejected at Stage 1 before the venom classifier executes, preventing false venomous classifications on non-snake objects.
* **Wound Screening Model (`venom_watch_snakebite_efficientnetb0.keras`):**
  - Architecture: EfficientNetB0 binary classifier (224x224x3 RGB).
  - Outputs probability of snakebite puncture / tissue trauma pattern.
  - Uncertainty band (0.40–0.60) alerts the user to seek immediate emergency medical evaluation.

### 3.2 Automated Duplicate Sighting Engine
* **Current Implementation:** Checked Euclidean/Haversine distance (< 500m) and temporal window (< 2 hours).
* **Gaps Identified:**
  - Did not check if the prior report was already `RESOLVED` (a new snake appearing at the same spot days later was risk of incorrect auto-linking).
  - Did not compute a composite duplicate likelihood score (0–100) combining spatial, temporal, and species signals.
  - Linked duplicates could still allow duplicate active ranger assignments.
* **Resolution Plan:** Upgrade `DuplicateSpamDetectionService` to implement multi-signal scoring, automated linking on high-confidence, flagging on medium-confidence, and assignment consolidation.

### 3.3 Ranger Response & Authority Verification
* **Current Implementation:** Ranger moves assignment from `ASSIGNED` -> `ACCEPTED` -> `ON_THE_WAY` -> `AT_LOCATION` -> `COMPLETED`.
* **Gaps Identified:**
  - Authority had no formal review step to inspect the outcome photograph, confirm capture/relocation, or reject false outcomes.
  - Transition jumped directly to `COMPLETED` and resolved the sighting report without audit.
* **Resolution Plan:** Introduce `OUTCOME_SUBMITTED` state, outcome categories, photo evidence validation, and an Authority review/approval action.

### 3.4 Emergency SOS & Hospital Logistics
* **Current Implementation:** `Hospital` model computes Haversine distance and displays anti-venom stock and ICU status.
* **Gaps Identified:**
  - `sos_trigger_api` returned a static JSON message without saving the distress event.
  - Authorities could not view active emergency SOS events on their console.
* **Resolution Plan:** Create `EmergencySOSEvent` model, persist SOS calls with coordinates and user contact, and display an active SOS alert feed on the Authority Map.

### 3.5 Admin Account Management
* **Current Implementation:** Superusers managed users via `/admin/`, but `accounts/admin.py` was blank.
* **Gaps Identified:** Admin had no direct form to provision Authority officers or Rangers with operational coordinates and districts.
* **Resolution Plan:** Register custom `UserProfileAdmin` and inline into `UserAdmin`, and provide an Admin account provisioning interface.

---

## 4. Audit Action Plan

1. **Database & Models:**
   - Add `EmergencySOSEvent` in `emergency/models.py`.
   - Enhance `RangerAssignment` in `reports/models.py` with review status, reviewer, review notes, and outcome choices.
   - Run `python manage.py makemigrations` and `python manage.py migrate`.
2. **Services & Business Logic:**
   - Upgrade `reports/services.py` with multi-signal duplicate scoring and incident linkage.
   - Update `emergency/views.py` to persist SOS events.
   - Add Authority verification endpoints in `reports/views.py`.
3. **Admin & Roles:**
   - Implement `accounts/admin.py` with user profile inlines and operational fields.
4. **Templates & UI:**
   - Update `templates/ranger/assignment_detail.html` with outcome photo upload.
   - Update `templates/reports/authority_map.html` with outcome review modal and SOS alerts.
   - Update `templates/emergency/assistance.html` with real-time SOS logging.
5. **Testing & Verification:**
   - Write comprehensive unit tests in `reports/tests.py`, `emergency/tests.py`, and `accounts/tests.py`.
   - Run end-to-end verification via Django test runner and browser automation.
