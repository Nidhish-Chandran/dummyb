# Database Audit Report — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-DB-AUDIT  
**Audit Date:** October 20, 2026  
**Auditor:** Senior Software Architect (Antigravity AI Pair Engineer)  
**Database Engine:** SQLite 3 (`d:\dummyb\db.sqlite3`) / Django ORM 5.2.x  

---

## 1. Overview of Data Architecture

VenomWatch utilizes Django's Object-Relational Mapping (ORM) to define and manage its database schema. The application persists core business entities including users, role extensions, credential applications, sighting encounters, field assignments, hospital inventories, and emergency distress events.

### Key Architectural Characteristics
- **Dynamic vs. Persisted Data:** Hotspot clusters and community risk zones are **not persisted** in database tables. They are calculated dynamically at runtime by `DBSCANHotspotService` using scikit-learn.
- **Relational Integrity:** Foreign keys enforce strict cascades or protection rules (`models.PROTECT`, `models.SET_NULL`, `models.CASCADE`).
- **Audit Trails:** Immutable logging is implemented via `accounts.AuditLog` capturing security and operational mutations.

---

## 2. Table and Entity Inventory

| Django Model | Underlying Database Table | App Module | Primary Key | Key Foreign Keys | Purpose / Responsibilities |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `User` | `auth_user` | `django.contrib.auth` | `id` (Auto) | None | Core user credentials, password hash, active status. |
| `UserProfile` | `accounts_userprofile` | `accounts` | `id` (Auto) | `user_id` (1:1 `auth_user`) | Role (`citizen`, `authority`, `ranger`, `admin`), operational base, availability, account status. |
| `AccountApplication` | `accounts_accountapplication` | `accounts` | `id` (Auto) | `user_id` (1:1 `auth_user`), `reviewed_by_id` (1:N `auth_user`) | Official Authority/Ranger registration requests, supporting document files. |
| `Notification` | `accounts_notification` | `accounts` | `id` (Auto) | `recipient_id` (1:N `auth_user`), `actor_id` (1:N `auth_user`) | In-app user notifications with 2-minute deduplication. |
| `AuditLog` | `accounts_auditlog` | `accounts` | `id` (Auto) | `actor_id` (1:N `auth_user`) | Immutable audit ledger for sensitive administrative and response actions. |
| `SightingReport` | `reports_sightingreport` | `reports` | `id` (Auto) | `user_id` (1:N `auth_user`), `verified_by_id` (1:N `auth_user`), `duplicate_of_id` (Self 1:N), `assigned_responder_id` (1:N `auth_user`) | Snake sighting encounters, photos, GPS coordinates, AI predictions, duplicate/spam flags. |
| `RangerAssignment` | `reports_rangerassignment` | `reports` | `id` (Auto) | `sighting_id` (1:N `reports_sightingreport`), `ranger_id` (1:N `auth_user`), `assigned_by_id` (1:N `auth_user`), `reviewed_by_id` (1:N `auth_user`) | Incident response dispatch milestones, ranger field notes, outcome evidence photo, Authority review. |
| `Hospital` | `emergency_hospital` | `emergency` | `id` (Auto) | `updated_by_id` (1:N `auth_user`) | Healthcare facilities, anti-venom vial counts, ICU capacity, operating hours, coordinates. |
| `EmergencySOSEvent` | `emergency_emergencysosevent` | `emergency` | `id` (Auto) | `user_id` (1:N `auth_user`), `acknowledged_by_id` (1:N `auth_user`) | Citizen distress broadcast events, location coordinates, callback phone number, status. |

---

## 3. Entity Relationships and Cardinalities

```
  ┌────────────────────────────────────────────────────────┐
  │                    auth_user                           │
  └───────┬────────────┬─────────────┬─────────────┬───────┘
          │ 1:1        │ 1:1         │ 1:N         │ 1:N
          ▼            ▼             ▼             ▼
  ┌──────────────┐ ┌──────────────┐┌──────────────┐┌──────────────┐
  │ UserProfile  │ │AccountApp.   ││ SightingRep. ││RangerAssign. │
  └──────────────┘ └──────────────┘└──────┬───────┘└──────┬───────┘
                                          │ 1:N           │
                                          └───────────────┘
                                           (One report can have
                                            multiple assignment
                                            attempts/history)

          auth_user                  auth_user
              │ 1:N                      │ 1:N
              ▼                          ▼
      ┌──────────────┐           ┌──────────────┐
      │EmergencySOS  │           │   Hospital   │
      └──────────────┘           └──────────────┘
```

