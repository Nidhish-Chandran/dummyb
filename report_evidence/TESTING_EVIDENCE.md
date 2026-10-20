# Testing Evidence Report — VenomWatch

**Project Title:** VenomWatch — AI-Assisted Snake Sighting Monitoring and Community Safety Platform  
**Document Reference:** MCA-VW-2026-TEST-EVIDENCE  
**Execution Timestamp:** October 20, 2026 (11:55:27 – 12:00:17 IST)  
**Execution Environment:** Windows 11, Python 3.11, Django 5.2.17, SQLite 3 (Isolated Test DB), PyTorch 2.14.0+cpu, TensorFlow 2.21.0, Keras 3.15.0  
**Test Runner:** `django.test.runner.DiscoverRunner`  

---

## 1. Live Automated Test Execution Summary

The entire automated test suite was executed directly against the project using the standard Django CLI:

### Command 1: Django System Health Check
```bash
python manage.py check
```
- **Exit Code:** `0`
- **Standard Output:**
  ```text
  System check identified no issues (0 silenced).
  ```

### Command 2: Full Test Suite Execution
```bash
python manage.py test
```
- **Execution Command:** `python manage.py test`
- **Exit Code:** `0`
- **Execution Duration:** 280.472 seconds (~4.67 minutes)
- **Total Tests Discovered:** 85
- **Total Tests Executed:** 85
- **Passed:** **85**
- **Failed:** **0**
- **Errors:** **0**
- **Skipped:** **0**
- **Status:** **OK (100% Pass Rate)**

#### Verbatim Execution Console Output
```text
Creating test database for alias 'default'...
.....................................................................................
----------------------------------------------------------------------
Ran 85 tests in 280.472s

OK
Destroying test database for alias 'default'...
Found 85 test(s).
System check identified no issues (0 silenced).
```

---

## 2. Test Inventory by Application Module

The 85 executed tests are partitioned across 8 `django.test.TestCase` classes in 4 core applications:

```
+------------------------------------------------------------------------------------+
|                             VENOMWATCH TEST SUITE (85 TESTS)                        |
+------------------------------------------------------------------------------------+
| 1. accounts App: 33 Tests                                                          |
|    - AccountsWorkflowTestCase (15 tests)                                           |
|    - AdminApplicationWorkflowTestCase (18 tests)                                   |
|                                                                                    |
| 2. reports App: 24 Tests                                                           |
|    - AuthorityMapAndImageMappingTestCase (9 tests)                                 |
|    - ReportingAndRiskZoneLifecycleTestCase (5 tests)                                |
|    - VenomWatchAccessControlTestCase (10 tests)                                    |
|                                                                                    |
| 3. emergency App: 24 Tests                                                         |
|    - AdminHospitalManagementTestCase (19 tests)                                    |
|    - EmergencySOSTestCase (5 tests)                                                |
|                                                                                    |
| 4. ranger App: 4 Tests                                                             |
|    - RangerWorkflowAndSecurityTestCase (4 tests)                                   |
+------------------------------------------------------------------------------------+
```

---

## 3. Detailed Test Inventory & Assertion Scenarios

### 3.1 `accounts` Module (33 Tests)

#### A. `AccountsWorkflowTestCase` (15 Tests)
1. `test_citizen_registration_always_assigns_citizen_role`: Verifies that self-registration strictly forces `ROLE_CITIZEN`, blocking privilege escalation attempts.
2. `test_admin_separate_provision_forms_for_authority_and_ranger`: Validates distinct admin provisioning workflows and form field requirements.
3. `test_admin_account_edit_view_and_password_reset`: Verifies admin read-only account detail inspection and password update workflows.
4. `test_admin_self_deactivation_prevention`: Ensures an administrator cannot deactivate their own active administrative session.
5. `test_admin_profile_update_and_password_change`: Verifies admin profile detail updates and secure password change.
6. `test_non_admin_cannot_access_provisioning`: Enforces HTTP 403 on `/accounts/provision/` for citizen and ranger roles.
7. `test_session_logout`: Confirms full session flushing and redirection to login on user logout.
8. `test_admin_dashboard_metrics_and_permissions`: Tests metric calculation (pending applications, active accounts) on `/accounts/admin/dashboard/`.
9. `test_user_profile_effective_role`: Validates superuser elevation logic (`is_superuser` $\implies$ `admin`).
10. `test_notification_creation_and_filtering`: Tests user notification delivery and recipient isolation.
11. `test_notification_mark_as_read_api`: Verifies AJAX read status update endpoint.
12. `test_notification_mark_all_as_read`: Tests batch mark-as-read operation.
13. `test_audit_log_record_helper`: Validates creation of immutable audit ledger entries.
14. `test_account_suspension_blocks_login`: Verifies suspended accounts are denied login access.
15. `test_user_profile_operational_status`: Validates the `is_operational` property across roles and approval states.

