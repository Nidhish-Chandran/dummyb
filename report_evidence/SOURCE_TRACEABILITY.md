# Source Traceability Matrix — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-TRACEABILITY  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  

---

## 1. Traceability Standard

This document maps all architectural, machine learning, operational, and security claims to exact source file paths, class names, method identifiers, and line number ranges within the repository.

---

## 2. Core Traceability Matrix

| Functional Claim | Primary Source Path | Class / Function / Symbol | Line Range | Verifiable Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **System Check Passes Cleanly** | `manage.py` | CLI Entrypoint | N/A | `python manage.py check` outputs "System check identified no issues (0 silenced)". |
| **Installed Applications** | `venomwatch/settings.py` | `INSTALLED_APPS` | L33–L48 | Lists `accounts`, `reports`, `ai`, `hotspots`, `dashboard`, `emergency`, `ranger`, `rest_framework`. |
| **Protected Document Gate** | `venomwatch/urls.py` | `protected_media_block_view` | L24–L27 | Intercepts `/media/verification_docs/<path>` and raises `PermissionDenied` (HTTP 403). |
| **Role Hierarchy & Definition** | `accounts/models.py` | `UserProfile.ROLE_CHOICES` | L10–L20 | Defines 4 roles: `citizen`, `ranger`, `authority`, `admin`. |
| **Superuser Role Elevation** | `accounts/models.py` | `UserProfile.effective_role` | L80–L84 | If `user.is_superuser`, effective role is always returned as `admin`. |
| **Authority Console Membership** | `accounts/models.py` | `UserProfile.is_authority` | L105–L110 | Evaluates `is_admin or is_authority_officer` (rangers are explicitly excluded). |
| **Role Enforcement Decorator** | `accounts/decorators.py` | `authority_required` | L15–L28 | Checks `profile.is_authority`; raises `PermissionDenied` on unauthorized access. |
| **Ranger Console Decorator** | `accounts/decorators.py` | `ranger_required` | L30–L42 | Checks `profile.is_ranger`; raises `PermissionDenied` on non-ranger users. |
| **Official Role Application** | `accounts/models.py` | `AccountApplication` | L137–L184 | Stores requested role (`authority` or `ranger`), uploaded credential document, review status. |
| **Admin Application Review** | `accounts/views.py` | `admin_provision_account_view` | L158–L250 | Atomic transaction approves application, sets `is_active=True`, records `AuditLog` entry. |
| **Secure Document Streaming** | `accounts/views.py` | `admin_application_document_view` | L612–L665 | Validates admin session before streaming `supporting_document` with `FileResponse`. |
| **Account Ban & Suspension** | `accounts/views.py` | `admin_provision_account_view` | L350–L389 | Sets `account_status` to `SUSPENDED` or `BANNED`, deactivates login, records reason. |
| **Admin Self-Protection Gate** | `accounts/views.py` | `admin_provision_account_view` | L352–L360 | Security policy blocks suspending or banning the last active platform administrator. |
| **Admin Profile Read-Only Gate** | `accounts/views.py` | `admin_account_edit_view` | L906–L939 | Blocks POST requests attempting to alter responder coordinates or personal details. |
| **Two-Stage Snake AI Pipeline** | `ai/services.py` | `SnakeAIPipelineService.analyze_image` | L160–L353 | Orchestrates Stage 1 gate detector followed by Stage 2 binary venom classifier. |
| **Stage 1 Serpentes Synset Check** | `ai/services.py` | `SnakeAIPipelineService.analyze_image` | L223–L232 | Checks ImageNet classes 52–68; flags snake if $\sum P_i \ge 0.15$ or in top-2 predictions. |
| **Stage 1 Non-Snake Rejection** | `ai/services.py` | `SnakeAIPipelineService.analyze_image` | L234–L285 | If not a snake, terminates immediately with `NOT_A_SNAKE`; Stage 2 is skipped. |
| **Stage 2 Venom Classifier** | `ai/services.py` | `SnakeAIPipelineService.get_venom_classifier` | L126–L148 | Loads `venomwatch_cnn2_final.keras` once into thread-safe `MODEL_CACHE` singleton. |
| **Venom Output Mapping** | `ai/services.py` | `map_venom_prediction` | L50–L59 | Maps single sigmoid output: $p \ge 0.50 \implies \text{VENOMOUS}$, $p < 0.50 \implies \text{NON-VENOMOUS}$. |
| **Snakebite Wound Screener** | `ai/services.py` | `SnakebiteScreeningService.analyze_wound_image` | L401–L515 | Loads `venom_watch_snakebite_efficientnetb0.keras` and evaluates bite characteristics. |
| **Wound Uncertainty Boundary** | `ai/services.py` | `SnakebiteScreeningService.UNCERTAINTY_RANGE` | L377, L454–L486 | Range $[0.40, 0.60]$ overrides status to `Unable to Confidently Classify`. |
| **Stateless Wound Checker View** | `ai/views.py` | `wound_checker_view` | L55–L106 | Evaluates uploaded wound photo, deletes file immediately, sets `Cache-Control: no-store`. |
| **Multi-Signal Duplicate Scoring** | `reports/services.py` | `DuplicateSpamDetectionService.calculate_duplicate_score` | L39–L101 | Evaluates distance ($\le 500$m), time ($\le 6$h), species consistency; outputs score $0-100$. |
| **Duplicate Auto-Linking** | `reports/services.py` | `DuplicateSpamDetectionService.evaluate_and_flag` | L147–L175 | Score $\ge 75$ auto-links `duplicate_of` to canonical parent incident. |
| **Spam Rate Limiter** | `reports/services.py` | `DuplicateSpamDetectionService.evaluate_and_flag` | L111–L123 | Flags user if $>3$ reports submitted within 5 minutes. |
| **Haversine Distance (km)** | `reports/dispatch.py` | `haversine_km` | L20–L34 | Computes great-circle distance between two coordinate pairs ($R = 6371.0088$ km). |
| **Location-Based Ranger Dispatch** | `reports/dispatch.py` | `get_candidate_rangers` | L36–L109 | Filters approved, active, available rangers within 30 km radius of sighting coordinates. |
| **Ranger Response Milestones** | `reports/models.py` | `RangerAssignment.ALLOWED_TRANSITIONS` | L209–L216 | Enforces linear transition graph; blocks ranger from setting `STATUS_COMPLETED`. |
| **Ranger Assignment Isolation** | `ranger/views.py` | `assignment_detail_view` | L72–L90 | Fetches assignment filtered by `ranger=request.user` (object-level security). |
| **Authority Outcome Review** | `reports/views.py` | `review_assignment_outcome_view` | L433–L558 | Handles `APPROVED` (marks incident `RESOLVED`), `REJECTED`, `CLARIFICATION_REQUESTED`. |
| **Authority Operations Map View** | `reports/views.py` | `authority_map_view` | L703–L740 | Enforces `@authority_required`; prepares unassigned venomous count telemetry. |
| **Authority Map JSON Feed** | `reports/views.py` | `authority_map_reports_api` | L742–L855 | Returns real DB sighting markers with coordinates and dispatch status color-coding. |
| **Haversine DBSCAN Risk Zones** | `hotspots/services.py` | `DBSCANHotspotService.compute_community_risk_zones` | L32–L247 | Converts coordinates to radians, runs DBSCAN (`eps=1.5km`, `ball_tree`), 4-state lifecycle. |
| **Authority Hotspot Radar** | `hotspots/services.py` | `DBSCANHotspotService.compute_hotspots` | L249–L398 | Evaluates 48h active reports with DBSCAN ($\epsilon=1.0$km, `min_samples=2`). |
| **Hospital Distance Sorting** | `emergency/views.py` | `assistance_view` | L13–L70 | Sorts hospital records nearest-first from citizen coordinates using `distance_from()`. |
| **Emergency SOS Broadcast** | `emergency/views.py` | `sos_trigger_api` | L72–L135 | Persists `EmergencySOSEvent`; throttles duplicate activations within 2 minutes. |
| **Emergency SOS Authority Feed** | `emergency/views.py` | `sos_feed_api` | L137–L161 | JSON feed of active distress incidents for Authority surveillance monitor. |
| **Hospital Admin CRUD** | `emergency/views.py` | `admin_hospital_manage_view` | L200–L250 | Enforces `@admin_required`; provides full create/edit/delete capability. |
