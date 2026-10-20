from django.test import TestCase
from django.contrib.auth.models import User
from accounts.models import UserProfile
from emergency.models import Hospital, EmergencySOSEvent

class EmergencySOSTestCase(TestCase):
    def setUp(self):
        # Create Authority user
        self.authority = User.objects.create_user(username='authority_emergency', password='password123')
        self.authority.profile.role = UserProfile.ROLE_AUTHORITY
        self.authority.profile.save()

        # Create Citizen user
        self.citizen = User.objects.create_user(username='citizen_emergency', password='password123')
        self.citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.citizen.profile.save()

        # Create Hospital
        self.hospital = Hospital.objects.create(
            name='District General Hospital',
            phone_number='108',
            address='Civil Lines',
            latitude=9.9312,
            longitude=76.2673,
            anti_venom_available=True,
            anti_venom_stock_vials=50,
            has_icu=True
        )

    def test_sos_trigger_persists_event(self):
        """Citizen or guest triggering SOS persists an EmergencySOSEvent."""
        self.client.login(username='citizen_emergency', password='password123')
        response = self.client.post('/emergency/api/sos/', {
            'latitude': 9.9315,
            'longitude': 76.2670,
            'phone_number': '+91 99988 77766',
            'location': 'Near Gandhi Square',
            'description': 'Snake encounter, suspected bite.',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertIn('event_id', data)

        event = EmergencySOSEvent.objects.get(id=data['event_id'])
        self.assertEqual(event.user, self.citizen)
        self.assertEqual(event.phone_number, '+91 99988 77766')
        self.assertEqual(event.status, EmergencySOSEvent.STATUS_ACTIVE)

    def test_sos_duplicate_throttling(self):
        """Rapid duplicate SOS requests within 2 minutes return the existing event."""
        # First trigger
        res1 = self.client.post('/emergency/api/sos/', {
            'latitude': 9.9315,
            'longitude': 76.2670,
            'phone_number': '+91 99988 77766',
        })
        self.assertEqual(res1.status_code, 200)

        # Immediate second trigger at same location
        res2 = self.client.post('/emergency/api/sos/', {
            'latitude': 9.9315,
            'longitude': 76.2670,
            'phone_number': '+91 99988 77766',
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2.get('duplicate', False))
        self.assertEqual(EmergencySOSEvent.objects.filter(status=EmergencySOSEvent.STATUS_ACTIVE).count(), 1)

    def test_sos_authority_feed_and_acknowledgement(self):
        """Authority can view the live SOS feed and acknowledge/resolve events."""
        event = EmergencySOSEvent.objects.create(
            user=self.citizen,
            latitude=9.9312,
            longitude=76.2673,
            phone_number='+91 98765 00000',
            location_name='Kochi Marine Drive',
            status=EmergencySOSEvent.STATUS_ACTIVE
        )

        self.client.login(username='authority_emergency', password='password123')

        # 1. Authority checks feed
        res_feed = self.client.get('/emergency/api/sos/feed/')
        self.assertEqual(res_feed.status_code, 200)
        events_list = res_feed.json()['sos_events']
        self.assertTrue(any(e['id'] == event.id for e in events_list))

        # 2. Authority acknowledges
        res_ack = self.client.post(f'/emergency/api/sos/{event.id}/ack/', {
            'action': 'ACKNOWLEDGE',
            'notes': 'Dispatched emergency ambulance and alerted local ranger unit.'
        })
        self.assertEqual(res_ack.status_code, 200)

        event.refresh_from_db()
        self.assertEqual(event.status, EmergencySOSEvent.STATUS_ACKNOWLEDGED)
        self.assertEqual(event.acknowledged_by, self.authority)

        # 3. Authority resolves
        res_resolve = self.client.post(f'/emergency/api/sos/{event.id}/ack/', {
            'action': 'RESOLVE',
            'notes': 'Patient received at District General Hospital; anti-venom administered.'
        })
        self.assertEqual(res_resolve.status_code, 200)

        event.refresh_from_db()
        self.assertEqual(event.status, EmergencySOSEvent.STATUS_RESOLVED)

    def test_sos_security_denied_for_citizen(self):
        """Citizens cannot view the Authority SOS operations feed or acknowledge events."""
        event = EmergencySOSEvent.objects.create(
            latitude=9.9312, longitude=76.2673, status=EmergencySOSEvent.STATUS_ACTIVE
        )
        self.client.login(username='citizen_emergency', password='password123')
        res_feed = self.client.get('/emergency/api/sos/feed/')
        self.assertEqual(res_feed.status_code, 403)

        res_ack = self.client.post(f'/emergency/api/sos/{event.id}/ack/', {'action': 'ACKNOWLEDGE'})
        self.assertEqual(res_ack.status_code, 403)

    def test_hospital_distance_calculation(self):
        """Haversine distance calculates correctly and returns distance in km."""
        dist = self.hospital.distance_from(9.9312, 76.2673)
        self.assertEqual(dist, 0.0)

        # ~12 km away in Kalamassery
        dist_kal = self.hospital.distance_from(10.0456, 76.3212)
        self.assertGreater(dist_kal, 10.0)
        self.assertLess(dist_kal, 16.0)


class AdminHospitalManagementTestCase(TestCase):
    def setUp(self):
        # Admin user
        self.admin = User.objects.create_superuser(username='admin_hosp', password='password123', email='admin@test.gov')
        self.admin.profile.role = UserProfile.ROLE_ADMIN
        self.admin.profile.save()

        # Non-admin users
        self.authority = User.objects.create_user(username='auth_hosp', password='password123')
        self.authority.profile.role = UserProfile.ROLE_AUTHORITY
        self.authority.profile.save()

        self.ranger = User.objects.create_user(username='ranger_hosp', password='password123')
        self.ranger.profile.role = UserProfile.ROLE_RANGER
        self.ranger.profile.save()

        self.citizen = User.objects.create_user(username='citizen_hosp', password='password123')
        self.citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.citizen.profile.save()

    def test_hospital_management_permission_denied_for_non_admins(self):
        """Citizens, Rangers, and Authority officers are forbidden from managing hospitals."""
        for user in [self.citizen, self.ranger, self.authority]:
            self.client.login(username=user.username, password='password123')
            resp = self.client.get('/emergency/manage/')
            self.assertEqual(resp.status_code, 403, f"{user.username} should receive 403 on /emergency/manage/")

    def test_admin_can_access_and_add_hospital(self):
        """Admin can access hospital management and register a new medical facility."""
        self.client.login(username='admin_hosp', password='password123')
        resp = self.client.get('/emergency/manage/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Hospital &amp; Anti-Venom Supply Registry")

        # Create new hospital
        post_data = {
            'action': 'add_hospital',
            'name': 'Wayanad District Envenomation Center',
            'district': 'Wayanad',
            'address': 'Main Highway, Mananthavady',
            'phone_number': '+91 4935 240223',
            'latitude': 11.8021,
            'longitude': 76.0034,
            'operating_hours': '24/7 Trauma Emergency Care',
            'anti_venom_available': True,
            'anti_venom_stock_vials': 75,
            'anti_venom_notes': 'Polyvalent lyophilized anti-venom vials in cold storage.',
            'emergency_department': True,
            'has_icu': True,
        }
        res_post = self.client.post('/emergency/manage/', post_data)
        self.assertRedirects(res_post, '/emergency/manage/')

        hospital = Hospital.objects.get(name='Wayanad District Envenomation Center')
        self.assertEqual(hospital.district, 'Wayanad')
        self.assertEqual(hospital.anti_venom_stock_vials, 75)
        self.assertTrue(hospital.has_icu)
        self.assertTrue(hospital.emergency_department)
        self.assertEqual(hospital.updated_by, self.admin)
        self.assertIsNotNone(hospital.stock_last_updated)

    def test_duplicate_hospital_rejected(self):
        """Attempting to add a hospital with duplicate name & district is rejected."""
        Hospital.objects.create(
            name='Kollam General Hospital',
            district='Kollam',
            address='Hospital Road',
            phone_number='108',
            latitude=8.8932,
            longitude=76.6141,
        )

        self.client.login(username='admin_hosp', password='password123')
        post_data = {
            'action': 'add_hospital',
            'name': 'Kollam General Hospital',
            'district': 'Kollam',
            'address': 'Different address',
            'phone_number': '108',
            'latitude': 8.8950,
            'longitude': 76.6150,
        }
        resp = self.client.post('/emergency/manage/', post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already registered in district")

    def test_invalid_coordinates_rejected(self):
        """Out of bounds coordinates are rejected by the hospital form."""
        self.client.login(username='admin_hosp', password='password123')
        post_data = {
            'action': 'add_hospital',
            'name': 'Invalid Coord Hospital',
            'district': 'Kochi',
            'address': 'Test address',
            'phone_number': '108',
            'latitude': 120.5,  # Invalid latitude (> 90)
            'longitude': 76.2673,
        }
        resp = self.client.post('/emergency/manage/', post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "between -90.0 and 90.0")

    def test_admin_edit_hospital(self):
        """Admin can edit an existing hospital record."""
        h = Hospital.objects.create(
            name='Alappuzha Medical Unit',
            district='Alappuzha',
            address='Beach Road',
            phone_number='108',
            latitude=9.4981,
            longitude=76.3388,
            anti_venom_stock_vials=20
        )
        self.client.login(username='admin_hosp', password='password123')
        edit_url = f'/emergency/manage/{h.pk}/edit/'

        # Get edit page
        resp_get = self.client.get(edit_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, 'Alappuzha Medical Unit')

        # Submit update
        resp_post = self.client.post(edit_url, {
            'name': 'Alappuzha Medical Unit',
            'district': 'Alappuzha',
            'address': 'Beach Road, Sector 2',
            'phone_number': '+91 477 2251111',
            'latitude': 9.4981,
            'longitude': 76.3388,
            'anti_venom_available': True,
            'anti_venom_stock_vials': 80,
            'anti_venom_notes': 'Stock restocked with 60 additional vials.',
            'emergency_department': True,
            'has_icu': True,
        })
        self.assertRedirects(resp_post, '/emergency/manage/')

        h.refresh_from_db()
        self.assertEqual(h.anti_venom_stock_vials, 80)
        self.assertEqual(h.updated_by, self.admin)
        self.assertIn('restocked', h.anti_venom_notes)

    def test_admin_delete_hospital(self):
        """Admin can delete a hospital record."""
        h = Hospital.objects.create(
            name='Temporary Clinic',
            district='Kottayam',
            address='Town Road',
            phone_number='108',
            latitude=9.5916,
            longitude=76.5222,
        )
        self.client.login(username='admin_hosp', password='password123')
        del_url = f'/emergency/manage/{h.pk}/delete/'

        resp = self.client.post(del_url)
        self.assertRedirects(resp, '/emergency/manage/')
        self.assertFalse(Hospital.objects.filter(pk=h.pk).exists())

    def test_assistance_view_uses_authority_hospitals_and_sorts_nearest_first(self):
        """Emergency assistance page displays authority-managed hospitals sorted nearest first."""
        # Create 2 hospitals at known distances
        h_near = Hospital.objects.create(
            name='Near Medical Centre',
            phone_number='108',
            address='Kochi Sector 1',
            latitude=9.9320,
            longitude=76.2680,
            anti_venom_available=True,
            anti_venom_stock_vials=20
        )
        h_far = Hospital.objects.create(
            name='Distant Regional Hospital',
            phone_number='108',
            address='Thrissur Central',
            latitude=10.5276,
            longitude=76.2144,
            anti_venom_available=True,
            anti_venom_stock_vials=35
        )

        # Query assistance page with user coords close to h_near
        resp = self.client.get('/emergency/?lat=9.9312&lng=76.2673')
        self.assertEqual(resp.status_code, 200)
        hospitals_in_context = resp.context['hospitals']
        self.assertGreaterEqual(len(hospitals_in_context), 2)
        
        # Verify first hospital is the nearest
        first_hosp = hospitals_in_context[0]
        self.assertEqual(first_hosp.name, 'Near Medical Centre')
        self.assertIsNotNone(first_hosp.distance_km)
        self.assertLess(first_hosp.distance_km, 1.0)

    def test_assistance_view_safe_missing_coordinates(self):
        """Page safely handles missing coordinates without crashing."""
        resp = self.client.get('/emergency/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('hospitals', resp.context)
        content = resp.content.decode('utf-8')
        self.assertIn("No hospitals currently registered", content)


class KollamHospitalRegistrySeedingTestCase(TestCase):
    """Verifies that the seed_kollam_hospitals command is additive, idempotent,
    contains authentic facilities with valid coordinates, and integrates with distance sorting.
    """

    def test_seed_command_additive_and_idempotent(self):
        from django.core.management import call_command
        from io import StringIO

        # 1. Create a pre-existing custom hospital to ensure it is preserved
        pre_existing = Hospital.objects.create(
            name="Existing Specialty Clinic",
            phone_number="0474-2000000",
            address="Kollam Town",
            latitude=8.8900,
            longitude=76.6000,
            district="Kollam",
            anti_venom_available=False
        )
        initial_count = Hospital.objects.count()

        # 2. Run seed command
        out = StringIO()
        call_command('seed_kollam_hospitals', stdout=out)
        self.assertEqual(Hospital.objects.count(), initial_count + 10)
        
        # Verify pre-existing hospital is preserved
        self.assertTrue(Hospital.objects.filter(pk=pre_existing.pk).exists())

        # 3. Re-run command to verify idempotency
        call_command('seed_kollam_hospitals', stdout=out)
        self.assertEqual(Hospital.objects.count(), initial_count + 10)

    def test_kollam_hospital_coordinates_and_distance_ranking(self):
        from django.core.management import call_command
        call_command('seed_kollam_hospitals')

        # Verify key facilities exist with valid coordinates
        gmc = Hospital.objects.get(name='Government Medical College Hospital, Kollam')
        self.assertEqual(gmc.district, 'Kollam')
        self.assertTrue(8.0 <= gmc.latitude <= 9.5)
        self.assertTrue(76.0 <= gmc.longitude <= 77.5)
        self.assertTrue(gmc.anti_venom_available)
        self.assertTrue(gmc.has_icu)
        self.assertTrue(gmc.emergency_department)

        # Distance ranking from Asramam, Kollam (8.8926, 76.5922)
        dist_hosp = Hospital.objects.get(name='District Hospital Kollam')
        dist_km = dist_hosp.distance_from(8.8926, 76.5922)
        self.assertLess(dist_km, 0.5)  # Co-located in Asramam

        tmc = Hospital.objects.get(name='Government Medical College Hospital, Thiruvananthapuram')
        tmc_dist = tmc.distance_from(8.8926, 76.5922)
        self.assertGreater(tmc_dist, 40.0)  # Thiruvananthapuram is ~50 km away



