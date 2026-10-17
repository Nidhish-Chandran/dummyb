# VENOMWATCH — REQUIREMENTS TRACEABILITY MATRIX

**Project Title:** VenomWatch — AI-Powered Snake Sighting Monitoring, Geographic Risk Analysis & Public Safety Response  
**Academic Context:** MCA Project, Department of Computer Applications, TKM College of Engineering (2025–2027)  
**Project Members:** Nehmal N (25MCA043), Nidhish Chandran (25MCA044)  
**Project Guide:** Natheera Beevi S.  
**Repository:** `https://github.com/Nidhish-Chandran/dummyb`  
**Last Updated:** October 2026  

---

## Classification Legend
- **[VERIFIED]** Implemented, audited in code, and verified by test suite or browser execution.
- **[PARTIAL]** Implemented in code but lacks complete workflow or sub-feature.
- **[IN PROGRESS]** Currently being implemented / updated.
- **[MISSING]** Required by abstract / master specification, but was missing in original codebase.
- **[BLOCKED]** Blocked by missing external service or model asset (documented with mitigation).
- **[OUT OF SCOPE]** Explicitly excluded (e.g. YOLO, React rewrite, simulated live ambulance dispatch).

---

## 1. User Roles & Access Control

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **ROL-01** | **Citizen Role:** Self-registration strictly limited to Citizen role. View own sightings, submit reports, use wound checker, emergency SOS. | `accounts/models.py`, `accounts/forms.py`, `accounts/views.py`, `templates/accounts/register.html` | [VERIFIED] | [VERIFIED] | `tests.py`, Browser registration check (tampering rejected) |
| **ROL-02** | **Authority Role:** Land directly on `/authority/map/`. View authorized sightings, assign rangers, review duplicate detections, review ranger outcomes, view risk zones. | `accounts/models.py`, `reports/views.py`, `dashboard/views.py`, `templates/reports/authority_map.html` | [PARTIAL] | [VERIFIED] | Authority login redirect test, map assignment & outcome review verification |
| **ROL-03** | **Ranger Role:** Dedicated `/ranger/` portal. View only assigned incidents. Object-level isolation (cannot access others' assignments or authority tools). Accept, travel, arrive, submit outcome. | `ranger/views.py`, `reports/models.py`, `templates/ranger/dashboard.html`, `templates/ranger/assignment_detail.html` | [PARTIAL] | [VERIFIED] | Object-level security test (403/404 on unassigned), assignment lifecycle test |
| **ROL-04** | **Admin Role:** Custom and Django admin management for creating Authority and Ranger accounts, setting operational locations, coordinates, and viewing audit history. | `accounts/admin.py`, `accounts/views.py`, `accounts/forms.py`, `templates/admin/` | [PARTIAL] | [VERIFIED] | Admin account creation workflow test (creates Authority & Ranger, logs in) |
| **ROL-05** | **Privilege Escalation Prevention:** Users cannot elevate role via POST parameter tampering. Server-side role enforcement on all views. | `accounts/forms.py`, `accounts/decorators.py`, `reports/views.py` | [VERIFIED] | [VERIFIED] | Security penetration test with manipulated POST parameters |

---

## 2. Authentication, Navigation & Profiles

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **NAV-01** | **Clean Navbar Links:** Role-specific navigation items. No duplicate controls navigating to the same destination. | `templates/base.html`, `static/css/style.css` | [VERIFIED] | [VERIFIED] | Browser inspection across all 4 roles |
| **NAV-02** | **Display-Only Identity Badge:** Username and role pill displayed in navbar without redundant navigation href. | `templates/base.html`, `static/css/style.css` | [VERIFIED] | [VERIFIED] | DOM inspection: `user-identity-badge` is non-anchor with default cursor |
| **NAV-03** | **Single Navbar Logout:** Exactly one logout button in the main navbar for Authority, Ranger, and Admin. Removed from citizen navbar and profile pages. | `templates/base.html`, `templates/accounts/profile.html`, `templates/ranger/profile.html` | [VERIFIED] | [VERIFIED] | Visual inspection of profile pages & navbars |
| **NAV-04** | **Secure Session Termination:** `/accounts/logout/` invalidates session and flushes session data. Protected pages reject unauthenticated users. | `accounts/views.py`, `accounts/decorators.py` | [VERIFIED] | [VERIFIED] | Session invalidation test: back button / cached request denied |
| **NAV-05** | **Profile Management:** Users can update contact info, organization, and region without breaking permissions. | `accounts/views.py`, `accounts/forms.py`, `templates/accounts/profile.html` | [VERIFIED] | [VERIFIED] | Profile update POST test, database persistence check |

---

## 3. Snake AI Identification Pipeline

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **AI-01** | **Model Architecture Identification:** Verify model files. `venomwatch_cnn2_final.keras` is MobileNetV2 with 1 sigmoid output (binary venomous / non-venomous). | `ai/services.py`, `venomwatch_cnn2_final.keras` | [VERIFIED] | [VERIFIED] | Inspect Keras config, test sigmoid outputs >= 0.5 and < 0.5 |
| **AI-02** | **Snake vs. Non-Snake Gate:** Negative class / pre-screening gate to reject non-snake images (rat, dog, cat, person) before running venom classifier. | `ai/services.py` (MobileNetV2 ImageNet Gate: Synsets 52-68 Serpentes) | [VERIFIED] | [VERIFIED] | Test with non-snake image (rat/dog) -> rejected with `is_snake=False` |
| **AI-03** | **Venom Classification:** Evaluates confirmed snake images into VENOMOUS vs. NON-VENOMOUS with calibrated confidence percentage. | `ai/services.py` | [VERIFIED] | [VERIFIED] | Test with sample snake images, check confidence and venom category |
| **AI-04** | **Model Singleton Caching:** Models loaded once into memory to prevent high inference latency on repeated requests. | `ai/services.py` (`MODEL_CACHE`, `_MODEL_LOCK`) | [VERIFIED] | [VERIFIED] | Timing benchmark: subsequent requests execute in < 0.1s |
| **AI-05** | **Safe Fallback:** Model failures or corrupt images do not crash citizen report submission. Error messages inform user clearly. | `ai/services.py`, `reports/views.py` | [VERIFIED] | [VERIFIED] | Corrupted image upload test -> handled gracefully with fallback notes |

---

## 4. Wound Image Screening Pipeline

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **WND-01** | **Wound Model Verification:** `venom_watch_snakebite_efficientnetb0.keras` binary classifier for snakebite wound patterns. | `ai/services.py`, `venom_watch_snakebite_efficientnetb0.keras` | [VERIFIED] | [VERIFIED] | Model loading test, tensor dimension verification (224x224x3) |
| **WND-02** | **Dedicated Wound Portal:** Separate route `/ai/wound-checker/` for wound image screening with clear medical disclaimers. | `ai/urls.py`, `ai/views.py`, `templates/ai/wound_checker.html` | [VERIFIED] | [VERIFIED] | Browser test of wound checker upload, preview, and results |
| **WND-03** | **Uncertainty & Recommendation:** Ambiguous outputs (0.40–0.60) flagged as uncertain with urgent recommendation for clinical evaluation. | `ai/services.py` | [VERIFIED] | [VERIFIED] | Boundary evaluation test with synthetic sigmoid outputs |

---

## 5. Citizen Sighting Reports

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **REP-01** | **Sighting Submission:** Citizen uploads image, provides title, location, coordinates (picker or browser GPS), and notes. | `reports/views.py`, `reports/forms.py`, `templates/reports/create.html` | [VERIFIED] | [VERIFIED] | End-to-end report creation test |
| **REP-02** | **Coordinate Validation:** Latitude/longitude validated, stored as decimal degrees, displayed on Leaflet map. | `reports/models.py`, `reports/forms.py`, `templates/reports/create.html` | [VERIFIED] | [VERIFIED] | Coordinate bounds validation test (-90 to 90, -180 to 180) |
| **REP-03** | **History & Tracking:** Citizen views own submitted reports list and detail status (`PENDING`, `VERIFIED`, `RESOLVED`). | `reports/views.py`, `templates/reports/list.html`, `templates/reports/detail.html` | [VERIFIED] | [VERIFIED] | User-scoped queryset test (`reports.filter(user=request.user)`) |

---

## 6. Automated Duplicate-Sighting Detection

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **DUP-01** | **Incident vs. Report Distinction:** Multiple citizen reports can link to one underlying incident (`duplicate_of`), preserving original submissions. | `reports/models.py`, `reports/services.py` | [PARTIAL] | [VERIFIED] | Submit 2 reports at same location; second links to first |
| **DUP-02** | **Multi-Signal Duplicate Scoring:** Haversine distance (<50m high, <500m medium), time window (<2h), status check (not resolved). | `reports/services.py` | [PARTIAL] | [VERIFIED] | Unit test testing distance, time, and status boundary conditions |
| **DUP-03** | **Confidence-Based Action:** High confidence automatically links; medium flags for review; low creates independent incident. | `reports/services.py`, `reports/views.py` | [PARTIAL] | [VERIFIED] | Threshold test: auto-link on high, flag on medium |
| **DUP-04** | **Assignment Safeguard:** Prevent duplicate active ranger dispatches for duplicate sightings of the same snake encounter. | `reports/views.py`, `reports/dispatch.py` | [PARTIAL] | [VERIFIED] | Test: linked duplicate does not spawn redundant active assignment |
| **DUP-05** | **Authority Duplicate Management:** Authority can inspect grouped duplicates and confirm or detach links. | `templates/reports/authority_map.html`, `reports/views.py` | [PARTIAL] | [VERIFIED] | Authority UI inspection of linked duplicates panel |

---

## 7. Geographic Location & Authority GIS Map

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **GIS-01** | **Interactive Location Picker:** Leaflet picker on sighting creation form allowing pin drag, click, and reverse geocoding fallback. | `templates/reports/create.html` | [VERIFIED] | [VERIFIED] | Browser picker interaction test |
| **GIS-02** | **Authority Operations Map:** Dedicated `/authority/map/` visualizing incident markers with venom status, ranger status, and click-to-assign. | `templates/reports/authority_map.html`, `reports/views.py` | [VERIFIED] | [VERIFIED] | Browser test of marker rendering, popup click, and assignment panel |
| **GIS-03** | **Permitted Basemap Tiles:** Functional tile layer without broken API keys (ArcGIS World Street Map / OSM fallback). | `templates/reports/authority_map.html`, `templates/reports/detail.html` | [VERIFIED] | [VERIFIED] | Browser network inspection: HTTP 200 on tile requests |

---

## 8. DBSCAN Risk Zones & Spatial Analytics

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **DBC-01** | **Spherical Haversine Clustering:** DBSCAN with `metric='haversine'`, converting coords to radians and `eps = km / 6371.0`. | `hotspots/services.py` | [VERIFIED] | [VERIFIED] | Mathematical verification of distance calculation in test suite |
| **DBC-02** | **Temporal Filtering:** Dynamic cluster calculation using sightings within 24h/48h window. Excludes spam/rejected reports. | `hotspots/services.py` | [VERIFIED] | [VERIFIED] | Filter test: 72h old reports excluded from active clusters |
| **DBC-03** | **Public vs. Authority Views:** Public view displays aggregated regional risk categories (Green/Yellow/Red); Authority sees detailed GIS clusters. | `reports/views.py` (`risk_zones_public_view`), `hotspots/views.py` | [VERIFIED] | [VERIFIED] | Role test: Public user cannot see individual cluster GPS coordinates |

---

## 9. Ranger Response System & Authority Review

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **RNG-01** | **Proximity Ranger Matching:** Find nearby available rangers filtered by `role='ranger'` and sorted by Haversine distance. | `reports/dispatch.py`, `reports/views.py` | [VERIFIED] | [VERIFIED] | Dispatch algorithm test: closest ranger sorted first |
| **RNG-02** | **Availability State Machine:** Rangers transition between `AVAILABLE`, `BUSY` (on active assignment), and `OFFLINE`. | `accounts/models.py`, `reports/views.py`, `ranger/views.py` | [VERIFIED] | [VERIFIED] | State transition test on assignment acceptance and completion |
| **RNG-03** | **Linear Status Lifecycle:** `ASSIGNED` -> `ACCEPTED` -> `ON_THE_WAY` -> `AT_LOCATION` -> `OUTCOME_SUBMITTED` -> `UNDER_REVIEW` -> `COMPLETED`. | `reports/models.py`, `ranger/views.py`, `reports/views.py` | [PARTIAL] | [VERIFIED] | End-to-end status advancement test |
| **RNG-04** | **Structured Outcome Submission:** Ranger records outcome category (captured, relocated, escaped, not found), field notes, and photo evidence. | `reports/models.py`, `ranger/views.py`, `templates/ranger/assignment_detail.html` | [PARTIAL] | [VERIFIED] | Outcome form submission test with photo upload |
| **RNG-05** | **Authority Verification of Outcome:** Authority reviews ranger-reported outcome and approves, rejects, or requests clarification. | `reports/views.py`, `templates/reports/authority_map.html`, `templates/reports/detail.html` | [PARTIAL] | [VERIFIED] | Authority review action test: approve sets report `RESOLVED` |

---

## 10. Emergency SOS & Hospital Logistics

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **SOS-01** | **SOS Event Persistence:** SOS activations stored in database with coordinates, reporter, timestamp, and status. | `emergency/models.py`, `emergency/views.py` | [MISSING] | [VERIFIED] | POST to `/emergency/api/sos/` creates database record |
| **SOS-02** | **Transparent Feedback:** Inform user SOS is logged locally without falsely claiming an ambulance was dispatched. | `emergency/views.py`, `templates/emergency/assistance.html` | [PARTIAL] | [VERIFIED] | UI feedback verification test |
| **SOS-03** | **Authority SOS Feed:** Authorities can monitor, acknowledge, and resolve active emergency distress events. | `emergency/views.py`, `templates/emergency/sos_dashboard.html`, `templates/reports/authority_map.html` | [MISSING] | [VERIFIED] | Authority SOS list & acknowledge test |
| **HOS-01** | **Anti-Venom Hospital Directory:** Nearest hospital locator with verified Haversine distance, phone, anti-venom stock, and ICU capacity. | `emergency/models.py`, `emergency/views.py`, `templates/emergency/assistance.html` | [VERIFIED] | [VERIFIED] | Distance calculation test against known landmarks |

---

## 11. Admin Account Management Portal

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **ADM-01** | **Admin Account Creation Workflow:** Secure portal for platform administrator to provision Authority and Ranger accounts. | `accounts/admin.py`, `accounts/views.py`, `accounts/forms.py` | [MISSING] | [VERIFIED] | Admin creates Authority officer and Ranger user, verifies login |
| **ADM-02** | **Ranger Operational Base Configuration:** Admin sets ranger's operating region, town, base coordinates (lat/lng), and initial availability. | `accounts/forms.py`, `accounts/views.py`, `accounts/admin.py` | [PARTIAL] | [VERIFIED] | Profile field persistence and dispatch query test |
| **ADM-03** | **Django Admin Integration:** Inlined UserProfile in Django UserAdmin with role filter, availability status, and region. | `accounts/admin.py` | [MISSING] | [VERIFIED] | Inspect `/admin/auth/user/` in browser |

---

## 12. Security & Data Integrity

| Req ID | Requirement Description | Implementation Files | Initial Status | Target Status | Verification Test / Method |
|---|---|---|---|---|---|
| **SEC-01** | **CSRF & Form Validation:** All forms protected with `{% csrf_token %}` and server-side Django form validation. | All templates and forms | [VERIFIED] | [VERIFIED] | Automated security audit |
| **SEC-02** | **Object-Level Permissions:** Rangers cannot inspect/modify other rangers' tasks. Citizens cannot modify other citizens' sightings. | `ranger/views.py`, `reports/views.py` | [VERIFIED] | [VERIFIED] | Direct ID manipulation test returns 404/403 |
| **SEC-03** | **Media Upload Security:** Validated file formats (JPEG, PNG), dimension limits, and secure upload directory paths. | `reports/forms.py`, `ai/services.py` | [VERIFIED] | [VERIFIED] | Invalid file extension rejection test |
