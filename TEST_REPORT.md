# VenomWatch — Test Report & Verification Document

**Project Name:** VenomWatch  
**Academic Context:** MCA Project, TKM College of Engineering, Department of Computer Applications (2025–2027)  
**Project Members:** Nehmal N (25MCA043), Nidhish Chandran (25MCA044)  
**Project Guide:** Natheera Beevi S.  
**Execution Timestamp:** October 17, 2026 — 22:38 IST  
**Environment:** Python 3.11, Django 5.x, SQLite 3, Windows 11  

---

## 1. System Health Check

Command executed:
```bash
python manage.py check
```
**Output:**
```
System check identified no issues (0 silenced).
Exit Code: 0
```

---

## 2. Migration Status

Command executed:
```bash
python manage.py showmigrations
```
**Output:**
```
[X] emergency.0001_initial
[X] emergency.0002_emergencysosevent
[X] reports.0001_initial
[X] reports.0002_rangerassignment
[X] reports.0003_rangerassignment_is_read_rangerassignment_read_at
[X] reports.0004_rangerassignment_distance_km
[X] reports.0005_rangerassignment_outcome_submitted_at_and_more
All migrations applied cleanly.
```

---

## 3. Automated Test Suite Results

Command executed:
```bash
python manage.py test
```
**Summary:**
```
Ran 18 tests in 26.179s
OK
Destroying test database for alias 'default'...
```

### Detailed Test Case Inventory

| Test Class | Method Name | Status | Functionality Verified |
|---|---|---|---|
| `AccountsWorkflowTestCase` | `test_citizen_registration_always_assigns_citizen_role` | **PASS** | Prevents privilege escalation during self-registration. Forced `ROLE_CITIZEN`. |
| `AccountsWorkflowTestCase` | `test_admin_provision_authority_and_ranger` | **PASS** | Platform Admin creates Authority & Ranger accounts with districts, coords, availability. Tests new user login and dashboard redirection. |
| `AccountsWorkflowTestCase` | `test_non_admin_cannot_access_provisioning` | **PASS** | Enforces server-side 403 Forbidden when Citizens/Rangers access `/accounts/provision/`. |
| `AccountsWorkflowTestCase` | `test_session_logout` | **PASS** | Validates session flush and redirection to login page upon logout. |
| `EmergencySOSTestCase` | `test_sos_trigger_persists_event` | **PASS** | Validates `EmergencySOSEvent` persistence with coordinates, contact phone, and `ACTIVE` status. |
| `EmergencySOSTestCase` | `test_sos_duplicate_throttling` | **PASS** | Prevents duplicate distress spam within 2-minute window at identical GPS location. |
| `EmergencySOSTestCase` | `test_sos_authority_feed_and_acknowledgement` | **PASS** | Tests Authority feed query, `ACKNOWLEDGE` status transition, and `RESOLVE` transition with audit notes. |
| `EmergencySOSTestCase` | `test_sos_security_denied_for_citizen` | **PASS** | Enforces 403 Forbidden for non-authority users querying the operations distress feed or acknowledging events. |
| `EmergencySOSTestCase` | `test_hospital_distance_calculation` | **PASS** | Validates exact spherical Haversine distance in kilometers for nearest anti-venom hospital sorting. |
| `VenomWatchAccessControlTestCase` | `test_sighting_properties` | **PASS** | Validates `is_venomous` property and 48-hour active status window for DBSCAN clustering. |
| `VenomWatchAccessControlTestCase` | `test_dbscan_clustering` | **PASS** | Verifies DBSCAN clustering algorithm grouping nearby active reports using radian coordinates. |
| `VenomWatchAccessControlTestCase` | `test_citizen_access_control_denied` | **PASS** | Verifies Citizen is denied Authority Dashboard (403), Hotspot Radar (403), Clusters API (403), and Other Citizen's Report (403). |
| `VenomWatchAccessControlTestCase` | `test_citizen_sees_only_own_reports_in_list` | **PASS** | Verifies data isolation: Citizens only see their own submitted sighting reports in the history list. |
| `VenomWatchAccessControlTestCase` | `test_authority_access_control_allowed` | **PASS** | Verifies Authority user has full authorized access to surveillance dashboard, radar, and detail reports. |
| `VenomWatchAccessControlTestCase` | `test_duplicate_detection_multi_signal_scoring` | **PASS** | Evaluates multi-signal duplicate engine: score >= 75, automatic `duplicate_of` linking, and reason text generation. |
| `VenomWatchAccessControlTestCase` | `test_duplicate_detection_does_not_merge_resolved_incidents` | **PASS** | Verifies edge case: sightings near previously resolved incidents are kept independent and not auto-merged. |
| `VenomWatchAccessControlTestCase` | `test_ranger_assignment_and_authority_review_lifecycle` | **PASS** | Complete 6-step lifecycle: Authority assigns -> Ranger accepts (availability becomes `BUSY`) -> en route -> at location -> outcome submitted (`OUTCOME_SUBMITTED`) -> Authority rejects for sweep -> Ranger re-submits -> Authority approves (`COMPLETED`, sighting `STATUS_RESOLVED`, ranger `AVAILABLE`). |
| `VenomWatchAccessControlTestCase` | `test_ranger_object_level_security` | **PASS** | Verifies Ranger A cannot inspect or manipulate Ranger B's assignment detail (HTTP 404). |