### Relationship Breakdown:
1. **`auth_user` $\longleftrightarrow$ `accounts_userprofile` (1 : 1):**
   - Automatically created via post-save signal upon user creation.
   - Enforces unique user profiles.
2. **`auth_user` $\longleftrightarrow$ `accounts_accountapplication` (1 : 1):**
   - Links prospective Authority Officers and Forest Rangers to their official credential submission.
3. **`reports_sightingreport` $\longleftrightarrow$ `reports_sightingreport` (Self-referential 1 : N):**
   - `duplicate_of` links a suspected duplicate report to the canonical parent sighting report.
4. **`reports_sightingreport` $\longleftrightarrow$ `reports_rangerassignment` (1 : N):**
   - One incident report can have multiple assignment records over time (e.g., initial ranger declined or reassigned; final ranger completed).
5. **`auth_user` $\longleftrightarrow$ `reports_rangerassignment` (1 : N):**
   - `ranger`: Restricted via `limit_choices_to={'profile__role': 'ranger'}` and `on_delete=models.PROTECT`.
   - `assigned_by`: Authority user who issued dispatch.
   - `reviewed_by`: Authority user who reviewed outcome notes and photo evidence.

---

## 4. Detailed Field Specifications

### 4.1 `accounts_userprofile`
- `role`: `CharField(max_length=20)`, choices: `citizen`, `ranger`, `authority`, `admin`. Default: `citizen`.
- `account_status`: `CharField(max_length=20)`, choices: `ACTIVE`, `SUSPENDED`, `BANNED`. Default: `ACTIVE`.
- `availability`: `CharField(max_length=10)`, choices: `AVAILABLE`, `BUSY`, `OFFLINE`. Default: `AVAILABLE`.
- `registered_location`: `CharField(max_length=150, null=True, blank=True)`.
- `latitude`, `longitude`: `FloatField(null=True, blank=True)` — operational base coordinates.
- `full_name`, `phone_number`, `organization`, `assigned_region`: Supporting demographic and agency fields.
- `suspension_reason`: `TextField(null=True, blank=True)`.

### 4.2 `reports_sightingreport`
- `status`: `CharField(max_length=20)`, choices: `PENDING`, `VERIFIED`, `REJECTED`, `RESOLVED`.
- `response_status`: `CharField(max_length=20)`, choices: `UNASSIGNED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`.
- `original_image`: `ImageField(upload_to='sightings/')`.
- `processed_image`: `ImageField(upload_to='processed_sightings/', null=True, blank=True)`.
- `latitude`, `longitude`: `FloatField` — encounter GPS coordinates.
- `location_name`: `CharField(max_length=255)` — textual landmark or district.
- `snake_detected`: `BooleanField(default=False)`.
- `snake_confidence`: `FloatField(null=True, blank=True)`.
- `venomous`: `BooleanField(null=True, blank=True)`.
- `venom_confidence`: `FloatField(null=True, blank=True)`.
- `species_predicted`: `CharField(max_length=150, null=True, blank=True)`.
- `venom_category`: `CharField(max_length=30)`, choices: `HIGHLY_VENOMOUS`, `VENOMOUS`, `NON_VENOMOUS`.
- `duplicate_flag`: `BooleanField(default=False)`.
- `duplicate_score`: `IntegerField(default=0)` ($0-100$).
- `duplicate_reason`: `CharField(max_length=255, null=True, blank=True)`.
- `spam_flag`: `BooleanField(default=False)`.
- `spam_reason`: `CharField(max_length=255, null=True, blank=True)`.

