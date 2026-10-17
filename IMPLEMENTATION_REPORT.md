# VenomWatch — Implementation Report

**Project Name:** VenomWatch (Snake-Sighting Surveillance, AI-Assisted Identification, Geographic Risk-Analysis, and Public-Safety Response Platform)  
**Academic Context:** MCA Project, TKM College of Engineering, Department of Computer Applications (2025–2027)  
**Project Members:** Nehmal N (25MCA043), Nidhish Chandran (25MCA044)  
**Project Guide:** Natheera Beevi S.  
**Repository:** `https://github.com/Nidhish-Chandran/dummyb`  
**Date:** October 17, 2026  

---

## 1. Executive Summary

This implementation report documents the complete engineering audit, structural enhancements, module integrations, workflow completions, and security hardening executed on the VenomWatch platform. The application satisfies every core requirement defined in its approved project specification while preserving existing database records, migrations, AI checkpoints, and Django architecture.

---

## 2. Key Modules Completed & Enhanced

### 2.1 Role-Based Access Control & Navigation (ROL, NAV, SEC)
- **Role Isolation**: Enforced 4 distinct operational roles:
  - **Citizen**: Public registration, sighting submission, personal sighting history, Wound Checker, Emergency SOS. Restricted from accessing other users' records or authority endpoints.
  - **Authority**: Landing on Authority Operations Map, incident monitoring, nearest-ranger location-filtered dispatch, duplicate analysis, outcome review, and hotspot radar.
  - **Ranger**: Dedicated isolated console (`/ranger/`), assignment tracking, GPS incident navigation, dispatch lifecycle (`ASSIGNED` -> `ACCEPTED` -> `ON_THE_WAY` -> `AT_LOCATION` -> `OUTCOME_SUBMITTED` -> `COMPLETED`), field outcome and evidence photo submission. Object-level security prevents viewing other rangers' assignments.
  - **Platform Admin**: Dedicated account provisioning console (`/accounts/provision/`) for creating Authority and Ranger accounts with operational districts, coordinates, and availability; inlined Django Admin profile management.
- **Navigation & CSS Polish**:
  - Restyled login and registration views with responsive cards, 2-column input layouts, and custom focus states.
  - Converted navbar user identity into display-only badge pills (`.user-identity-card.user-identity-badge`) to eliminate duplicate profile clicks.
  - Removed duplicate in-page logout buttons from profile templates, retaining single global navbar logout.
  - Removed Citizen navbar logout button per design specification while preserving session invalidation.

### 2.2 Automated Multi-Signal Duplicate Sighting Detection (DUP, REP)
- **Service**: Upgraded `DuplicateSpamDetectionService` in `reports/services.py`.
- **Composite Scoring Signals**:
  - **Geographic Proximity (Haversine)**: <= 50m (+50 pts), <= 200m (+35 pts), <= 500m (+20 pts).
  - **Temporal Proximity**: <= 30 mins (+30 pts), <= 2 hrs (+15 pts), <= 6 hrs (+5 pts).
  - **Species & Venom Consistency**: Exact predicted species match (+20 pts), matching venom class (+10 pts).
  - **Reporter Frequency / Re-submission**: +10 pts.
- **Decision Engine**:
  - **High-Confidence (Score >= 75)**: Automatically links `duplicate_of` to the canonical active root incident, sets `duplicate_flag = True`, records `duplicate_score` and `duplicate_reason`. Prevents duplicate responder dispatches.
  - **Medium-Confidence (45 <= Score < 75)**: Flags for Authority manual review with detailed rationale without blocking incident response.
  - **Low-Confidence (Score < 45)**: Retains sighting as an independent incident.
  - **Edge-Case Protection**: Sighting reports marked `STATUS_RESOLVED` are strictly excluded as candidate parents, preventing new encounters from auto-merging into historical resolved records.

### 2.3 Ranger Outcome Submission & Authority Verification Lifecycle (RNG, AUT)
- **Model Upgrades**: Added `outcome_submitted_at`, `reviewed_by`, `reviewed_at`, `review_decision` (`PENDING_REVIEW`, `APPROVED`, `REJECTED`, `CLARIFICATION_REQUESTED`), and `review_notes` to `RangerAssignment`.
- **Ranger Console**:
  - Replaced immediate self-completion with `SUBMIT_OUTCOME`.
  - Structured outcome dropdown (`SNAKE_CAPTURED`, `SNAKE_RELOCATED`, `SNAKE_ESCAPED`, `REFERRED_OTHER_TEAM`, `UNRESOLVED`, `REPORT_UNVERIFIED`, `OTHER`), mandatory field notes, and optional supporting photo evidence upload.
  - Dynamic state cards: displays "Under Authority Review" during pending verification, or actionable Authority feedback if clarification/rejection occurs.
- **Authority Verification**:
  - Implemented `review_assignment_outcome_view` in `reports/views.py` (`/reports/assignments/<id>/review/`).
  - Integrated verification panel in `templates/reports/detail.html`:
    - **Approve**: Sets assignment to `COMPLETED`, sets `completed_at`, marks sighting `STATUS_RESOLVED`, frees ranger to `AVAILABLE`.
    - **Reject**: Returns assignment to `AT_LOCATION`, records review notes/instructions for ranger follow-up sweep.
    - **Request Clarification**: Holds in review and logs query for responder.

