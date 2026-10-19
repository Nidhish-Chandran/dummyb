# VenomWatch — Platform Admin Implementation Report

## Executive Summary

This report documents the architectural audit, implementation, security hardening, and end-to-end verification of the **Platform Admin Console** in the VenomWatch Django application.

The Platform Administrator's role is strictly focused and segregated from operational incident triage:
- **Provision & manage Authority and Ranger accounts**
- **Maintain registered hospitals and anti-venom vial inventories**
- **Manage administrative profile details and security credentials**

Administrative workflows **do not** duplicate or interfere with everyday operational incident management (citizen sighting review, duplicate merging, Ranger field dispatch, or evidence outcome approval), which remain exclusive to the Authority and Ranger consoles.

---

## 1. Existing Functionality Discovered & Architecture Audit

An audit of the existing codebase revealed:
1. **Accounts App (`accounts/`)**:
   - `UserProfile` model contained role definitions (`citizen`, `authority`, `ranger`, `admin`), operational locations, GPS coordinates, and availability status.
   - Public registration strictly forced citizen role, but an administrative provisioning interface was partially stubbed at `/accounts/provision/` without full editing, dedicated Authority/Ranger forms, or lockout protections.
   - Admin logins redirected to the default Django model admin (`/admin/`) rather than a focused platform dashboard.
2. **Emergency App (`emergency/`)**:
   - Contained `Hospital` model with basic fields (`name`, `phone_number`, `address`, `latitude`, `longitude`, `anti_venom_available`, `anti_venom_stock_vials`, `has_icu`, `operating_hours`) and Haversine distance calculation `distance_from()`.
   - Lacked district categorization, emergency department flags, detailed anti-venom clinical notes, stock verification timestamps, and updating admin tracking.
   - No dedicated frontend management interface existed for administrators to register, edit, filter, or delete hospital facilities.
3. **Permissions & Security**:
   - `@admin_required` was defined in `accounts/decorators.py` checking superuser or `profile.is_admin`, but was not yet applied to dedicated hospital management routes.

---

## 2. Pages and Routes Implemented or Repaired

| Module | URL Route | View Function | Permissions Enforced | Description |
|---|---|---|---|---|
| **Admin Dashboard** | `/accounts/dashboard/` | `admin_dashboard_view` | `@login_required`, `@admin_required` | Central responsive admin hub featuring 3 functional sections (Account Management, Hospital Management, Admin Profile) and real database statistics. |
| **Account Provisioning** | `/accounts/provision/` | `admin_provision_account_view` | `@login_required`, `@admin_required` | Provision Authority officers and Forest Rangers with tabbed forms, operational district/base fields, dispatch GPS coordinates, active account status toggles, and search filters. |
| **Edit Account** | `/accounts/manage/<id>/edit/` | `admin_account_edit_view` | `@login_required`, `@admin_required` | Modify existing officer details, operational base, dispatch coordinates, availability, active status, or initiate secure password resets. |
| **Hospital Registry** | `/emergency/manage/` | `admin_hospital_manage_view` | `@login_required`, `@admin_required` | View, search, filter, and register hospitals with anti-venom vial stocks, 24/7 ICU & Emergency Department availability, and GPS coordinates. |
| **Edit Hospital** | `/emergency/manage/<pk>/edit/` | `admin_hospital_edit_view` | `@login_required`, `@admin_required` | Update hospital contact numbers, coordinates, operating hours, anti-venom vial counts, notes, and audit timestamps. |
| **Delete Hospital** | `/emergency/manage/<pk>/delete/` | `admin_hospital_delete_view` | `@login_required`, `@admin_required`, `@require_POST` | Safely remove hospital facility records with confirmation prompts. |
| **Admin Profile** | `/accounts/profile/` | `profile_view` | `@login_required` | View account credentials, update personal contact details, and change administrator password via secure Django PBKDF2 hashing. |

---

## 3. Models and Migrations Changed

### Model Extension: `Hospital` (`emergency/models.py`)
Extended the `Hospital` model with essential operational reference fields:
- `district` (`CharField`, max_length=100, default=''): Administrative district/region.
- `emergency_department` (`BooleanField`, default=True): Dedicated 24/7 emergency unit availability.
- `anti_venom_notes` (`TextField`, blank=True, default=''): Clinical stock notes, anti-venom types (polyvalent/monovalent), storage conditions, or supplier info.
- `stock_last_updated` (`DateTimeField`, auto_now=True): Timestamp recording when stock was last verified.
- `updated_by` (`ForeignKey` to `auth.User`, null=True, blank=True): Audit pointer to the administrator who last modified the record.
- `created_at` (`DateTimeField`, auto_now_add=True, null=True)
- `updated_at` (`DateTimeField`, auto_now=True, null=True)

### Django Migrations:
- **Migration**: `emergency/migrations/0003_alter_hospital_options_hospital_anti_venom_notes_and_more.py`
  - Applied cleanly via `python manage.py migrate` without data loss or schema conflicts.

---

## 4. Account Management & Provisioning Behavior

1. **Add Authority Officer**:
   - Fields: Full name, username, email, phone number, temporary password, organization/department, assigned district/region.
   - Saves `User` and `UserProfile` with `role='authority'`.
   - Account can immediately log in via `/accounts/login/` and is redirected to `/authority/map/`.
2. **Add Forest Ranger**:
   - Fields: Full name, username, email, phone number, temporary password, organization, assigned region, registered operational base, latitude/longitude, and initial availability.
   - Saves `User` and `UserProfile` with `role='ranger'`.
   - Account logs in via `/accounts/login/` and lands on `/ranger/dashboard/`.
