# Academic Report Facts, Gaps, and Verification Standards — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-FACTS-GAPS  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  

---

## 1. Verified Facts Ready for the Academic Report

The following architectural and implementation facts are backed by direct source-code inspection and 100% passing automated test execution:

1. **Django Web Application Architecture:**
   - 7 core internal Django applications: `accounts`, `reports`, `ai`, `hotspots`, `emergency`, `ranger`, `dashboard`.
   - SQLite 3 database (`db.sqlite3`) with relational integrity enforced via Django ORM.
   - Comprehensive automated test suite comprising **85 tests across 8 test classes**, executing with **100% pass rate (0 failures, 0 errors, Exit Code: 0)**.
2. **Four-Tier User Role Hierarchy & RBAC:**
   - Implemented roles: `citizen` (self-service registration), `ranger` (field responder), `authority` (dispatch and verification supervisor), `admin` (system governance).
   - Server-side decorator gates (`@authority_required`, `@ranger_required`, `@admin_required`) block unauthorized URL access.
   - Official Authority and Ranger registrations require administrative review of uploaded supporting credentials with protected media streaming.
3. **Verified Two-Stage Snake AI Pipeline:**
   - *Stage 1 Gate:* MobileNetV2 pretrained on ImageNet checking Serpentes synsets 52–68. Images failing this gate ($\sum P_i < 0.15$ and not in top-2) are rejected immediately as `NOT_A_SNAKE`.
   - *Stage 2 Venom Classifier:* `venomwatch_cnn2_final.keras` (23.68 MB, MobileNetV2 backbone with 1 scalar sigmoid output neuron):
     $$p \ge 0.50 \implies \text{VENOMOUS (Confidence } = p \times 100\%)$$
     $$p < 0.50 \implies \text{NON-VENOMOUS (Confidence } = (1-p) \times 100\%)$$
4. **Verified Snakebite Wound Screening Service:**
   - `venom_watch_snakebite_efficientnetb0.keras` (35.35 MB, EfficientNetB0 binary classifier).
   - Evaluates puncture mark characteristics with a clinical safety uncertainty interval $[0.40, 0.60]$ that triggers `Unable to Confidently Classify` and displays mandatory emergency medical disclaimers.
5. **Multi-Signal Duplicate & Spam Detection:**
   - Automated score ($0-100$) based on Haversine distance ($\le 500$ m), temporal window ($\le 6$ h), and venom class consistency.
   - Scores $\ge 75$ auto-link to the canonical incident, preventing duplicate field dispatches.
   - Rate limiter flags users submitting $>3$ sightings within 5 minutes.
