from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from reports.models import SightingReport, RangerAssignment
from hotspots.services import DBSCANHotspotService

class VenomWatchAccessControlTestCase(TestCase):
    def setUp(self):
        # Create Citizen User
        self.citizen = User.objects.create_user(username='john_citizen', password='password123')
        self.citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.citizen.profile.save()

        # Create Second Citizen User
        self.other_citizen = User.objects.create_user(username='other_citizen', password='password123')
        self.other_citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.other_citizen.profile.save()

        # Create Higher Authority User
        self.authority = User.objects.create_user(username='authority_officer', password='password123')
        self.authority.profile.role = UserProfile.ROLE_AUTHORITY
        self.authority.profile.save()

        # Create Citizen 1 Sighting Report
        self.citizen_report = SightingReport.objects.create(
            user=self.citizen,
            title="Citizen's Cobra Sighting",
            latitude=9.9312,
            longitude=76.2673,
            location_name='Kochi Sector 4',
            species_predicted='Indian Cobra (Naja naja)',
            venom_category=SightingReport.VENOM_HIGHLY,
            toxicity_level='CRITICAL',
            danger_score=95
        )

        # Create Other Citizen Sighting Report
        self.other_report = SightingReport.objects.create(
            user=self.other_citizen,
            title="Other Citizen's Viper Sighting",
            latitude=10.0420,
            longitude=76.3200,
            location_name='Kalamassery Industrial Area',
            species_predicted="Russell's Viper",
            venom_category=SightingReport.VENOM_HIGHLY,
            toxicity_level='CRITICAL',
            danger_score=98
        )

    def test_sighting_properties(self):
        self.assertTrue(self.citizen_report.is_venomous)
        self.assertTrue(self.citizen_report.is_active_48h)

    def test_dbscan_clustering(self):
        hotspot_data = DBSCANHotspotService.compute_hotspots(eps_km=1.0, min_samples=2, hours=48)
        self.assertEqual(hotspot_data['total_active_sightings'], 2)

    def test_citizen_access_control_denied(self):
        self.client.login(username='john_citizen', password='password123')

        # Citizen cannot access Authority Dashboard (403 Forbidden)
        response_dash = self.client.get('/authority/')
        self.assertEqual(response_dash.status_code, 403)

        # Citizen cannot access Hotspot Radar (403 Forbidden)
        response_hotspots = self.client.get('/hotspots/')
        self.assertEqual(response_hotspots.status_code, 403)

        # Citizen cannot access Hotspots GeoJSON API (403 Forbidden)
        response_api = self.client.get('/hotspots/api/clusters/')
        self.assertEqual(response_api.status_code, 403)

        # Citizen cannot view other citizen's report detail (403 Forbidden)
        response_detail_other = self.client.get(f'/reports/{self.other_report.pk}/')
        self.assertEqual(response_detail_other.status_code, 403)

        # Citizen CAN view their own report detail (200 OK)
        response_detail_own = self.client.get(f'/reports/{self.citizen_report.pk}/')
        self.assertEqual(response_detail_own.status_code, 200)

    def test_citizen_sees_only_own_reports_in_list(self):
        self.client.login(username='john_citizen', password='password123')
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        reports_in_context = response.context['reports']
        self.assertEqual(len(reports_in_context), 1)
        self.assertEqual(reports_in_context[0].pk, self.citizen_report.pk)

    def test_authority_access_control_allowed(self):
        self.client.login(username='authority_officer', password='password123')

        # Higher Authority CAN access Dashboard (200 OK)
        response_dash = self.client.get('/authority/')
        self.assertEqual(response_dash.status_code, 200)

        # Higher Authority CAN access Hotspot Radar (200 OK)
        response_hotspots = self.client.get('/hotspots/')
        self.assertEqual(response_hotspots.status_code, 200)

        # Higher Authority CAN view any report detail (200 OK)
        response_detail = self.client.get(f'/reports/{self.citizen_report.pk}/')
        self.assertEqual(response_detail.status_code, 200)

        # Higher Authority sees all reports in list view
        response_list = self.client.get('/reports/')
        self.assertEqual(len(response_list.context['reports']), 2)

    def test_duplicate_detection_multi_signal_scoring(self):
        """Multi-signal duplicate detection evaluates spatial, temporal, and species proximity."""
        from reports.services import DuplicateSpamDetectionService

        # New report right next to citizen_report (within 25m), 5 mins later, same species
        report_b = SightingReport.objects.create(
            user=self.other_citizen,
            title="Second cobra sighting",
            latitude=9.9314,
            longitude=76.2674,
            location_name='Kochi Sector 4 Market',
            species_predicted='Indian Cobra (Naja naja)',
            venom_category=SightingReport.VENOM_HIGHLY,
        )

        DuplicateSpamDetectionService.evaluate_and_flag(report_b)
        report_b.refresh_from_db()

        self.assertTrue(report_b.duplicate_flag)
        self.assertGreaterEqual(report_b.duplicate_score, 75)
        self.assertEqual(report_b.duplicate_of, self.citizen_report)
        self.assertIn("Immediate proximity", report_b.duplicate_reason)

    def test_duplicate_detection_does_not_merge_resolved_incidents(self):
        """Resolved incidents must never be automatically linked as active duplicate parents."""
        from reports.services import DuplicateSpamDetectionService

        # Mark citizen report as resolved
        self.citizen_report.status = SightingReport.STATUS_RESOLVED
        self.citizen_report.save()

        # New sighting in same spot
        report_new = SightingReport.objects.create(
            user=self.other_citizen,
            title="Fresh snake encounter",
            latitude=9.9312,
            longitude=76.2673,
            location_name='Kochi Sector 4',
            species_predicted='Indian Cobra (Naja naja)',
            venom_category=SightingReport.VENOM_HIGHLY,
        )

        DuplicateSpamDetectionService.evaluate_and_flag(report_new)
        report_new.refresh_from_db()

        # Must NOT auto-merge to a resolved incident
        self.assertNotEqual(report_new.duplicate_of, self.citizen_report)

    def test_ranger_assignment_and_authority_review_lifecycle(self):
        """End-to-end Ranger response and Authority verification workflow."""
        from reports.models import RangerAssignment

        # Create Ranger user
        ranger = User.objects.create_user(username='ranger_kochi', password='password123')
        ranger.profile.role = UserProfile.ROLE_RANGER
        ranger.profile.registered_location = 'Kochi Sector 4'
        ranger.profile.latitude = 9.9310
        ranger.profile.longitude = 76.2670
        ranger.profile.availability = UserProfile.AVAILABILITY_AVAILABLE
        ranger.profile.save()

        # 1. Authority assigns incident to Ranger
        self.client.login(username='authority_officer', password='password123')
        res_assign = self.client.post(f'/reports/{self.citizen_report.pk}/assign/', {
            'ranger_id': ranger.pk
        })
        self.assertEqual(res_assign.status_code, 302)

        assignment = RangerAssignment.objects.get(sighting=self.citizen_report, ranger=ranger)
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ASSIGNED)

        # 2. Ranger logs in, views assignment detail, and accepts
        self.client.logout()
        self.client.login(username='ranger_kochi', password='password123')
        res_detail = self.client.get(f'/ranger/assignments/{assignment.pk}/')
        self.assertEqual(res_detail.status_code, 200)

        # Accept
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'ACCEPT'})
        assignment.refresh_from_db()
        ranger.profile.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ACCEPTED)
        self.assertEqual(ranger.profile.availability, UserProfile.AVAILABILITY_BUSY)

        # En route
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'ON_THE_WAY'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ON_THE_WAY)

        # At location
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'AT_LOCATION'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_AT_LOCATION)

        # 3. Ranger submits field outcome
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {
            'action': 'SUBMIT_OUTCOME',
            'outcome': 'SNAKE_CAPTURED',
            'notes': 'Snake safely retrieved using tongs and secured in ventilated rescue bin.',
        })
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_OUTCOME_SUBMITTED)
        self.assertEqual(assignment.review_decision, 'PENDING_REVIEW')

        # 4. Authority reviews and rejects with request to verify perimeter
        self.client.logout()
        self.client.login(username='authority_officer', password='password123')
        res_reject = self.client.post(f'/reports/assignments/{assignment.pk}/review/', {
            'decision': 'REJECTED',
            'review_notes': 'Please conduct a 10m perimeter sweep to confirm no secondary snakes in brush.'
        })
        self.assertEqual(res_reject.status_code, 302)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_AT_LOCATION)
        self.assertEqual(assignment.review_decision, 'REJECTED')

        # 5. Ranger re-submits outcome after sweep
        self.client.logout()
        self.client.login(username='ranger_kochi', password='password123')
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {
            'action': 'SUBMIT_OUTCOME',
            'outcome': 'SNAKE_CAPTURED',
            'notes': 'Perimeter sweep completed. Zero secondary specimens found. Area secure.',
        })
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_OUTCOME_SUBMITTED)

        # 6. Authority approves outcome
        self.client.logout()
        self.client.login(username='authority_officer', password='password123')
        res_approve = self.client.post(f'/reports/assignments/{assignment.pk}/review/', {
            'decision': 'APPROVED',
            'review_notes': 'Well executed. Sighting confirmed closed.'
        })
        self.assertEqual(res_approve.status_code, 302)

        assignment.refresh_from_db()
        self.citizen_report.refresh_from_db()
        ranger.profile.refresh_from_db()

        self.assertEqual(assignment.status, RangerAssignment.STATUS_COMPLETED)
        self.assertEqual(assignment.review_decision, 'APPROVED')
        self.assertEqual(self.citizen_report.status, SightingReport.STATUS_RESOLVED)
        self.assertEqual(ranger.profile.availability, UserProfile.AVAILABILITY_AVAILABLE)

    def test_ranger_object_level_security(self):
        """Rangers cannot inspect or act on assignments belonging to other rangers."""
        from reports.models import RangerAssignment

        ranger_a = User.objects.create_user(username='ranger_alpha', password='password123')
        ranger_a.profile.role = UserProfile.ROLE_RANGER
        ranger_a.profile.save()

        ranger_b = User.objects.create_user(username='ranger_beta', password='password123')
        ranger_b.profile.role = UserProfile.ROLE_RANGER
        ranger_b.profile.save()

        assignment_a = RangerAssignment.objects.create(
            sighting=self.citizen_report, ranger=ranger_a, status=RangerAssignment.STATUS_ASSIGNED
        )

        self.client.login(username='ranger_beta', password='password123')
        # Ranger Beta attempts to view Ranger Alpha's assignment -> 404
        res = self.client.get(f'/ranger/assignments/{assignment_a.pk}/')
        self.assertEqual(res.status_code, 404)