### 4.3 `reports_rangerassignment`
- `status`: `CharField(max_length=20)`, choices: `ASSIGNED`, `ACCEPTED`, `ON_THE_WAY`, `AT_LOCATION`, `OUTCOME_SUBMITTED`, `COMPLETED`, `DECLINED`, `CANCELLED`.
- `distance_km`: `FloatField(null=True, blank=True)` — Haversine distance from ranger base at assignment time.
- `outcome`: `CharField(max_length=30)`, choices: `SNAKE_CAPTURED`, `SNAKE_RELOCATED`, `SNAKE_ESCAPED`, `REFERRED_OTHER_TEAM`, `UNRESOLVED`, `REPORT_UNVERIFIED`, `OTHER`.
- `notes`: `TextField(null=True, blank=True)` — field notes captured by ranger.
- `outcome_image`: `ImageField(upload_to='assignment_outcomes/', null=True, blank=True)`.
- `review_decision`: `CharField(max_length=30)`, choices: `PENDING_REVIEW`, `APPROVED`, `REJECTED`, `CLARIFICATION_REQUESTED`.
- `review_notes`: `TextField(null=True, blank=True)` — Authority review remarks.

### 4.4 `emergency_hospital`
- `name`: `CharField(max_length=200)`.
- `phone_number`: `CharField(max_length=50)`.
- `address`: `CharField(max_length=255)`.
- `district`: `CharField(max_length=100)`.
- `latitude`, `longitude`: `FloatField`.
- `anti_venom_available`: `BooleanField(default=True)`.
- `anti_venom_stock_vials`: `IntegerField(default=50)`.
- `has_icu`: `BooleanField(default=True)`.
- `emergency_department`: `BooleanField(default=True)`.
- `anti_venom_notes`: `TextField(blank=True)`.

### 4.5 `emergency_emergencysosevent`
- `latitude`, `longitude`: `FloatField` — distress incident coordinates.
- `phone_number`: `CharField(max_length=50, null=True, blank=True)`.
- `location_name`: `CharField(max_length=255)`.
- `status`: `CharField(max_length=20)`, choices: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`.
- `emergency_type`: `CharField(max_length=50, default='SNAKEBITE_DISTRESS')`.

---

## 5. Model-to-Feature Mapping Matrix

| Platform Feature | Primary Models Read | Primary Models Written |
| :--- | :--- | :--- |
| **Citizen Registration** | None | `User`, `UserProfile` |
| **Official Role Application** | `User` | `AccountApplication` |
| **Application Approval/Rejection** | `AccountApplication`, `User` | `AccountApplication`, `User`, `UserProfile`, `AuditLog`, `Notification` |
| **Sighting Submission** | None | `SightingReport` |
| **Duplicate & Spam Scoring** | `SightingReport` (historical $\le 6$h) | `SightingReport` (`duplicate_flag`, `duplicate_score`, `duplicate_of`) |
| **Ranger Proximity Dispatch** | `SightingReport`, `UserProfile`, `AccountApplication` | `RangerAssignment`, `SightingReport` (`assigned_responder`, `response_status`), `Notification`, `AuditLog` |
| **Ranger Response Updates** | `RangerAssignment` | `RangerAssignment` (`status`, `notes`, `outcome`, `outcome_image`) |
| **Authority Outcome Review** | `RangerAssignment`, `SightingReport` | `RangerAssignment` (`status`, `review_decision`), `SightingReport` (`status`, `response_status`), `Notification`, `AuditLog` |
| **DBSCAN Risk Zones** | `SightingReport` (filtered non-duplicate) | *(Computed dynamically, no table written)* |
| **Hospital Distance Lookup** | `Hospital` | *(Computed dynamically via Haversine)* |
| **Hospital Registry Admin** | `Hospital` | `Hospital` |
| **Emergency SOS Trigger** | `EmergencySOSEvent` (throttling check) | `EmergencySOSEvent` |

---

## 6. Discrepancies Between Theoretical ER Diagrams & Actual Implementation

1. **No Hotspot / Cluster Table:**
   - Some conceptual presentations depict a `Hotspot` or `ClusterZone` database table. In reality, DBSCAN clustering is **purely dynamic** in `hotspots/services.py`, computed on the fly from `SightingReport` coordinates. No `hotspots_hotspot` table exists in the database.
2. **Unified User Table with Profile Extension:**
   - Instead of separate tables for `Citizen`, `Authority`, `Ranger`, and `Admin`, the system implements a single `UserProfile` entity extending standard `django.contrib.auth.models.User` with a `role` discriminator field.
3. **No Standalone Species Table:**
   - Species taxonomy is not maintained in a normalized relational lookup table. The predicted snake class (`'Venomous Snake'` or `'Non-Venomous Snake'`) is recorded directly in `SightingReport.species_predicted` and `venom_category`.
