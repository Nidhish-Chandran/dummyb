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
        self.ranger = User.objects.create_user(username='ranger_officer', password='password123')
        self.ranger.profile.role = UserProfile.ROLE_RANGER
        self.ranger.profile.save()

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
        response_dash = self.client.get('/')
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
        self.client.login(username='ranger_officer', password='password123')

        # Higher Authority CAN access Dashboard (200 OK)
        response_dash = self.client.get('/')
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