class ReportingAndRiskZoneLifecycleTestCase(TestCase):
    def setUp(self):
        from accounts.models import UserProfile
        self.user1 = User.objects.create_user(username='citizen_one', password='password123')
        self.user1.profile.role = UserProfile.ROLE_CITIZEN
        self.user1.profile.save()

        self.user2 = User.objects.create_user(username='citizen_two', password='password123')
        self.user2.profile.role = UserProfile.ROLE_CITIZEN
        self.user2.profile.save()

    def test_report_numbering_and_reference_per_citizen(self):
        """
        Verifies the resolution of the #12 bug:
        - The user's first report is numbered #1 for that citizen.
        - Subsequent reports increment sequentially for that citizen (#2).
        - Different citizens have independent submission counters starting at #1.
        - Each report has a stable, unique report_reference (e.g. VW-0001).
        """
        # User 1 submits report 1
        r1 = SightingReport.objects.create(
            user=self.user1,
            title="First sighting for user 1",
            latitude=9.9312,
            longitude=76.2673,
            location_name="Sector 1"
        )
        self.assertEqual(r1.citizen_submission_number, 1)
        self.assertEqual(r1.report_reference, f"VW-{r1.id:04d}")

        # User 1 submits report 2
        r2 = SightingReport.objects.create(
            user=self.user1,
            title="Second sighting for user 1",
            latitude=9.9320,
            longitude=76.2680,
            location_name="Sector 1 Park"
        )
        self.assertEqual(r2.citizen_submission_number, 2)
        self.assertEqual(r2.report_reference, f"VW-{r2.id:04d}")

        # User 2 submits their first report - must be #1, NOT #3
        r3 = SightingReport.objects.create(
            user=self.user2,
            title="First sighting for user 2",
            latitude=10.0400,
            longitude=76.3200,
            location_name="Kalamassery"
        )
        self.assertEqual(r3.citizen_submission_number, 1)
        self.assertEqual(r3.report_reference, f"VW-{r3.id:04d}")

    def test_sighting_form_coordinate_validation(self):
        """Form validates coordinates boundaries and handles manual location input."""
        from reports.forms import SightingReportForm

        # Invalid latitude (> 90)
        form_invalid_lat = SightingReportForm(data={
            'title': 'Test Snake',
            'latitude': 95.0,
            'longitude': 76.2673,
            'location_name': 'Kochi'
        })
        self.assertFalse(form_invalid_lat.is_valid())
        self.assertIn('latitude', form_invalid_lat.errors)

        # Invalid longitude (> 180)
        form_invalid_lng = SightingReportForm(data={
            'title': 'Test Snake',
            'latitude': 9.9312,
            'longitude': 185.0,
            'location_name': 'Kochi'
        })
        self.assertFalse(form_invalid_lng.is_valid())
        self.assertIn('longitude', form_invalid_lng.errors)

        # Missing location name
        form_missing_loc = SightingReportForm(data={
            'title': 'Test Snake',
            'latitude': 9.9312,
            'longitude': 76.2673,
            'location_name': ''
        })
        self.assertFalse(form_missing_loc.is_valid())
        self.assertIn('location_name', form_missing_loc.errors)

        # Valid manual input with valid image
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        img_byte_arr = io.BytesIO()
        test_img = Image.new("RGB", (50, 50), color=(10, 150, 80))
        test_img.save(img_byte_arr, format='JPEG')
        dummy_img = SimpleUploadedFile("snake.jpg", img_byte_arr.getvalue(), content_type="image/jpeg")

        form_valid = SightingReportForm(
            data={
                'title': 'Manual Location Sighting',
                'latitude': 9.9312,
                'longitude': 76.2673,
                'location_name': 'Marine Drive Promenade',
                'notes': 'Observed near walkway rocks.'
            },
            files={'original_image': dummy_img}
        )
        self.assertTrue(form_valid.is_valid(), f"Form errors: {form_valid.errors}")

    def test_risk_zone_lifecycle_and_distinct_incident_counting(self):
        """
        Tests the 4-state lifecycle and duplicate deduplication:
        - 0 active -> No active zones
        - 1-2 distinct active -> ORANGE
        - 3+ distinct active -> RED
        - Duplicates do not inflate active count
        - Resolved incident -> YELLOW (cooldown)
        - Cooldown expired -> GREEN
        - Green retention expired -> removed
        """
        from hotspots.services import DBSCANHotspotService
        from datetime import timedelta
        from django.utils import timezone

        # 1. Zero incidents -> empty zones
        res_zero = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_zero['total_active_incidents'], 0)
        self.assertEqual(len(res_zero['zones']), 0)

        # 2. 1 active incident -> ORANGE
        inc1 = SightingReport.objects.create(
            user=self.user1,
            title="Active Incident 1",
            latitude=9.9312,
            longitude=76.2673,
            location_name="Zone Central",
            status=SightingReport.STATUS_PENDING
        )
        res_one = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_one['total_active_incidents'], 1)
        self.assertEqual(len(res_one['zones']), 1)
        self.assertEqual(res_one['zones'][0]['state'], 'ORANGE')

        # 3. Add duplicate report for inc1 -> should NOT increase active count
        dup_report = SightingReport.objects.create(
            user=self.user2,
            title="Duplicate report for inc1",
            latitude=9.9313,
            longitude=76.2674,
            location_name="Zone Central",
            status=SightingReport.STATUS_PENDING,
            duplicate_flag=True,
            duplicate_of=inc1
        )
        res_dup = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_dup['total_active_incidents'], 1)
        self.assertEqual(res_dup['zones'][0]['state'], 'ORANGE')

        # 4. Add 2 more distinct incidents in same sector -> total 3 distinct active -> RED
        inc2 = SightingReport.objects.create(
            user=self.user1,
            title="Active Incident 2",
            latitude=9.9320,
            longitude=76.2680,
            location_name="Zone Central East",
            status=SightingReport.STATUS_VERIFIED
        )
        inc3 = SightingReport.objects.create(
            user=self.user2,
            title="Active Incident 3",
            latitude=9.9305,
            longitude=76.2665,
            location_name="Zone Central South",
            status=SightingReport.STATUS_PENDING
        )
        res_three = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_three['total_active_incidents'], 3)
        self.assertEqual(res_three['zones'][0]['state'], 'RED')

        # 5. Resolve all 3 incidents now -> zone enters YELLOW (Recently Resolved cooldown)
        now = timezone.now()
        for inc in [inc1, inc2, inc3]:
            inc.status = SightingReport.STATUS_RESOLVED
            inc.save()
        res_resolved = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_resolved['total_active_incidents'], 0)
        self.assertEqual(res_resolved['zones'][0]['state'], 'YELLOW')

        # 6. Simulate cooldown expiry (resolved 26 hours ago, where cooldown = 24h)
        # Using SightingReport.objects.filter.update to set updated_at directly
        past_cooldown = now - timedelta(hours=26)
        SightingReport.objects.filter(pk__in=[inc1.pk, inc2.pk, inc3.pk]).update(
            updated_at=past_cooldown,
            created_at=past_cooldown
        )
        res_green = DBSCANHotspotService.compute_community_risk_zones()
        self.assertEqual(res_green['zones'][0]['state'], 'GREEN')

        # 7. Simulate retention expiry (> 24 + 48 = 72 hours ago)
        past_retention = now - timedelta(hours=75)
        SightingReport.objects.filter(pk__in=[inc1.pk, inc2.pk, inc3.pk]).update(
            updated_at=past_retention,
            created_at=past_retention
        )
        res_expired = DBSCANHotspotService.compute_community_risk_zones()
        # Expired zone must not be shown
        self.assertEqual(len(res_expired['zones']), 0)

    def test_citizen_sightings_page_removes_rescue_status_and_filter(self):
        """Verifies that Rescue Status column and filter buttons are removed from citizen view."""
        self.client.login(username='citizen_one', password='password123')
        resp = self.client.get('/reports/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertNotIn('Rescue Status', content)
        self.assertNotIn('Filter Results', content)
        self.assertNotIn('Filter Sightings', content)

    def test_risk_zones_api_endpoint(self):
        """Verifies the /reports/api/risk-zones/ endpoint returns structured zone data."""
        resp = self.client.get('/reports/api/risk-zones/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertIn('zones', data)
        self.assertIn('active_window_hours', data)


class AuthorityMapAndImageMappingTestCase(TestCase):
    """
    Automated tests verifying:
    1. New Citizen report persistence
    2. Authority map reports API returns new reports
    3. Pending verification reports are not excluded
    4. Unauthorized users blocked (Citizens/Rangers get 403 or redirect)
    5. Distinct images map to correct reports without crossover
    6. Marker report IDs match panel detail data
    7. Confidence normalization (percentage scale 0-100%, handling 0-1, 0-100, invalid)
    8. Assignment and status changes reflect in map API
    9. Invalid coordinates handled safely
    10. Missing images handled gracefully
    """
    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.citizen = User.objects.create_user(username='test_citizen_map', password='password123')
        self.citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.citizen.profile.save()

        self.authority = User.objects.create_user(username='test_authority_map', password='password123')
        self.authority.profile.role = UserProfile.ROLE_AUTHORITY
        self.authority.profile.assigned_region = 'Kollam Division'
        self.authority.profile.save()

        self.ranger = User.objects.create_user(username='test_ranger_map', password='password123')
        self.ranger.profile.role = UserProfile.ROLE_RANGER
        self.ranger.profile.registered_location = 'Kollam, Kerala'
        self.ranger.profile.latitude = 8.8932
        self.ranger.profile.longitude = 76.6141
        self.ranger.profile.save()

        # Create two distinct test image files
        png_1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        png_2 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x06\x00\x00\x00v\xd7\x89\x94\x00\x00\x00\x0bIDATx\x9cc`\x00\x02\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

        self.file_1 = SimpleUploadedFile('cobra_image.png', png_1, content_type='image/png')
        self.file_2 = SimpleUploadedFile('viper_image.png', png_2, content_type='image/png')

    def test_01_citizen_report_saved_correctly(self):
        report = SightingReport.objects.create(
            user=self.citizen,
            title="Citizen Sighting Alpha",
            original_image=self.file_1,
            latitude=8.8932,
            longitude=76.6141,
            location_name="Kollam Town",
            species_predicted="Indian Cobra",
            venom_category=SightingReport.VENOM_HIGHLY,
            venom_confidence=82.4,
            status=SightingReport.STATUS_PENDING
        )
        self.assertEqual(report.user, self.citizen)
        self.assertEqual(report.latitude, 8.8932)
        self.assertEqual(report.longitude, 76.6141)
        self.assertEqual(report.status, SightingReport.STATUS_PENDING)
        self.assertIn('cobra_image', report.original_image.name)

    def test_02_authorized_authority_endpoint_returns_new_report(self):
        report = SightingReport.objects.create(
            user=self.citizen,
            title="New Cobra Sighting",
            latitude=8.8932,
            longitude=76.6141,
            location_name="Kollam",
            species_predicted="Indian Cobra",
            venom_category=SightingReport.VENOM_HIGHLY,
            venom_confidence=82.4,
            status=SightingReport.STATUS_PENDING
        )
        self.client.login(username='test_authority_map', password='password123')
        resp = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        report_ids = [r['id'] for r in data['reports']]
        self.assertIn(report.id, report_ids)

    def test_03_pending_verification_reports_not_excluded(self):
        pending_report = SightingReport.objects.create(
            user=self.citizen,
            title="Pending Report",
            latitude=8.8932,
            longitude=76.6141,
            location_name="Kollam",
            status=SightingReport.STATUS_PENDING
        )
        self.client.login(username='test_authority_map', password='password123')
        resp = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        matched = next((r for r in data['reports'] if r['id'] == pending_report.id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched['report_status'], SightingReport.STATUS_PENDING)

    def test_04_unauthorized_users_blocked_from_authority_endpoints(self):
        # Anonymous user
        resp_anon = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp_anon.status_code, 302)

        # Citizen user gets HTTP 403
        self.client.login(username='test_citizen_map', password='password123')
        resp_citizen = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp_citizen.status_code, 403)

        resp_citizen_panel = self.client.get('/reports/api/report-panel/1/')
        self.assertEqual(resp_citizen_panel.status_code, 403)

        # Ranger user gets HTTP 403
        self.client.login(username='test_ranger_map', password='password123')
        resp_ranger = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp_ranger.status_code, 403)

    def test_05_two_reports_distinct_images_never_crossed(self):
        rep1 = SightingReport.objects.create(
            user=self.citizen,
            title="Report with Cobra",
            original_image=self.file_1,
            latitude=8.8932,
            longitude=76.6141,
            location_name="Site A",
            venom_confidence=82.4
        )
        rep2 = SightingReport.objects.create(
            user=self.citizen,
            title="Report with Viper",
            original_image=self.file_2,
            latitude=8.8950,
            longitude=76.6150,
            location_name="Site B",
            venom_confidence=91.5
        )

        self.client.login(username='test_authority_map', password='password123')

        p1_res = self.client.get(f'/reports/api/report-panel/{rep1.id}/')
        p1 = p1_res.json()

        p2_res = self.client.get(f'/reports/api/report-panel/{rep2.id}/')
        p2 = p2_res.json()

        self.assertNotEqual(p1['image_url'], p2['image_url'])
        self.assertIn('cobra_image', p1['image_url'])
        self.assertIn('viper_image', p2['image_url'])
        self.assertEqual(p1['id'], rep1.id)
        self.assertEqual(p2['id'], rep2.id)

    def test_06_confidence_normalization_semantics(self):
        from reports.views import normalize_confidence_percentage
        # Probability scale [0.0, 1.0] -> percentage scale
        self.assertEqual(normalize_confidence_percentage(0.824), 82.4)
        self.assertEqual(normalize_confidence_percentage(1.0), 100.0)
        self.assertEqual(normalize_confidence_percentage(0.0), 0.0)

        # Already percentage scale (1.0, 100.0] -> preserved
        self.assertEqual(normalize_confidence_percentage(82.4), 82.4)
        self.assertEqual(normalize_confidence_percentage(99.9), 99.9)
        self.assertEqual(normalize_confidence_percentage(100.0), 100.0)

        # Invalid, negative, or uncalibrated > 100 -> None (Confidence unavailable)
        self.assertIsNone(normalize_confidence_percentage(8240))
        self.assertIsNone(normalize_confidence_percentage(-5))
        self.assertIsNone(normalize_confidence_percentage(None))
        self.assertIsNone(normalize_confidence_percentage("invalid"))

    def test_07_invalid_coordinates_handled_safely(self):
        # Non-numeric or out-of-range coordinates should not crash the endpoint
        rep_invalid = SightingReport.objects.create(
            user=self.citizen,
            title="Invalid Coords Report",
            latitude=999.0, # invalid latitude > 90
            longitude=76.6141,
            location_name="Ocean"
        )
        rep_zero = SightingReport.objects.create(
            user=self.citizen,
            title="Zero Island Report",
            latitude=0.0,
            longitude=0.0,
            location_name="Null Island"
        )
        rep_invalid_lng = SightingReport.objects.create(
            user=self.citizen,
            title="Invalid Longitude Report",
            latitude=8.8932,
            longitude=250.0,
            location_name="Out of bounds"
        )

        self.client.login(username='test_authority_map', password='password123')
        resp = self.client.get('/reports/api/map-reports/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [r['id'] for r in data['reports']]
        self.assertNotIn(rep_invalid.id, ids)
        self.assertNotIn(rep_zero.id, ids)
        self.assertNotIn(rep_invalid_lng.id, ids)
        self.assertGreaterEqual(data['counts']['unplotted_count'], 3)

    def test_08_assignment_and_status_changes_update_map(self):
        rep = SightingReport.objects.create(
            user=self.citizen,
            title="Incident for Assignment",
            latitude=8.8932,
            longitude=76.6141,
            location_name="Kollam",
            venomous=True,
            venom_category=SightingReport.VENOM_HIGHLY,
            response_status=SightingReport.RESPONSE_UNASSIGNED
        )
        self.client.login(username='test_authority_map', password='password123')
        resp1 = self.client.get('/reports/api/map-reports/')
        r_item1 = next(r for r in resp1.json()['reports'] if r['id'] == rep.id)
        self.assertEqual(r_item1['dispatch_state'], 'UNASSIGNED')

        # Create active assignment
        assignment = RangerAssignment.objects.create(
            sighting=rep,
            ranger=self.ranger,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ACCEPTED
        )
        rep.response_status = SightingReport.RESPONSE_IN_PROGRESS
        rep.save()

        resp2 = self.client.get('/reports/api/map-reports/')
        r_item2 = next(r for r in resp2.json()['reports'] if r['id'] == rep.id)
        self.assertEqual(r_item2['dispatch_state'], 'ACTIVE')
        self.assertEqual(r_item2['assignment']['ranger'], self.ranger.username)

        # Complete assignment
        assignment.status = RangerAssignment.STATUS_COMPLETED
        assignment.save()
        rep.response_status = SightingReport.RESPONSE_RESOLVED
        rep.status = SightingReport.STATUS_RESOLVED
        rep.save()

        resp3 = self.client.get('/reports/api/map-reports/')
        r_item3 = next(r for r in resp3.json()['reports'] if r['id'] == rep.id)
        self.assertEqual(r_item3['dispatch_state'], 'COMPLETED')

    def test_09_missing_image_handled_safely(self):
        rep_no_img = SightingReport.objects.create(
            user=self.citizen,
            title="Report Without Image",
            latitude=8.8932,
            longitude=76.6141,
            location_name="Kollam",
            original_image=None
        )
        self.client.login(username='test_authority_map', password='password123')
        resp = self.client.get(f'/reports/api/report-panel/{rep_no_img.id}/')
        self.assertEqual(resp.status_code, 200)
        p = resp.json()
        self.assertIsNone(p['image_url'])
        self.assertEqual(p['id'], rep_no_img.id)



