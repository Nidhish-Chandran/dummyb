# Audit Commands Executed and Verification Results — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-CMD-LOG  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  
**Execution Environment:** Windows 11, Python 3.11, Django 5.2.17, SQLite 3  

---

## 1. Safety Protocol and Execution Philosophy

In accordance with the audit guidelines:
- **No Mutative Commands Executed:** No migrations were created or applied (`makemigrations`/`migrate`), no models were retrained, no application code was edited, and no database records in `db.sqlite3` were altered or deleted.
- **Isolated Testing Database:** The test runner `python manage.py test` automatically constructed an isolated, temporary test database (`test_db.sqlite3`) in memory/disk and cleanly destroyed it upon completion, leaving the active production database untouched.
- **External Integration Safeguards:** No external cellular SMS messages were sent, no external hospitals were contacted, and no real-world emergency responders were dispatched.

---

## 2. Inventory of Executed Commands and Verbatim Results

### Command 1: Django System Health Check
- **Command:** `python manage.py check`
- **Execution Working Directory:** `d:\dummyb`
- **Timestamp:** October 20, 2026, 11:55:15 IST
- **Purpose:** Validate Django configuration, application registry, URL routing syntax, model definitions, and system integrity.
- **Exit Code:** `0`
- **Verbatim Output:**
  ```text
  System check identified no issues (0 silenced).
  ```

---

### Command 2: Django Automated Test Suite Execution
- **Command:** `python manage.py test`
- **Execution Working Directory:** `d:\dummyb`
- **Timestamp:** October 20, 2026, 11:55:27 – 12:00:17 IST
- **Duration:** 280.472 seconds (~4.67 minutes)
- **Purpose:** Execute all unit tests, integration tests, security access controls, and workflow verifications across `accounts`, `reports`, `emergency`, and `ranger`.
- **Exit Code:** `0`
- **Verbatim Output:**
  ```text
  Creating test database for alias 'default'...
  .....................................................................................
  ----------------------------------------------------------------------
  Ran 85 tests in 280.472s

  OK
  Destroying test database for alias 'default'...
  Found 85 test(s).
  System check identified no issues (0 silenced).
  Current hospitals in database: 0
    + Added: Government Medical College Hospital, Kollam (Kollam)
    + Added: District Hospital Kollam (Kollam)
    + Added: Taluk Headquarters Hospital, Kottarakkara (Kollam)
    + Added: Taluk Headquarters Hospital, Punalur (Kollam)
    + Added: Taluk Headquarters Hospital, Sasthamkotta (Kollam)
    + Added: Bishop Benziger Hospital (Kollam)
    + Added: N.S. Memorial Institute of Medical Sciences (Kollam)
    + Added: Travancore Medicity Medical College Hospital (Kollam)
    + Added: Government Medical College Hospital, Thiruvananthapuram (Thiruvananthapuram)
    + Added: General Hospital, Pathanamthitta (Pathanamthitta)

  Hospital seeding complete: 10 new facilities added, 0 already existed. Total database records: 10.
  ```

---

### Command 3: Installed Python Package Environment Inspection
- **Command:** `python -m pip list`
- **Execution Working Directory:** `d:\dummyb`
- **Timestamp:** October 20, 2026, 11:56:42 IST
- **Purpose:** Audit installed packages and verify dependency versions against requirements.
- **Exit Code:** `0`
- **Key Package Versions Observed:**
  - `Django`: 5.2.17
  - `djangorestframework`: 3.18.0
  - `tensorflow`: 2.21.0
  - `keras`: 3.15.0
  - `torch`: 2.14.0
  - `torchvision`: 0.29.0
  - `ultralytics`: 8.4.146
  - `scikit-learn`: 1.5.2
  - `scipy`: 1.14.1
  - `numpy`: 2.2.6
  - `pandas`: 3.0.6
  - `pillow`: 10.2.0

---

### Command 4: Git Commit History Audit
- **Command:** `git log -n 15 --format="%h | %an <%ae> | %ad | %s"`
- **Execution Working Directory:** `d:\dummyb`
- **Timestamp:** October 20, 2026, 11:56:13 IST
- **Purpose:** Trace commit provenance, team author identities, and project chronology.
- **Exit Code:** `0`
- **Output:** Verified that all recent human commits were authored by `Nidhish Chandran <nidhishchandran24@gmail.com>`.

---

### Command 5: Unique Git Author Audit
- **Command:** `git log --format="%an <%ae>" | sort -u`
- **Execution Working Directory:** `d:\dummyb`
- **Timestamp:** October 20, 2026, 11:56:19 IST
- **Purpose:** Confirm whether any separate commit credentials existed for co-author Nehmal N.
- **Exit Code:** `0`
- **Output:** Identified only `Nidhish Chandran` and `qwen.ai[bot]` in Git author records.

---

## 3. Explicit Inventory of Commands NOT Executed

The following operations were explicitly evaluated and rejected to maintain the strict read-only safety protocol:

1. **`python manage.py makemigrations` / `python manage.py migrate`:**
   - *Reason for Omission:* The database schema is fully aligned with models; running migration generation or application could alter production tables or create untracked migration files.
2. **`python manage.py createsuperuser` / `changepassword`:**
   - *Reason for Omission:* Would mutate authenticated user credentials in `db.sqlite3`.
3. **`pip install` / `pip uninstall`:**
   - *Reason for Omission:* Package installation could alter the host environment.
4. **Model Retraining Scripts (`train.py` / Colab notebooks):**
   - *Reason for Omission:* Retraining models would overwrite established `.keras` model weights and create speculative benchmarks.
5. **Direct SQL Data Mutation (`sqlite3 db.sqlite3 "UPDATE..."`):**
   - *Reason for Omission:* Direct database writes bypass Django model validation and violate the non-destructive audit mandate.
6. **`python seed_demo_data.py`:**
   - *Reason for Omission:* Script is permanently disabled with early return to protect genuine database records from synthetic test data.
