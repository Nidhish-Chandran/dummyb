from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from reports.models import SightingReport
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