6. **Location-Based Ranger Dispatch & Incident Response Lifecycle:**
   - Candidate rangers are algorithmically matched within a 30 km Haversine radius based on availability (`AVAILABLE`) and approved status.
   - Formal response milestone state machine: `ASSIGNED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `ON_THE_WAY` $\rightarrow$ `AT_LOCATION` $\rightarrow$ `OUTCOME_SUBMITTED`.
   - Rangers are strictly prevented from self-completing incidents. Incident resolution requires Authority review of field notes and evidence photos.
7. **Geospatial Analytics & DBSCAN Risk Zones:**
   - Dynamic scikit-learn DBSCAN clustering using spherical Haversine distance in radians (`algorithm='ball_tree'`).
   - Community Risk Zones implement a 4-state lifecycle: Red ($\ge 3$ active incidents), Orange (1–2 active), Yellow (resolved cooldown, 24h), and Green (safe retention, 48h).
   - Authority Operations Map displays real-time markers with color-coded dispatch states and 30-second live polling.
8. **Emergency Support & Hospital Directory:**
   - Haversine geodesic distance sorting from citizen GPS coordinates to regional hospitals.
   - Displays real-time anti-venom vial inventories, 24/7 operating hours, ICU readiness, and emergency hotlines (`108`, `1926`).
   - Emergency SOS distress broadcast API with 2-minute geographic deduplication throttling.

---

## 2. Claims Requiring User Confirmation

1. **Project Guide Information:**
   - Mentioned in existing documentation as "Prof. Natheera Beevi S."
   - *Action Required:* Confirm official academic designation (e.g., Assistant Professor, Associate Professor, Head of Department).
2. **Team Member Contribution Split:**
   - Candidates: Nehmal N (25MCA043) and Nidhish Chandran (25MCA044).
   - In Git commit history, all human commits were authored under `Nidhish Chandran <nidhishchandran24@gmail.com>`.
   - *Action Required:* Formally confirm the division of responsibilities and contribution percentage between Nehmal N and Nidhish Chandran for the academic report.
3. **Report Presentation Format & Guidelines:**
   - *Action Required:* Confirm the required departmental formatting standards, citation style (IEEE / ACM), and maximum page limit.

---

## 3. Metrics That Must NOT Be Claimed

To preserve academic integrity, the following claims must **never** be included in the MCA project report:

1. **DO NOT claim that the active web application runs a YOLOv8 detection model:**
   - The production inference pipeline in `ai/services.py` uses MobileNetV2 and EfficientNetB0. `ai/models/best.pt` is an archived Colab training artifact that is never executed by Django views.
2. **DO NOT claim 15-class species classification in the active application:**
   - The deployed model `venomwatch_cnn2_final.keras` is a binary classifier ($p \ge 0.50$ Venomous, $p < 0.50$ Non-Venomous). It does not predict granular taxonomic species names.
3. **DO NOT claim epoch-wise loss/accuracy curves for the Keras models:**
   - The repository contains only the compiled `.keras` weight files. Historical training history CSVs or TensorBoard logs for `venomwatch_cnn2_final.keras` and `venom_watch_snakebite_efficientnetb0.keras` are not present in source control.
4. **DO NOT claim external cellular SMS delivery:**
   - The Emergency SOS system logs distress records to the database and feeds Authority dashboards, but does not send physical cellular SMS messages via external telecom gateways.
5. **DO NOT claim live IoT/sensor hospital inventory syncing:**
   - Hospital vial stocks are administratively maintained through Django forms; they are not connected to hospital RFID/ERP APIs.

---

## 4. Screenshot Topics That Must Be Captured Manually

Per the audit guidelines, no synthetic screenshots have been generated. The following screens must be captured manually from the running application for inclusion in the final MCA report:

1. **Citizen Portal:**
   - Sighting Submission Page (`/reports/create/`) showing image upload and coordinate fields.
   - Sighting Detail Page (`/reports/<id>/`) showing the permanent report reference (`VW-0012`), AI venom prediction badge, and status card.
   - Wound Image Checker (`/ai/wound-check/`) showing upload card, uncertainty note, and medical disclaimer.
   - Emergency Hospital Directory (`/emergency/`) showing distance-sorted facilities and vial count badges.
   - Public Community Risk Zones Map (`/reports/risk-zones/`) showing colored circular risk sectors.
2. **Authority Console:**
   - Surveillance Dashboard (`/dashboard/authority/`) showing active statistics, unassigned counts, and radar.
   - Authority Operations Map (`/reports/map/`) showing colored incident markers and candidate ranger dispatch drawer.
   - Incident Review & Verification Modal (`/reports/<id>/`) showing verification controls and ranger assignment interface.
   - Outcome Verification Modal showing ranger notes, evidence photo, and Approve/Reject buttons.
   - Emergency SOS Feed (`/emergency/api/sos/feed/`) showing distress incident monitoring.
3. **Forest Ranger Mobile Console:**
   - Ranger Landing Page (`/ranger/`) showing new, active, and completed assignment counts.
   - Assignment Detail Page (`/ranger/assignments/<id>/`) showing incident coordinates, observer notes, and linear action button (`ACCEPT` $\rightarrow$ `ON_THE_WAY` $\rightarrow$ `AT_LOCATION`).
   - Outcome Submission Form showing outcome selector (`SNAKE_CAPTURED`), field notes, and photo upload.
4. **Platform Administrator Console:**
   - Admin Dashboard (`/accounts/admin/dashboard/`) showing pending applications and account counts.
   - Application Review Queue (`/accounts/provision/?tab=applications`) showing pending applicant cards.
   - Document Inspection Modal showing official verification credential PDF/JPG.
   - Operational Accounts Roster (`/accounts/provision/?tab=roster`) showing role filters and account status buttons.
   - Hospital Management Console (`/emergency/manage/`) showing hospital CRUD table.