3. **Manage Existing Accounts**:
   - Filterable operational roster with search by name, username, email, region, or organization.
   - **Edit Account**: View and edit permitted officer details, base location, dispatch coordinates, availability, and active status.
   - **Password Reset**: Admin can set a temporary password without exposing hashes.
   - **Deactivation Protection**: Toggling active status disables login while strictly preserving all historical sightings, assignments, and audit logs.
   - **Lockout Safeguards**:
     - Admins cannot deactivate their own account.
     - The system prevents deactivating the last remaining active administrator account.

---

## 5. Hospital & Anti-Venom Data Behavior

1. **Add & Edit Facilities**:
   - Validates coordinates: Latitude bounded to [-90.0, 90.0], Longitude bounded to [-180.0, 180.0].
   - Validates emergency phone numbers and hotlines.
   - **Duplicate Prevention**: Rejects duplicate facility submissions where another hospital with the exact same name already exists in the same district, or where another facility already exists at the exact GPS coordinates.
2. **Anti-Venom Stock Tracking**:
   - Maintains verified stock vial quantities and available/out-of-stock boolean flags.
   - Records `stock_last_updated` and `updated_by` on every save.
   - **Data Transparency**: UI explicitly communicates that stock levels are *manually maintained administrative records* based on periodic clinical updates, distinguishing them from live IoT telemetry.
3. **Integration with Operations**:
   - All registered hospitals and verified coordinates feed directly into the existing `Hospital.distance_from()` Haversine calculation used by `/emergency/` (public hospital locator) and Authority logistics.

---

## 6. Registration, Authentication, & Permission Checks

1. **Role Separation**:
   - Public registration (`/accounts/register/`) forces `role='citizen'`. Injected role values are rejected by server-side validation in `UserRegistrationForm.clean_role()`.
   - Authority and Ranger accounts can only be created by an authorized administrator through `/accounts/provision/`.
2. **Server-Side Authorization**:
   - All admin endpoints (`/accounts/dashboard/`, `/accounts/provision/`, `/accounts/manage/<id>/edit/`, `/emergency/manage/`, `/emergency/manage/<pk>/edit/`, `/emergency/manage/<pk>/delete/`) enforce `@admin_required`.
   - Citizens, Authority officers, and Rangers attempting direct URL access receive `HTTP 403 Forbidden`.
   - Session logout completely flushes session storage and redirects to login.

---

## 7. Testing & Verification Results

### Automated Test Suite:
Run via `python manage.py test`:

```
Creating test database for alias 'default'...
...............................
----------------------------------------------------------------------
Ran 31 tests in 69.282s

OK
Destroying test database for alias 'default'...
Found 31 test(s).
System check identified no issues (0 silenced).
```

### Verified Test Cases:
1. `test_admin_dashboard_metrics_and_permissions`: Admin lands on dashboard with real metrics; non-admins receive 403.
2. `test_admin_separate_provision_forms_for_authority_and_ranger`: Both forms validate and persist accounts with role-specific profiles.
3. `test_admin_account_edit_view_and_password_reset`: Officer profile, coordinates, and password reset verified; user logs in with new password.
4. `test_admin_self_deactivation_prevention`: Admin cannot deactivate their own active account.
5. `test_admin_profile_update_and_password_change`: Admin updates email/name and changes password via Django's `PasswordChangeForm`.
6. `test_hospital_management_permission_denied_for_non_admins`: Citizens, Authority, and Rangers receive 403 on `/emergency/manage/`.
7. `test_admin_can_access_and_add_hospital`: New hospital registered with district, ICU, ED, and vials; audit stamps set.
8. `test_duplicate_hospital_rejected`: Duplicate hospital name & district rejected with validation message.
9. `test_invalid_coordinates_rejected`: Out-of-bounds latitude/longitude rejected.
10. `test_admin_edit_hospital`: Updating vial count and notes succeeds and records last-updated timestamp.
11. `test_admin_delete_hospital`: Removing hospital record succeeds with safe POST confirmation.
12. `test_citizen_registration_always_assigns_citizen_role`: Role escalation injection rejected.
13. `test_hospital_distance_calculation`: Haversine formula calculates accurate distances for emergency routing.

### Live Browser Subagent Verification:
- Automated browser session logged into `http://127.0.0.1:8000/accounts/login/` as `admin_demo`.
- Verified automatic redirect to `/accounts/dashboard/`.
- Captured screenshot of the 3-section dashboard hub.
- Filled and submitted the "Add Hospital" form for *Idukki Mountain Toxicology & Envenomation Center* with 65 vials.
- Verified appearance in registered hospital directory.
- Clicked "Edit", updated stock to 70 vials, and saved successfully.
- Verified operational roster and "Edit" buttons on `/accounts/provision/`.
- Verified profile and password change forms on `/accounts/profile/`.
- Recorded browser session saved to artifacts directory.

---

## 8. Remaining Limitations and External Integrations

1. **Hospital Inventory Real-time Integration**:
   - Hospital anti-venom vial quantities are maintained through administrative data entry. Integration with external hospital management systems (HL7/FHIR or State Health Portal APIs) would be needed for automated real-time inventory synchronization.
2. **SMS / Email Gateway**:
   - Password reset and credential notification presently rely on administrator communication or standard Django email backend. Configuring an external SMS/SMTP provider (e.g., Twilio or Amazon SES) is recommended for production deployment.
