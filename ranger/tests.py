import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import UserProfile, AccountApplication, Notification, AuditLog
from reports.models import SightingReport, RangerAssignment
from reports.dispatch import get_candidate_rangers


def create_test_image():
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='green')
    image.save(file, 'JPEG')
    file.seek(0)
    return SimpleUploadedFile("evidence.jpg", file.read(), content_type="image/jpeg")


class RangerWorkflowAndSecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser('admin_user', 'admin@example.com', 'AdminPass123!')
        self.admin.profile.role = UserProfile.ROLE_ADMIN
        self.admin.profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.admin.profile.save()

        # Authority user
        self.authority = User.objects.create_user('authority_officer', 'auth@example.com', 'AuthPass123!')
        self.authority.profile.role = UserProfile.ROLE_AUTHORITY
        self.authority.profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.authority.profile.save()

        # Approved Ranger 1 (Kollam)
        self.ranger1 = User.objects.create_user('ranger_kollam', 'ranger1@example.com', 'RangerPass123!')
        self.ranger1.profile.role = UserProfile.ROLE_RANGER
        self.ranger1.profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.ranger1.profile.availability = UserProfile.AVAILABILITY_AVAILABLE
        self.ranger1.profile.registered_location = 'Kollam'
        self.ranger1.profile.latitude = 8.8932
        self.ranger1.profile.longitude = 76.6141
        self.ranger1.profile.save()

        # Approved Ranger 2 (Thiruvananthapuram)
        self.ranger2 = User.objects.create_user('ranger_tvm', 'ranger2@example.com', 'RangerPass123!')
        self.ranger2.profile.role = UserProfile.ROLE_RANGER
        self.ranger2.profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.ranger2.profile.availability = UserProfile.AVAILABILITY_AVAILABLE
        self.ranger2.profile.registered_location = 'Thiruvananthapuram'
        self.ranger2.profile.latitude = 8.5241
        self.ranger2.profile.longitude = 76.9366
        self.ranger2.profile.save()

        # Citizen user
        self.citizen = User.objects.create_user('citizen_user', 'citizen@example.com', 'CitizenPass123!')
        self.citizen.profile.role = UserProfile.ROLE_CITIZEN
        self.citizen.profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.citizen.profile.save()

        # Incident sighting in Kollam
        self.sighting = SightingReport.objects.create(
            user=self.citizen,
            title="Spectacled Cobra Sighting",
            location_name="Kollam Town",
            latitude=8.8940,
            longitude=76.6150,
            status=SightingReport.STATUS_PENDING,
        )

    def test_eligible_rangers_dispatch_recommendation_without_dummy_data(self):
        """Only genuine approved, active, available rangers are recommended using real Haversine distance."""
        # Default 30 km radius returns only nearby Kollam ranger
        candidates_30km = get_candidate_rangers(self.sighting, only_available=True)
        self.assertEqual(len(candidates_30km), 1)
        self.assertEqual(candidates_30km[0]['user'], self.ranger1)
        self.assertLess(candidates_30km[0]['distance_km'], 1.0)

        # Extended 100 km radius returns both Kollam and TVM rangers, sorted by distance
        candidates_100km = get_candidate_rangers(self.sighting, only_available=True, radius_km=100)
        self.assertEqual(len(candidates_100km), 2)
        self.assertEqual(candidates_100km[0]['user'], self.ranger1)
        self.assertEqual(candidates_100km[1]['user'], self.ranger2)
        self.assertGreater(candidates_100km[1]['distance_km'], 40.0)

        # Suspended ranger must NOT appear in recommendations
        self.ranger1.profile.account_status = UserProfile.ACCOUNT_SUSPENDED
        self.ranger1.profile.save()
        candidates_after_suspend = get_candidate_rangers(self.sighting, only_available=True, radius_km=100)
        self.assertEqual(len(candidates_after_suspend), 1)
        self.assertEqual(candidates_after_suspend[0]['user'], self.ranger2)

    def test_ranger_assignment_isolation_and_acceptance(self):
        """Rangers only access their assigned tasks. Citizen only sees ranger name after acceptance."""
        assignment = RangerAssignment.objects.create(
            sighting=self.sighting,
            ranger=self.ranger1,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Other ranger cannot access this assignment detail
        self.client.login(username='ranger_tvm', password='RangerPass123!')
        res_other = self.client.get(f'/ranger/assignments/{assignment.pk}/')
        self.assertEqual(res_other.status_code, 404)
        self.client.logout()

        # Citizen views sighting before ranger acceptance: Ranger name must NOT appear
        self.client.login(username='citizen_user', password='CitizenPass123!')
        res_citizen_pre = self.client.get(f'/reports/{self.sighting.pk}/')
        self.assertEqual(res_citizen_pre.status_code, 200)
        self.assertNotContains(res_citizen_pre, "ranger_kollam")
        self.assertContains(res_citizen_pre, "Awaiting Acceptance")
        self.client.logout()

        # Assigned ranger logs in and accepts assignment
        self.client.login(username='ranger_kollam', password='RangerPass123!')
        res_accept = self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'ACCEPT'})
        self.assertEqual(res_accept.status_code, 302)

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ACCEPTED)
        self.assertIsNotNone(assignment.responded_at)
        self.client.logout()

        # Now Citizen views sighting: Ranger display name appears
        self.client.login(username='citizen_user', password='CitizenPass123!')
        res_citizen_post = self.client.get(f'/reports/{self.sighting.pk}/')
        self.assertEqual(res_citizen_post.status_code, 200)
        self.assertContains(res_citizen_post, "ranger_kollam")
        self.client.logout()

    def test_complete_field_response_and_authority_verification_lifecycle(self):
        """Full lifecycle: Accept -> On the way -> At location -> Submit outcome -> Authority verification."""
        assignment = RangerAssignment.objects.create(
            sighting=self.sighting,
            ranger=self.ranger1,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        self.client.login(username='ranger_kollam', password='RangerPass123!')

        # 1. Accept
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'ACCEPT'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ACCEPTED)

        # 2. On the way
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'ON_THE_WAY'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_ON_THE_WAY)

        # 3. At location
        self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'AT_LOCATION'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_AT_LOCATION)

        # 4. Ranger CANNOT self-complete; must submit outcome with evidence
        res_illegal = self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {'action': 'COMPLETE'})
        self.assertEqual(res_illegal.status_code, 302)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_AT_LOCATION) # Unchanged

        # 5. Submit Outcome with evidence photo
        img = create_test_image()
        res_submit = self.client.post(f'/ranger/assignments/{assignment.pk}/update/', {
            'action': 'SUBMIT_OUTCOME',
            'outcome': RangerAssignment.OUTCOME_CAPTURED,
            'notes': 'Spectacled cobra safely captured in secure rescue bag.',
            'outcome_image': img
        })
        self.assertEqual(res_submit.status_code, 302)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_OUTCOME_SUBMITTED)
        self.assertIsNotNone(assignment.outcome_image)
        self.client.logout()

        # At this stage, Citizen sees 'Awaiting Authority Review', NOT confirmed capture
        self.client.login(username='citizen_user', password='CitizenPass123!')
        res_citizen_submitted = self.client.get(f'/reports/{self.sighting.pk}/')
        self.assertContains(res_citizen_submitted, "Awaiting Authority Review")
        self.client.logout()

        # 6. Authority verifies outcome: APPROVED
        self.client.login(username='authority_officer', password='AuthPass123!')
        res_verify = self.client.post(f'/reports/assignments/{assignment.pk}/review/', {
            'decision': 'APPROVED',
            'review_notes': 'Verified photo and rescue coordinates match standard protocols.'
        })
        self.assertEqual(res_verify.status_code, 302)

        assignment.refresh_from_db()
        self.sighting.refresh_from_db()
        self.assertEqual(assignment.status, RangerAssignment.STATUS_COMPLETED)
        self.assertEqual(self.sighting.status, SightingReport.STATUS_RESOLVED)
        self.client.logout()

        # 7. Citizen checks verified outcome
        self.client.login(username='citizen_user', password='CitizenPass123!')
        res_citizen_final = self.client.get(f'/reports/{self.sighting.pk}/')
        self.assertContains(res_citizen_final, "Verified Incident Resolution")
        self.assertContains(res_citizen_final, "Snake Safely Captured")
        self.assertContains(res_citizen_final, "Approved Response Evidence Photo")

        # Citizen also has in-app notification
        notifications = Notification.objects.filter(recipient=self.citizen)
        self.assertTrue(notifications.exists())
        self.assertTrue(notifications.filter(notification_type=Notification.TYPE_OUTCOME_VERIFIED).exists())

    def test_suspended_ranger_blocked_from_protected_operations(self):
        """Suspended or banned ranger cannot access ranger dashboard or perform assignment actions."""
        self.ranger1.profile.account_status = UserProfile.ACCOUNT_SUSPENDED
        self.ranger1.profile.suspension_reason = "Under disciplinary review."
        self.ranger1.profile.save()

        self.client.login(username='ranger_kollam', password='RangerPass123!')
        res = self.client.get('/ranger/')
        # Account is suspended -> blocked by middleware or decorator (302 to login or 403)
        self.assertIn(res.status_code, (302, 403))

    def test_ranger_sequential_incident_numbering(self):
        """
        Verify Ranger-specific sequential incident numbering:
        - Numbering starts at #1 independently per Ranger.
        - Ordered by assignment creation time (oldest to newest).
        - Repeated assignments of the same sighting preserve distinct number.
        - Displayed consistently across dashboard, assignments list, and detail views.
        - Does not change database primary key or relations.
        """
        import time

        # Create distinct sightings
        sighting_alpha = SightingReport.objects.create(
            user=self.citizen,
            title="Sighting Alpha",
            location_name="Location Alpha",
            latitude=8.8940,
            longitude=76.6150,
            status=SightingReport.STATUS_PENDING,
        )
        sighting_beta = SightingReport.objects.create(
            user=self.citizen,
            title="Sighting Beta",
            location_name="Location Beta",
            latitude=8.8950,
            longitude=76.6160,
            status=SightingReport.STATUS_PENDING,
        )
        sighting_gamma = SightingReport.objects.create(
            user=self.citizen,
            title="Sighting Gamma",
            location_name="Location Gamma",
            latitude=8.8960,
            longitude=76.6170,
            status=SightingReport.STATUS_PENDING,
        )

        # Assign sighting_beta first to ranger1 -> Ranger 1 Incident #1
        a1_r1 = RangerAssignment.objects.create(
            sighting=sighting_beta,
            ranger=self.ranger1,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Assign sighting_alpha second to ranger1 -> Ranger 1 Incident #2
        a2_r1 = RangerAssignment.objects.create(
            sighting=sighting_alpha,
            ranger=self.ranger1,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Reassign sighting_beta again to ranger1 (reassignment does not count as new distinct sighting)
        a3_r1 = RangerAssignment.objects.create(
            sighting=sighting_beta,
            ranger=self.ranger1,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Assign sighting_gamma to ranger2 as their first assignment -> Ranger 2 Incident #1
        a1_r2 = RangerAssignment.objects.create(
            sighting=sighting_gamma,
            ranger=self.ranger2,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Assign sighting_beta to ranger2 as their second assignment -> Ranger 2 Incident #2
        a2_r2 = RangerAssignment.objects.create(
            sighting=sighting_beta,
            ranger=self.ranger2,
            assigned_by=self.authority,
            status=RangerAssignment.STATUS_ASSIGNED
        )

        # Check model properties and mapping directly
        self.assertEqual(a1_r1.ranger_incident_number, 1)
        self.assertEqual(a2_r1.ranger_incident_number, 2)
        # Repeated assignment of sighting_beta for ranger1 is still incident #1
        self.assertEqual(a3_r1.ranger_incident_number, 1)

        # Check Ranger 2 numbering starts at 1 independently
        self.assertEqual(a1_r2.ranger_incident_number, 1)
        self.assertEqual(a2_r2.ranger_incident_number, 2)

        # Check get_ranger_incident_number on SightingReport
        self.assertEqual(sighting_beta.get_ranger_incident_number(self.ranger1), 1)
        self.assertEqual(sighting_alpha.get_ranger_incident_number(self.ranger1), 2)
        self.assertEqual(sighting_gamma.get_ranger_incident_number(self.ranger2), 1)
        self.assertEqual(sighting_beta.get_ranger_incident_number(self.ranger2), 2)

        # Check UI views for ranger1
        self.client.login(username='ranger_kollam', password='RangerPass123!')

        # 1. Dashboard
        res_dash = self.client.get('/ranger/')
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "Snake Sighting #1")
        self.assertContains(res_dash, "Snake Sighting #2")
        # Ensure the sighting_beta PK is distinct from #1 and that raw PK display pattern is not used
        if sighting_beta.pk != 1:
            self.assertNotContains(res_dash, f"Snake Sighting #{sighting_beta.pk}")

        # 2. Assignment List
        res_list = self.client.get('/ranger/assignments/')
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "Snake Sighting #1")
        self.assertContains(res_list, "Snake Sighting #2")

        # 3. Assignment Detail for Incident #1
        res_detail_1 = self.client.get(f'/ranger/assignments/{a1_r1.pk}/')
        self.assertEqual(res_detail_1.status_code, 200)
        self.assertContains(res_detail_1, "Snake Sighting #1")
        if sighting_beta.pk != 1:
            self.assertNotContains(res_detail_1, f"Snake Sighting #{sighting_beta.pk}")

        # 4. Assignment Detail for Incident #2
        res_detail_2 = self.client.get(f'/ranger/assignments/{a2_r1.pk}/')
        self.assertEqual(res_detail_2.status_code, 200)
        self.assertContains(res_detail_2, "Snake Sighting #2")
        if sighting_alpha.pk != 2:
            self.assertNotContains(res_detail_2, f"Snake Sighting #{sighting_alpha.pk}")

        self.client.logout()
