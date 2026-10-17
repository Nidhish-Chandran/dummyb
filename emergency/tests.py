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