#### B. `AdminApplicationWorkflowTestCase` (18 Tests)
16. `test_admin_inspect_document_success`: Confirms admin can safely inspect uploaded verification PDF/image files.
17. `test_application_without_document_returns_404`: Validates defensive 404 response if an application has no document attached.
18. `test_approve_eligible_application_end_to_end`: Tests atomic approval: activates user (`is_active=True`), sets role, logs audit entry.
19. `test_direct_approve_reject_endpoints_disallow_get`: Verifies that GET requests to approval/rejection endpoints are rejected (HTTP 405).
20. `test_direct_approve_reject_unauthorized_blocked`: Enforces HTTP 403 on non-admin approval attempts.
21. `test_duplicate_approval_and_rejection_handled_safely`: Safeguards against modifying already approved or rejected applications.
22. `test_get_request_cannot_modify_application_state`: Ensures GET requests cannot trigger state mutations.
23. `test_nonexistent_application_document_returns_404`: Tests error handling when requesting an invalid application ID.
24. `test_pending_application_counts_update_correctly`: Verifies counter increments/decrements on approval.
25. `test_reject_eligible_application_end_to_end`: Tests rejection: records mandatory remarks and leaves account inactive.
26. `test_request_additional_information_workflow`: Tests the `STATUS_NEEDS_INFO` application state transition.
27. `test_unauthorized_access_to_document_is_blocked`: Confirms direct `/media/verification_docs/` access is blocked (HTTP 403).
28. `test_admin_application_detail_view`: Tests application detail view rendering.
29. `test_admin_application_approve_direct_endpoint`: Tests POST approval action handling.
30. `test_admin_application_reject_direct_endpoint`: Tests POST rejection action handling.
31. `test_application_filter_by_status`: Tests application filtering by status query parameters.
32. `test_application_search_by_name_and_role`: Validates search filtering on applicant roster.
33. `test_applicant_notification_on_decision`: Verifies in-app notification dispatch to applicant upon approval/rejection.

---

### 3.2 `reports` Module (24 Tests)

#### A. `AuthorityMapAndImageMappingTestCase` (9 Tests)
34. `test_01_citizen_report_saved_correctly`: Confirms sighting record persistence, coordinates, and image binding.
35. `test_02_authorized_authority_endpoint_returns_new_report`: Map API returns newly created sighting incident.
36. `test_03_pending_verification_reports_not_excluded`: `PENDING` reports appear on the authority map with warning pins.
37. `test_04_unauthorized_users_blocked_from_authority_endpoints`: Citizens receive HTTP 403 on `/reports/map/`.
38. `test_05_two_reports_distinct_images_never_crossed`: Proves image URLs are strictly isolated to their own records.
39. `test_06_confidence_normalization_semantics`: Tests `normalize_confidence_percentage` against $[0.0, 1.0]$, percentages, and uncalibrated scores.
40. `test_07_invalid_coordinates_handled_safely`: Confirms invalid coordinates ($(0,0)$, out-of-bounds) are excluded from map JSON.
41. `test_08_assignment_and_status_changes_update_map`: Verifies that dispatch status updates reflect on map marker states.
42. `test_09_missing_image_handled_safely`: Validates graceful fallback when a report has no image file.

#### B. `ReportingAndRiskZoneLifecycleTestCase` (5 Tests)
43. `test_citizen_sightings_page_removes_rescue_status_and_filter`: Verifies clean citizen sighting list interface.
44. `test_report_numbering_and_reference_per_citizen`: Validates report reference formatting (`VW-0001`).
45. `test_risk_zone_lifecycle_and_distinct_incident_counting`: Tests 4-state lifecycle (Red, Orange, Yellow, Green) and incident counting.
46. `test_risk_zones_api_endpoint`: Validates JSON schema returned by `/reports/api/risk-zones/`.
47. `test_sighting_form_coordinate_validation`: Tests boundary checks on latitude and longitude in forms.

#### C. `VenomWatchAccessControlTestCase` (10 Tests)
48. `test_authority_access_control_allowed`: Confirms authorized officers can access surveillance consoles.
49. `test_citizen_access_control_denied`: Confirms citizens are blocked from operational authority views.
50. `test_citizen_sees_only_own_reports_in_list`: Enforces isolation of citizen report views (`user=request.user`).
51. `test_dbscan_clustering`: Tests DBSCAN grouping of active reports using Haversine metric in radians.
52. `test_duplicate_detection_does_not_merge_resolved_incidents`: Confirms resolved sightings are not merged as active duplicate parents.
53. `test_duplicate_detection_multi_signal_scoring`: Validates distance ($\le 500$m), time ($\le 6$h), and species score calculation.
54. `test_ranger_assignment_and_authority_review_lifecycle`: Tests end-to-end 6-step dispatch and outcome review workflow.
55. `test_ranger_object_level_security`: Confirms rangers cannot view or mutate other rangers' assignments.
56. `test_sighting_properties`: Tests `is_venomous` property and 48-hour active window logic.
57. `test_authority_reassignment_cancels_previous_active_assignment`: Confirms reassigning a report cancels previous active assignment.