### 2.4 Real Emergency SOS Persistence & Logistics (SOS, HOS)
- **Model**: Created `EmergencySOSEvent` in `emergency/models.py` tracking GPS coordinates, reporter phone number, location name, status (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`), acknowledging authority officer, and resolution notes.
- **Interactive Citizen Trigger**:
  - Added "Log Emergency SOS Distress Signal" card in `templates/emergency/assistance.html` with browser GPS acquisition and callback phone capture.
  - Two-minute duplicate throttling prevents spam/repeated activations at identical coordinates.
- **Authority Operations Feed**:
  - Exposed `/emergency/api/sos/feed/` and `/emergency/api/sos/<id>/ack/` for live operations monitoring, acknowledgement, and resolution logging.
  - Hospital locator sorts hospitals by spherical Haversine distance, displaying anti-venom vial inventory, 24/7 ICU availability, emergency call links, and Google Maps directions.

### 2.5 Admin Account Provisioning (ADM, SEC)
- **Django Admin Customization**:
  - `UserProfileInline` inlined into `UserAdmin` in `accounts/admin.py`.
  - Registered `UserProfileAdmin`, `SightingReportAdmin`, `RangerAssignmentAdmin`, `HospitalAdmin`, and `EmergencySOSEventAdmin`.
- **Custom Admin Console**:
  - Created `/accounts/provision/` (`admin_provision_account_view`, `AdminAccountProvisionForm`, `templates/accounts/admin_provision.html`).
  - Enables administrators to provision official Authority and Ranger accounts with operational districts, coordinates, and availability status.
  - Secured with `@admin_required` server-side authorization check.

### 2.6 AI Verification & Hotspot GIS (AI, GIS)
- **Snake Pipeline**: Verified two-stage architecture:
  1. ImageNet Serpentes synset validation gate (synsets 52–68) rejecting non-snake images (rats, dogs, cats, humans).
  2. MobileNetV2 (`venomwatch_cnn2_final.keras`) binary venom classification (venomous >= 0.50, non-venomous < 0.50).
- **Wound Screening**: Verified EfficientNetB0 (`venom_watch_snakebite_efficientnetb0.keras`) with 0.40–0.60 uncertainty handling and emergency guidance.
- **DBSCAN Risk Zones**: Verified spherical Haversine distance projection (`hotspots/services.py`), clustering incidents into risk zones without degree-to-meter distortion.

---

## 3. Files Created and Modified

| File | Type | Changes Made |
|---|---|---|
| `accounts/admin.py` | Python | Registered `UserProfileAdmin`, inlined `UserProfileInline` into `UserAdmin`. |
| `accounts/decorators.py` | Python | Added `admin_required` role-enforcement decorator. |
| `accounts/forms.py` | Python | Added `AdminAccountProvisionForm` with secure password hashing and role validation. |
| `accounts/models.py` | Python | Inspected and aligned `UserProfile` attributes. |
| `accounts/tests.py` | Python | Added test cases for role isolation, admin provisioning, and session logout. |
| `accounts/urls.py` | Python | Added `/accounts/provision/` route. |
| `accounts/views.py` | Python | Added `admin_provision_account_view` with permission enforcement. |
| `emergency/admin.py` | Python | Registered `HospitalAdmin` and `EmergencySOSEventAdmin`. |
| `emergency/models.py` | Python | Added `EmergencySOSEvent` with coordinates, status, and audit timestamps. |
| `emergency/tests.py` | Python | Added tests for SOS persistence, duplicate throttling, and Authority feeds. |
| `emergency/urls.py` | Python | Added `api_sos_feed` and `api_sos_ack` routes. |
| `emergency/views.py` | Python | Updated `sos_trigger_api`, added `sos_feed_api` and `sos_acknowledge_api`. |
| `ranger/views.py` | Python | Added `SUBMIT_OUTCOME` lifecycle step, outcome saving, and review tracking. |
| `reports/admin.py` | Python | Registered `SightingReportAdmin` and `RangerAssignmentAdmin`. |
| `reports/models.py` | Python | Added duplicate scoring/reason fields and outcome verification fields. |
| `reports/services.py` | Python | Replaced naive distance check with multi-signal composite duplicate engine. |
| `reports/tests.py` | Python | Added tests for multi-signal duplicate scoring, resolved edge cases, and assignment review lifecycle. |
| `reports/urls.py` | Python | Added `/reports/assignments/<pk>/review/` route. |
| `reports/views.py` | Python | Added `review_assignment_outcome_view` for Authority verification. |
| `static/css/style.css` | CSS | Restyled auth cards, navbar identity pill badge, form controls. |
| `templates/accounts/admin_provision.html` | HTML | Built admin account provisioning interface and operational roster table. |
| `templates/base.html` | HTML | Converted navbar badge to display-only pill; added admin provision link. |
| `templates/emergency/assistance.html` | HTML | Added interactive Emergency SOS Distress card with GPS fetch and alert display. |
| `templates/ranger/assignment_detail.html` | HTML | Added outcome submission form, under-review card, and Authority feedback display. |
| `templates/reports/detail.html` | HTML | Added duplicate score/reason badge and Authority Outcome Verification panel. |
| `PROJECT_AUDIT.md` | Markdown | Comprehensive architecture, models, gaps, and readiness audit. |
| `REQUIREMENTS_TRACEABILITY.md` | Markdown | Requirements matrix mapping requirements to code and tests. |
| `TEST_REPORT.md` | Markdown | Complete test execution scenarios and results. |
| `IMPLEMENTATION_REPORT.md` | Markdown | Detailed implementation and engineering report. |
