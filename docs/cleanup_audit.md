# VenomWatch — Conservative Project Cleanup & Dead-Weight Audit Report

**Date of Execution:** October 19, 2026  
**Project:** VenomWatch (Django Snakebite Surveillance, AI Identification & Rapid Response Platform)  
**Location:** `d:\dummyb`  
**Git Base Commit:** `master` @ `305e60ab` (*"Checkpoint before conservative project cleanup"*)  
**Database Engine:** SQLite3 (`d:\dummyb\db.sqlite3`)  
**Quarantine Location:** `C:\Users\User\.gemini\antigravity-ide\brain\17701716-aca4-4cb1-bfd1-44017e05ae90\quarantine\`

---

## 1. Executive Summary & Principles

This cleanup was executed strictly under the **Conservative Project Cleanup** mandate. The primary imperative was the absolute preservation of project integrity, ensuring zero risk to Django applications, AI inference models, user accounts, database schemas, GIS mapping, or academic evaluation evidence.

### Core Principles Upheld
1. **Preserve full functionality:** Shared authentication, Citizen sighting submission, Ranger dispatch/evidence, Authority live map & risk zones, Emergency SOS/hospitals, AI pipeline inference, and Admin provisioning remain 100% operational.
2. **Zero accidental data loss:** No database records, migrations, seeded accounts, or uploaded media were deleted or altered.
3. **Quarantine-first policy:** Approved disposable candidates were not permanently destroyed. Instead, they were moved into an isolated external quarantine directory outside the application package, establishing an immediate, lossless rollback mechanism.
4. **Deliberate retention over deletion:** Questionable, duplicate, or research-relevant files (including user pre-cleanup backups and YOLOv8 research weights) were deliberately retained or marked for manual review.

---

## 2. Before-and-After Metrics

| Metric | Before Cleanup | After Cleanup | Change / Delta |
|---|---|---|---|
| **Total Project Files (excl. `.git`)** | 753 files | 722 files* | -31 files net (-156 quarantined caches + test artifacts) |
| **Quarantined Files** | 0 files | 157 files (incl. manifest) | +157 files in external quarantine |
| **Total Disk Space** | 113.04 MB (118,531,786 B) | 112.87 MB (118,352,107 B) | -179.68 KB (~741.36 KB quarantined) |
| **Active Database (`db.sqlite3`)** | 290,816 bytes | 290,816 bytes | **0 bytes (Exact byte match, 100% intact)** |
| **User Profiles in Database** | 8 | 8 | **0 (Unchanged)** |
| **Sighting Reports in Database** | 5 | 5 | **0 (Unchanged)** |
| **Ranger Assignments in Database** | 1 | 1 | **0 (Unchanged)** |
| **Notifications in Database** | 23 | 23 | **0 (Unchanged)** |
| **Audit Logs in Database** | 20 | 20 | **0 (Unchanged)** |
| **AI Snake Detection Model** | `venomwatch_cnn2_final.keras` (23.68 MB) | `venomwatch_cnn2_final.keras` (23.68 MB) | **Preserved 100%** |
| **AI Wound Screening Model** | `venom_watch_snakebite_efficientnetb0.keras` (35.35 MB) | `venom_watch_snakebite_efficientnetb0.keras` (35.35 MB) | **Preserved 100%** |
| **Django System Checks** | 0 issues | 0 issues | **Passed (`System check identified no issues`)** |
| **Unapplied Migrations Check** | `No changes detected` | `No changes detected` | **Passed (Schema in complete sync)** |
| **Automated Test Suite** | 74 / 74 tests passing | 74 / 74 tests passing | **Passed (0 failures, 0 errors, 100% pass)** |

*\*Note: Running the automated test suite generates mock test uploads in `media/` under Django's default test runner storage. These untracked files are strictly preserved in accordance with rule 2.C.*

---

## 3. Comprehensive File Inventory & Actions

### Category A: Safe Disposable Files (Quarantined)

| Path | Purpose | Evidence of Usage | Action Taken | Rationale & Safety Proof |
|---|---|---|---|---|
| `test_esri_tile_19.jpg` | Transient 2.5 KB tile test image. | 0 references across Python code, templates, static assets, tests, or documentation. | **Moved to Quarantine** | Safe: Isolated temporary artifact from past interactive testing. |
| `accounts/__pycache__/` | Bytecode cache (13 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `accounts/management/commands/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `accounts/migrations/__pycache__/` | Bytecode cache (6 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `ai/__pycache__/` | Bytecode cache (8 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `ai/migrations/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `dashboard/__pycache__/` | Bytecode cache (7 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `dashboard/migrations/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `emergency/__pycache__/` | Bytecode cache (8 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `emergency/migrations/__pycache__/` | Bytecode cache (4 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `hotspots/__pycache__/` | Bytecode cache (8 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `hotspots/migrations/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `ranger/__pycache__/` | Bytecode cache (6 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `ranger/migrations/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `reports/__pycache__/` | Bytecode cache (10 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `reports/management/__pycache__/` | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `reports/management/commands/__pycache__/` | Bytecode cache (2 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `reports/migrations/__pycache__/` | Bytecode cache (6 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `venomwatch/__pycache__/` | Bytecode cache (5 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |
| `__pycache__/` (root) | Bytecode cache (1 `.pyc`). | Compiled CPython bytecode. | **Moved to Quarantine** | Safe: Auto-regenerated dynamically upon execution. |

---

### Category B: Files Deliberately Retained Despite Apparent Redundancy

| Path | Purpose | Evidence & Context | Reason for Deliberate Retention |
|---|---|---|---|
| `db.sqlite3.backup_before_cleanup` | Developer backup of `db.sqlite3` (278.5 KB). | Created and committed by developer in commit `305e60ab` before starting cleanup. | **Retained:** Removing a developer's pre-cleanup safety snapshot during the cleanup operation directly contradicts the mandate of conservative preservation. |
| `media_backup_before_cleanup/` (63 files) | Developer backup of `media/` folder. | Created and committed in commit `305e60ab` as a standalone media backup. | **Retained:** Serves as a failsafe copy of uploaded media. Keeping it ensures zero accidental media loss. |
| `ai/models/venomwatch_cnn2_final.keras` | Exact byte-for-byte duplicate (23.68 MB) of root model. | Identical to root `venomwatch_cnn2_final.keras`. Referenced in `ai/services.py:276` as a fallback search location. | **Retained:** `ai/services.py` checks both root and `ai/models/`. Retaining both guarantees that regardless of current working directory or deployment paths, model loading never fails. |

---

### Category C: Artifacts Requiring Future Manual Review

| Path | Purpose | Evidence & Research Value | Status / Review Recommendation |
|---|---|---|---|
| `ai/models/best.pt` | YOLOv8 PyTorch model weights (3.00 MB). | Documented in `docs/project_evidence_report.md` with training loss curves and evaluation metrics for the MCA project dissertation. | **Retained for Review:** Not invoked in production runtime (which uses MobileNetV2), but essential for academic reproducibility, training provenance, and project defense evidence. |
| `seed_demo_data.py` | Standalone CLI database seeder (12.6 KB). | Referenced in `project_features.md` and `docs/project_evidence_report.md`. Distinct from the disabled management command. | **Retained for Review:** Provides an offline, reproducible script for regenerating standard evaluation scenarios and demo accounts. |

---

### Protected Category: Core Operational Assets (Untouched)

All items below were verified and remained completely untouched:
- **Core Configuration:** `manage.py`, `requirements.txt`, `.gitignore`, `venomwatch/settings.py`, `venomwatch/urls.py`, `venomwatch/wsgi.py`, `venomwatch/asgi.py`.
- **Application Logic:** All Python modules (`models.py`, `views.py`, `forms.py`, `urls.py`, `admin.py`, `apps.py`, `middleware.py`, `decorators.py`, `dispatch.py`, `services.py`, `tests.py`) across `accounts`, `ai`, `dashboard`, `emergency`, `hotspots`, `ranger`, and `reports`.
- **Database Migrations:** All migration files (0001–0005) across all apps.
- **Frontend Templates:** All 28 HTML templates in `templates/` across all roles.
- **Static Assets:** `static/css/style.css`, `static/js/main.js`, `static/img/snake_safety_hero.jpg`.
- **Live Database:** `db.sqlite3` (290,816 bytes).
- **Uploaded Media:** All user media in `media/` (`sightings/`, `wounds/`, `verification_docs/`, `assignment_outcomes/`, `processed_sightings/`, `processed_wounds/`, `test_suite/`).
- **Production AI Models:** `venomwatch_cnn2_final.keras` and `venom_watch_snakebite_efficientnetb0.keras`.
- **Project Documentation & Evidence:** All reports and evidence diagrams (`ADMIN_IMPLEMENTATION_REPORT.md`, `IMPLEMENTATION_REPORT.md`, `PROJECT_AUDIT.md`, `project_features.md`, `REQUIREMENTS_TRACEABILITY.md`, `TEST_REPORT.md`, `docs/project_evidence_report.md`, `docs/evidence/*`).

---

## 4. Verification Commands & Actual Results

Every check specified in Section 5 of the prompt was executed and recorded:

### Check 1: Django System Check
- **Command:** `python manage.py check`
- **Result:** **PASSED** (Exit Code 0)
- **Output:**
  ```text
  System check identified no issues (0 silenced).
  ```

### Check 2: Migrations Dry-Run Check
- **Command:** `python manage.py makemigrations --check --dry-run`
- **Result:** **PASSED** (Exit Code 0)
- **Output:**
  ```text
  No changes detected
  ```

### Check 3: Automated Test Suite Execution
- **Command:** `python manage.py test`
- **Result:** **PASSED** (Exit Code 0)
- **Output:**
  ```text
  Ran 74 tests in 253.329s
  OK
  Destroying test database for alias 'default'...
  Found 74 test(s).
  System check identified no issues (0 silenced).
  ```

### Check 4: Python Module Import Verification
- **Command:** Comprehensive programmatic import across all Django apps, middleware, views, decorators, and context processors.
- **Result:** **PASSED** (Exit Code 0)
- **Output:**
  ```text
  All Python modules imported successfully!
  ```

### Check 5: AI Model File & Runtime Inference Loading Check
- **Command:** Direct programmatic loading via `SnakeAIPipelineService.get_model()` and `SnakebiteScreeningService.get_model()`.
- **Result:** **PASSED** (Exit Code 0)
- **Output:**
  ```text
  [AI] Loading CNN venom classifier from: D:\dummyb\venomwatch_cnn2_final.keras
  [AI] Venom classifier loaded and cached in memory.
  Snake CNN Model loaded successfully: Sequential

  [Snakebite] Loading EfficientNetB0 model from: D:\dummyb\venom_watch_snakebite_efficientnetb0.keras
  [Snakebite] Model loaded successfully
  Wound EfficientNet Model loaded successfully: Functional
  ```

### Check 6: Database Integrity & Record Count Verification
- **Command:** Querying database counts directly from `db.sqlite3`.
- **Result:** **PASSED** (100% record preservation)
- **Counts:**
  - `User`: 8 (Unchanged)
  - `UserProfile`: 8 (Unchanged)
  - `AccountApplication`: 3 (Unchanged)
  - `Notification`: 23 (Unchanged)
  - `AuditLog`: 20 (Unchanged)
  - `SightingReport`: 5 (Unchanged)
  - `RangerAssignment`: 1 (Unchanged)
  - `Hospital`: 0 (Unchanged)
  - `EmergencySOSEvent`: 0 (Unchanged)

### Check 7: Static Assets & Templates Presence Check
- **Command:** File system scan for all 28 templates and static bundles.
- **Result:** **PASSED**
- **Counts:** `static/css/style.css` (43,377 B), `static/js/main.js` (10,887 B), `static/img/snake_safety_hero.jpg` (940,766 B), 28 HTML templates present.

### Check 8: Media & Uploaded Files Presence Check
- **Command:** Directory walk of `media/` subdirectories.
- **Result:** **PASSED**
- **Counts:** `media/sightings` (32), `media/processed_sightings` (5), `media/wounds` (21), `media/processed_wounds` (14), `media/verification_docs` (304), `media/assignment_outcomes` (15), `media/test_suite` (7).

---

## 5. Rollback Procedure

Because all moved items were relocated to an external quarantine directory rather than deleted, a complete, instantaneous rollback can be performed at any time.

### Rollback Steps

#### Option A: Automated Scripted Rollback
Run the following PowerShell command from the project root (`d:\dummyb`):
```powershell
python -c "
import os, shutil

quarantine_root = r'C:\Users\User\.gemini\antigravity-ide\brain\17701716-aca4-4cb1-bfd1-44017e05ae90\quarantine'
manifest_path = os.path.join(quarantine_root, 'quarantine_manifest.txt')

if os.path.exists(manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ' -> ' in line:
                rel_src, abs_dst = line.strip().split(' -> ')
                if os.path.exists(abs_dst):
                    os.makedirs(os.path.dirname(rel_src) if os.path.dirname(rel_src) else '.', exist_ok=True)
                    shutil.move(abs_dst, rel_src)
                    print(f'Restored: {rel_src}')
    print('Rollback complete.')
else:
    print('Manifest not found.')
"
```

#### Option B: Git Working-Tree Restoration
Since no Git commits were made during this operation and Git HEAD remains clean at `305e60ab`:
```powershell
git checkout -- .
```
*(Restores all tracked `.pyc` and `test_esri_tile_19.jpg` files directly from the checkpoint commit).*

---

## 6. Remaining Uncertainty & Risk Assessment

- **Overall Residual Risk:** **Negligible / Zero.**
- **Application Stability:** Verified by 74 passing automated tests, full module imports, clean `manage.py check`, and successful AI model loading.
- **Database Safety:** Zero records altered, active database byte count identical, schema dry-run confirms 0 pending migrations.
- **Future Recommendation:** Prior to final MCA packaging, the developer may manually inspect `ai/models/best.pt` (3.0 MB) and `media_backup_before_cleanup/` to decide whether to archive them into external storage or keep them for final presentation evidence.