---

## 4. End-to-End Scenarios Verification

### Scenario A — Citizen Reporting
- Citizen navigates to `/reports/create/`.
- Uploads sighting image, selects coordinates via interactive Leaflet picker, submits report.
- Report persists with status `PENDING`, AI prediction runs, and report appears in citizen's personal history.
- **Result:** **Verified & Passing.**

### Scenario B — AI Analysis Pipeline
- Model `venomwatch_cnn2_final.keras` loaded and cached via `SnakeAIPipelineService`.
- Stage 1 Gate validates image against ImageNet Serpentes synsets 52–68 to reject non-snakes (rats, cats, dogs).
- Stage 2 MobileNetV2 classifies binary venomous vs non-venomous with confidence percentage.
- Wound model `venom_watch_snakebite_efficientnetb0.keras` evaluates puncture marks with 0.40–0.60 uncertainty handling.
- **Result:** **Verified & Passing.**

### Scenario C — Automated Duplicate Detection
- Multi-signal scoring evaluates spatial distance (Haversine), time delta, and species match.
- High-confidence duplicates (>= 75) automatically link to canonical root incident and prevent duplicate responder dispatches.
- Medium-confidence duplicates (45–74) flag `duplicate_flag=True` with `duplicate_reason` for Authority manual review.
- Resolved incidents are protected against auto-linking.
- **Result:** **Verified & Passing.**

### Scenario D — Authority Operations & Verification
- Authority logs in directly to `/authority/map/` with real database incident markers and ArcGIS World Street Map tiles.
- Selects report, inspects details and candidate rangers sorted by Haversine proximity.
- Assigns ranger; tracks response status.
- Once ranger submits field outcome, reviews outcome description and evidence photo.
- Approves outcome (transitions to `COMPLETED`, marks report `RESOLVED`, frees ranger to `AVAILABLE`), or rejects with notes.
- **Result:** **Verified & Passing.**

### Scenario E — Ranger Console
- Ranger logs in to `/ranger/`, viewing only their assigned tasks.
- Accepts assignment, updates status to `ON_THE_WAY` and `AT_LOCATION`.
- Submits structured outcome form (`SUBMIT_OUTCOME`) with outcome category, field notes, and optional photo.
- Receives Authority verification decision or feedback.
- Object-level security prevents viewing or editing other rangers' assignments.
- **Result:** **Verified & Passing.**

### Scenario F — Admin Account Provisioning
- Platform Administrator accesses `/accounts/provision/` (protected by `@admin_required`).
- Provisions Authority Officers and Field Rangers with username, password, district, base coordinates, and initial availability.
- Accounts are created with secure password hashing and proper role profiles.
- Verified that newly created officers/rangers can log in and reach their respective consoles.
- **Result:** **Verified & Passing.**

### Scenario G — Geographic Analytics & Risk Zones
- Reports with valid coordinates render on Authority Leaflet map and public community risk zones.
- DBSCAN clustering (`hotspots/services.py`) uses exact spherical Haversine distance projection in radians (`eps_km / 6371.0`), preventing degree-to-meter distortions.
- Community Risk Zones aggregate 24h reports into Green, Yellow, and Red zones without leaking private citizen coordinates.
- **Result:** **Verified & Passing.**

### Scenario H — Emergency SOS & Hospital Logistics
- Citizen triggers SOS on `/emergency/` with browser GPS acquisition and callback phone.
- Event is persisted in `EmergencySOSEvent` with status `ACTIVE`.
- Duplicate activations within 2 minutes are throttled.
- Authority operations feed (`/emergency/api/sos/feed/`) displays active distress signals.
- Authority can acknowledge or resolve incidents with clinical notes.
- Nearest anti-venom specialty hospitals calculate Haversine distance with vial stock and ICU availability.
- **Result:** **Verified & Passing.**

### Scenario I — Authentication & Security
- Unauthorized visitors cannot access protected pages (`@login_required`).
- Citizens cannot access Authority surveillance or Admin consoles (`@authority_required`, `@admin_required`).
- Rangers cannot access Authority maps or other rangers' assignments (`@ranger_required`).
- Public registration strictly forces `ROLE_CITIZEN`; privilege escalation via form injection is blocked.
- Logout invalidates Django sessions cleanly.
- **Result:** **Verified & Passing.**

---

## 5. Live Browser Verification Artifacts

- **Emergency Support & Hospital Locator Page Screenshot:**  
  `file:///C:/Users/User/.gemini/antigravity-ide/brain/e44c57d6-06b3-4997-b158-6716710fc572/emergency_support_page_1792256794796.png`
- **End-to-End Walkthrough Recording:**  
  `file:///C:/Users/User/.gemini/antigravity-ide/brain/e44c57d6-06b3-4997-b158-6716710fc572/verify_e2e_features_1792256199920.webp`

---

## 6. Unresolved Issues & Future Enhancements

- **Unresolved Critical Bugs:** 0
- **Failing Tests:** 0
- **Optional Enhancements for Production:**
  - Connect SMS gateway (Twilio / Fast2SMS) for live SMS broadcast upon Emergency SOS creation when credentials become available.
  - Periodic background celery worker for continuous DBSCAN cluster cache warming.