---

### 3.3 `emergency` Module (24 Tests)

#### A. `AdminHospitalManagementTestCase` (19 Tests)
58. `test_admin_can_access_and_add_hospital`: Admin adds hospital record with anti-venom vial counts and ICU status.
59. `test_admin_delete_hospital`: Tests facility deletion via POST confirmation.
60. `test_admin_edit_hospital`: Validates facility detail and anti-venom stock updates.
61. `test_assistance_view_empty_database_no_fake_records`: Confirms zero-state rendering without fake/dummy data.
62. `test_assistance_view_safe_missing_coordinates`: Validates fallback sorting when user coordinates are missing.
63. `test_assistance_view_uses_authority_hospitals_and_sorts_nearest_first`: Tests nearest-first sorting via Haversine distance.
64. `test_duplicate_hospital_rejected`: Confirms duplicate facility names within the same district are rejected.
65. `test_hospital_management_permission_denied_for_non_admins`: Non-admins receive HTTP 403 on `/emergency/manage/`.
66. `test_invalid_coordinates_rejected`: Tests coordinate boundary validation on hospital forms.
67. `test_admin_hospital_list_view_renders_correctly`: Validates management roster rendering.
68. `test_admin_hospital_create_form_validation`: Tests hospital creation form field validation.
69. `test_admin_hospital_edit_form_validation`: Tests hospital edit form validation.
70. `test_admin_hospital_delete_modal`: Tests deletion confirmation dialog.
71. `test_hospital_anti_venom_stock_vials_validation`: Ensures negative vial counts are rejected.
72. `test_hospital_icu_flag_toggle`: Tests ICU availability boolean toggling.
73. `test_hospital_emergency_department_flag`: Tests emergency department boolean flag.
74. `test_hospital_notes_storage`: Tests species-specific anti-venom stock notes persistence.
75. `test_hospital_district_filtering`: Tests hospital directory filtering by administrative district.
76. `test_hospital_operating_hours_display`: Tests 24/7 emergency care operating hours display.

#### B. `EmergencySOSTestCase` (5 Tests)
77. `test_hospital_distance_calculation`: Mathematical precision test of Haversine distance against known benchmarks.
78. `test_sos_authority_feed_and_acknowledgement`: Authority surveillance feed and incident acknowledgement.
79. `test_sos_duplicate_throttling`: Validates 2-minute geographic deduplication throttling on distress signals.
80. `test_sos_security_denied_for_citizen`: Citizens denied access to the Authority emergency distress operations feed.
81. `test_sos_trigger_persists_event`: Emergency SOS signal persisted to database with coordinates and callback phone.

---

### 3.4 `ranger` Module (4 Tests)

#### `RangerWorkflowAndSecurityTestCase` (4 Tests)
82. `test_complete_field_response_and_authority_verification_lifecycle`: Validates complete response lifecycle (`ASSIGNED` $\rightarrow$ `ACCEPTED` $\rightarrow$ `ON_THE_WAY` $\rightarrow$ `AT_LOCATION` $\rightarrow$ `OUTCOME_SUBMITTED` $\rightarrow$ Authority `APPROVED`).
83. `test_eligible_rangers_dispatch_recommendation_without_dummy_data`: Validates location-based ranger candidate matching ($\le 30$ km).
84. `test_ranger_assignment_isolation_and_acceptance`: Tests assignment privacy and status transition to `ACCEPTED`.
85. `test_suspended_ranger_blocked_from_protected_operations`: Confirms suspended rangers are excluded from dispatch eligibility.

---

## 4. Static Code Inspection vs. Live Execution Distinction

- **Tests Executed Live in This Audit:** **85 out of 85 tests** were executed synchronously via `python manage.py test`. All 85 passed with exit code 0.
- **Tested Modules:** `accounts`, `reports`, `emergency`, `ranger`.
- **Untested / Manually Verified Subsystems:**
  - Real-time client-side WebSocket/AJAX map polling interval (tested in-browser via Playwright Chromium subagent recorded to `.webp` artifacts).
  - External cellular SMS gateway delivery (not tested because no external SMS service is integrated in code).
  - Production WSGI/Nginx load handling (tested in single-process development mode).
