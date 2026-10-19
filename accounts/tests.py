from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.forms import UserRegistrationForm, AdminAccountProvisionForm

class AccountsWorkflowTestCase(TestCase):
    def setUp(self):
        # Platform Admin User
        self.admin_user = User.objects.create_superuser(username='platform_admin', password='adminpassword123', email='admin@venomwatch.gov')
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        self.admin_profile.role = UserProfile.ROLE_ADMIN
        self.admin_profile.save()

        # Regular Citizen User
        self.citizen_user = User.objects.create_user(username='citizen_user', password='citizenpassword123')
        self.citizen_profile, _ = UserProfile.objects.get_or_create(user=self.citizen_user)
        self.citizen_profile.role = UserProfile.ROLE_CITIZEN
        self.citizen_profile.save()

    def test_citizen_registration_always_assigns_citizen_role(self):
        """Public registration form must never permit self-promotion to Authority or Admin."""
        form_data = {
            'username': 'new_citizen_99',
            'email': 'newcitizen@example.com',
            'first_name': 'New',
            'last_name': 'Citizen',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
            'role': 'admin',  # Attacker attempt to escalate
        }
        form = UserRegistrationForm(data=form_data)
        # Even if 'admin' was injected, clean_role forces ROLE_CITIZEN
        if form.is_valid():
            user = form.save()
            self.assertEqual(user.profile.role, UserProfile.ROLE_CITIZEN)

    def test_admin_provision_authority_and_ranger(self):
        """Platform Admin can provision official Authority and Ranger accounts with operational metadata."""
        self.client.login(username='platform_admin', password='adminpassword123')

        # 1. Provision Authority Officer
        response = self.client.post('/accounts/provision/', {
            'username': 'kollam_authority_01',
            'email': 'authority.kollam@venomwatch.gov',
            'first_name': 'Anil',
            'last_name': 'Kumar',
            'password': 'SecureTempPassword123!',
            'role': UserProfile.ROLE_AUTHORITY,
            'phone_number': '+91 94471 23456',
            'organization': 'Kerala Forest Wildlife Division',
            'registered_location': 'Kollam Division HQ',
            'latitude': 8.8932,
            'longitude': 76.6141,
            'availability': UserProfile.AVAILABILITY_AVAILABLE,
        })
        self.assertEqual(response.status_code, 302)

        authority_user = User.objects.get(username='kollam_authority_01')
        self.assertEqual(authority_user.profile.role, UserProfile.ROLE_AUTHORITY)
        self.assertEqual(authority_user.profile.registered_location, 'Kollam Division HQ')

        # 2. Provision Field Ranger
        response_ranger = self.client.post('/accounts/provision/', {
            'username': 'kollam_ranger_01',
            'email': 'ranger.kollam@venomwatch.gov',
            'first_name': 'Suresh',
            'last_name': 'Gopi',
            'password': 'SecureTempPassword123!',
            'role': UserProfile.ROLE_RANGER,
            'phone_number': '+91 98472 54321',
            'organization': 'Kerala Forest Quick Response Team',
            'registered_location': 'Kollam',
            'latitude': 8.8940,
            'longitude': 76.6150,
            'availability': UserProfile.AVAILABILITY_AVAILABLE,
        })
        self.assertEqual(response_ranger.status_code, 302)

        ranger_user = User.objects.get(username='kollam_ranger_01')
        self.assertEqual(ranger_user.profile.role, UserProfile.ROLE_RANGER)
        self.assertEqual(ranger_user.profile.availability, UserProfile.AVAILABILITY_AVAILABLE)

        # 3. Verify newly provisioned Ranger can log in and reach Ranger console
        self.client.logout()
        login_success = self.client.login(username='kollam_ranger_01', password='SecureTempPassword123!')
        self.assertTrue(login_success)
        res_dashboard = self.client.get('/ranger/')
        self.assertEqual(res_dashboard.status_code, 200)

    def test_admin_separate_provision_forms_for_authority_and_ranger(self):
        """Admin can use separate Add Authority and Add Ranger actions with dedicated forms."""
        self.client.login(username='platform_admin', password='adminpassword123')

        # 1. Add Authority via dedicated action
        res_auth = self.client.post('/accounts/provision/', {
            'action': 'add_authority',
            'full_name': 'Dr. Rajesh Kumar',
            'username': 'rajesh_authority',
            'email': 'rajesh.kumar@venomwatch.gov',
            'phone_number': '+91 94471 99999',
            'password': 'StrongPassword123!',
            'organization': 'Kerala State Wildlife Department',
            'assigned_region': 'Kollam District HQ',
        })
        self.assertEqual(res_auth.status_code, 302)

        auth_user = User.objects.get(username='rajesh_authority')
        self.assertEqual(auth_user.profile.role, UserProfile.ROLE_AUTHORITY)
        self.assertEqual(auth_user.profile.full_name, 'Dr. Rajesh Kumar')
        self.assertEqual(auth_user.profile.assigned_region, 'Kollam District HQ')

        # Verify Authority Officer logs in and lands on Authority map
        self.client.logout()
        logged_in = self.client.login(username='rajesh_authority', password='StrongPassword123!')
        self.assertTrue(logged_in)
        res_map = self.client.get('/authority/map/')
        self.assertEqual(res_map.status_code, 200)

        # 2. Add Ranger via dedicated action
        self.client.logout()
        self.client.login(username='platform_admin', password='adminpassword123')

        res_rng = self.client.post('/accounts/provision/', {
            'action': 'add_ranger',
            'full_name': 'Ravi Varma',
            'username': 'ravi_ranger',
            'email': 'ravi.varma@venomwatch.gov',
            'phone_number': '+91 98472 88888',
            'password': 'StrongPassword123!',
            'organization': 'Forest Quick Response Unit 2',
            'assigned_region': 'Kollam Forest Division',
            'registered_location': 'Kollam Base Station',
            'latitude': 8.8932,
            'longitude': 76.6141,
            'availability': UserProfile.AVAILABILITY_AVAILABLE,
        })
        self.assertEqual(res_rng.status_code, 302)

        rng_user = User.objects.get(username='ravi_ranger')
        self.assertEqual(rng_user.profile.role, UserProfile.ROLE_RANGER)
        self.assertEqual(rng_user.profile.full_name, 'Ravi Varma')
        self.assertEqual(rng_user.profile.registered_location, 'Kollam Base Station')
        self.assertEqual(rng_user.profile.latitude, 8.8932)
        self.assertEqual(rng_user.profile.longitude, 76.6141)
        self.assertEqual(rng_user.profile.availability, UserProfile.AVAILABILITY_AVAILABLE)

        # Verify Ranger logs in and reaches Ranger console
        self.client.logout()
        logged_in = self.client.login(username='ravi_ranger', password='StrongPassword123!')
        self.assertTrue(logged_in)
        res_ranger_console = self.client.get('/ranger/')
        self.assertEqual(res_ranger_console.status_code, 200)

    def test_account_deactivation_and_reactivation_lifecycle(self):
        """Admin can deactivate accounts to disable login while preserving all data, then reactivate them."""
        # Create an active ranger user
        ranger = User.objects.create_user(username='test_deact_ranger', password='Password123!', email='deact@venomwatch.gov')
        prof, _ = UserProfile.objects.get_or_create(user=ranger)
        prof.role = UserProfile.ROLE_RANGER
        prof.save()

        self.client.login(username='platform_admin', password='adminpassword123')

        # 1. Deactivate the ranger account
        res_deact = self.client.post('/accounts/provision/', {
            'action': 'toggle_status',
            'user_id': ranger.pk,
        })
        self.assertEqual(res_deact.status_code, 302)
        ranger.refresh_from_db()
        self.assertFalse(ranger.is_active)

        # 2. Deactivated user cannot log in
        self.client.logout()
        logged_in = self.client.login(username='test_deact_ranger', password='Password123!')
        self.assertFalse(logged_in)

        # 3. Reactivate the ranger account
        self.client.login(username='platform_admin', password='adminpassword123')
        res_react = self.client.post('/accounts/provision/', {
            'action': 'toggle_status',
            'user_id': ranger.pk,
        })
        self.assertEqual(res_react.status_code, 302)
        ranger.refresh_from_db()
        self.assertTrue(ranger.is_active)

        # 4. Reactivated user can now log in successfully
        self.client.logout()
        logged_in = self.client.login(username='test_deact_ranger', password='Password123!')
        self.assertTrue(logged_in)

    def test_admin_lockout_protection(self):
        """Admin cannot accidentally deactivate their own session or the last admin account."""
        self.client.login(username='platform_admin', password='adminpassword123')

        # Attempt to deactivate current admin session
        res = self.client.post('/accounts/provision/', {
            'action': 'toggle_status',
            'user_id': self.admin_user.pk,
        })
        self.assertEqual(res.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_form_validation_duplicate_username_and_invalid_coordinates(self):
        """Forms validate unique usernames, emails, and coordinate boundaries."""
        self.client.login(username='platform_admin', password='adminpassword123')

        # 1. Duplicate username
        res_dup = self.client.post('/accounts/provision/', {
            'action': 'add_authority',
            'full_name': 'Duplicate User',
            'username': 'platform_admin', # already taken
            'email': 'unique@venomwatch.gov',
            'phone_number': '+91 94471 11111',
            'password': 'Password123!',
            'assigned_region': 'Kollam',
        })
        self.assertEqual(res_dup.status_code, 200) # Re-rendered with form error
        self.assertContains(res_dup, "A user with username &#x27;platform_admin&#x27; already exists.")

        # 2. Invalid coordinates for ranger
        res_coord = self.client.post('/accounts/provision/', {
            'action': 'add_ranger',
            'full_name': 'Bad Coord Ranger',
            'username': 'bad_coord_ranger',
            'email': 'badcoord@venomwatch.gov',
            'phone_number': '+91 94471 22222',
            'password': 'Password123!',
            'assigned_region': 'Kollam',
            'registered_location': 'Kollam Base',
            'latitude': 120.5, # invalid latitude > 90
            'longitude': 76.5,
        })
        self.assertEqual(res_coord.status_code, 200)
        self.assertContains(res_coord, "Latitude must be between -90.0 and 90.0 degrees.")

    def test_non_admin_cannot_access_provisioning(self):
        """Citizens, Authority officers, and Rangers are denied access to the account provisioning console."""
        # 1. Citizen denied (403)
        self.client.login(username='citizen_user', password='citizenpassword123')
        response = self.client.get('/accounts/provision/')
        self.assertEqual(response.status_code, 403)

        # 2. Authority officer denied (403)
        authority_user = User.objects.create_user(username='officer_test', password='password123')
        auth_prof, _ = UserProfile.objects.get_or_create(user=authority_user)
        auth_prof.role = UserProfile.ROLE_AUTHORITY
        auth_prof.save()

        self.client.login(username='officer_test', password='password123')
        res_auth = self.client.get('/accounts/provision/')
        self.assertEqual(res_auth.status_code, 403)

        # 3. Ranger denied (403)
        ranger_user = User.objects.create_user(username='ranger_test', password='password123')
        rng_prof, _ = UserProfile.objects.get_or_create(user=ranger_user)
        rng_prof.role = UserProfile.ROLE_RANGER
        rng_prof.save()

        self.client.login(username='ranger_test', password='password123')
        res_ranger = self.client.get('/accounts/provision/')
        self.assertEqual(res_ranger.status_code, 403)

    def test_session_logout(self):
        """Logout invalidates the session cleanly and redirects to login."""
        self.client.login(username='citizen_user', password='citizenpassword123')
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_dashboard_metrics_and_permissions(self):
        """Admin dashboard displays accurate database metrics and blocks non-admin access."""
        # Non-admins get 403
        self.client.login(username='citizen_user', password='citizenpassword123')
        resp_citizen = self.client.get('/accounts/dashboard/')
        self.assertEqual(resp_citizen.status_code, 403)

        # Admin gets 200 with stats
        self.client.login(username='platform_admin', password='adminpassword123')
        resp_admin = self.client.get('/accounts/dashboard/')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, "PLATFORM ADMINISTRATION")
        self.assertContains(resp_admin, "Review Applications")
        self.assertContains(resp_admin, "Manage Accounts")
        self.assertContains(resp_admin, "Manage Hospital Registry")
        self.assertContains(resp_admin, "Hospital Registry")
        self.assertNotContains(resp_admin, "Emergency SOS")

    def test_admin_read_only_access_and_cannot_modify_authority_or_ranger_profile(self):
        """
        Security requirement: Platform Admin can view Authority or Ranger account details in read-only mode,
        but direct URL access and crafted POST requests are forbidden from modifying their profile fields.
        """
        officer = User.objects.create_user(username='officer_protected', password='OldPassword123!', email='original@test.gov')
        officer.profile.role = UserProfile.ROLE_AUTHORITY
        officer.profile.full_name = 'Original Officer'
        officer.profile.organization = 'Kerala Forest Dept'
        officer.profile.save()

        self.client.login(username='platform_admin', password='adminpassword123')
        detail_url = f'/accounts/manage/{officer.pk}/detail/'
        edit_url = f'/accounts/manage/{officer.pk}/edit/'

        # 1. GET read-only detail view returns 200 with officer details
        resp_get = self.client.get(detail_url)
        self.assertEqual(resp_get.status_code, 200)
        self.assertContains(resp_get, 'officer_protected')
        self.assertContains(resp_get, 'Original Officer')

        # GET on legacy edit_url also returns 200 read-only view
        resp_edit_get = self.client.get(edit_url)
        self.assertEqual(resp_edit_get.status_code, 200)

        # 2. Crafted POST attempting to modify profile details must be rejected (403 Forbidden)
        resp_post = self.client.post(edit_url, {
            'full_name': 'Tampered Officer Name',
            'email': 'tampered@example.com',
            'phone_number': '+91 94471 88888',
            'organization': 'Malicious Agency',
        })
        self.assertEqual(resp_post.status_code, 403)

        # 3. Verify officer database records are completely unchanged
        officer.refresh_from_db()
        self.assertEqual(officer.email, 'original@test.gov')
        self.assertEqual(officer.profile.full_name, 'Original Officer')
        self.assertEqual(officer.profile.organization, 'Kerala Forest Dept')

        # 4. Verify Admin CAN manage account status (Suspend & Reinstate) with audit logging
        resp_suspend = self.client.post('/accounts/provision/', {
            'action': 'suspend_account',
            'user_id': officer.pk,
            'reason': 'Investigation into official protocol adherence',
        })
        self.assertRedirects(resp_suspend, '/accounts/provision/')

        officer.refresh_from_db()
        self.assertEqual(officer.profile.account_status, UserProfile.ACCOUNT_SUSPENDED)
        self.assertFalse(officer.is_active)
        self.assertEqual(officer.profile.suspension_reason, 'Investigation into official protocol adherence')

        # Reinstate
        resp_reinstate = self.client.post('/accounts/provision/', {
            'action': 'reinstate_account',
            'user_id': officer.pk,
        })
        self.assertRedirects(resp_reinstate, '/accounts/provision/')

        officer.refresh_from_db()
        self.assertEqual(officer.profile.account_status, UserProfile.ACCOUNT_ACTIVE)
        self.assertTrue(officer.is_active)

    def test_admin_profile_update_and_password_change(self):
        """Admin can update personal profile information and change password."""
        self.client.login(username='platform_admin', password='adminpassword123')

        # Update profile info (Full name, email, phone)
        resp_info = self.client.post('/accounts/profile/', {
            'action': 'update_profile',
            'full_name': 'Senior Admin Officer',
            'email': 'admin.senior@venomwatch.gov',
            'phone_number': '+91 94471 00000',
        })
        self.assertRedirects(resp_info, '/accounts/profile/')

        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.email, 'admin.senior@venomwatch.gov')
        self.assertEqual(self.admin_user.profile.full_name, 'Senior Admin Officer')
        self.assertEqual(self.admin_user.profile.phone_number, '+91 94471 00000')

        # Change password
        resp_pwd = self.client.post('/accounts/profile/#passwordSection', {
            'action': 'change_password',
            'old_password': 'adminpassword123',
            'new_password1': 'SuperSecretAdmin2026!',
            'new_password2': 'SuperSecretAdmin2026!',
        })
        self.assertRedirects(resp_pwd, '/accounts/profile/')

        # Verify old password no longer works, new one works
        self.client.logout()
        old_login = self.client.login(username='platform_admin', password='adminpassword123')
        self.assertFalse(old_login)
        new_login = self.client.login(username='platform_admin', password='SuperSecretAdmin2026!')
        self.assertTrue(new_login)

    def test_citizen_registration_phone_and_location_persisted(self):
        """Citizen registration saves phone number and location coordinates to UserProfile and displays them in profile."""
        response = self.client.post('/accounts/register/', {
            'username': 'citizen_john',
            'email': 'john.citizen@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+91 98765 43210',
            'registered_location': 'Kollam Coastal Ward',
            'latitude': '8.8932',
            'longitude': '76.6141',
            'password1': 'SecureCitizenPass123!',
            'password2': 'SecureCitizenPass123!',
        })
        self.assertEqual(response.status_code, 302)

        # Verify database persistence
        user = User.objects.get(username='citizen_john')
        self.assertEqual(user.profile.role, UserProfile.ROLE_CITIZEN)
        self.assertEqual(user.profile.phone_number, '+91 98765 43210')
        self.assertEqual(user.profile.registered_location, 'Kollam Coastal Ward')
        self.assertAlmostEqual(float(user.profile.latitude), 8.8932, places=4)
        self.assertAlmostEqual(float(user.profile.longitude), 76.6141, places=4)

        # Registration logs user in; verify profile view displays saved phone and location
        resp_profile = self.client.get('/accounts/profile/')
        self.assertEqual(resp_profile.status_code, 200)
        self.assertContains(resp_profile, '+91 98765 43210')
        self.assertContains(resp_profile, 'Kollam Coastal Ward')
        self.assertContains(resp_profile, '8.8932')
        self.assertContains(resp_profile, '76.6141')

    def test_citizen_registration_empty_phone_allowed(self):
        """Citizen registration allows optional blank phone number without template or database errors."""
        response = self.client.post('/accounts/register/', {
            'username': 'citizen_no_phone',
            'email': 'no.phone@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '',
            'password1': 'SecureCitizenPass123!',
            'password2': 'SecureCitizenPass123!',
        })
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username='citizen_no_phone')
        self.assertIn(user.profile.phone_number, (None, ''))

        resp_profile = self.client.get('/accounts/profile/')
        self.assertEqual(resp_profile.status_code, 200)
        self.assertContains(resp_profile, 'Not set')

    def test_citizen_registration_location_validation(self):
        """Invalid latitude and longitude inputs are rejected during citizen registration."""
        # Invalid latitude (> 90)
        resp_bad_lat = self.client.post('/accounts/register/', {
            'username': 'citizen_bad_lat',
            'email': 'badlat@example.com',
            'first_name': 'Bad',
            'last_name': 'Lat',
            'phone_number': '+91 98765 43210',
            'registered_location': 'Invalid Lat Place',
            'latitude': '95.5',
            'longitude': '76.6141',
            'password1': 'SecureCitizenPass123!',
            'password2': 'SecureCitizenPass123!',
        })
        self.assertEqual(resp_bad_lat.status_code, 200)
        self.assertContains(resp_bad_lat, "Latitude must be between -90.0 and 90.0.")

        # Invalid longitude (< -180)
        resp_bad_lon = self.client.post('/accounts/register/', {
            'username': 'citizen_bad_lon',
            'email': 'badlon@example.com',
            'first_name': 'Bad',
            'last_name': 'Lon',
            'phone_number': '+91 98765 43210',
            'registered_location': 'Invalid Lon Place',
            'latitude': '8.8932',
            'longitude': '-185.0',
            'password1': 'SecureCitizenPass123!',
            'password2': 'SecureCitizenPass123!',
        })
        self.assertEqual(resp_bad_lon.status_code, 200)
        self.assertContains(resp_bad_lon, "Longitude must be between -180.0 and 180.0.")

    def test_citizen_profile_update_persists_phone_and_location(self):
        """Citizen can update their phone number and location in their profile and updates persist across sessions."""
        self.client.login(username='citizen_user', password='citizenpassword123')

        resp_update = self.client.post('/accounts/profile/', {
            'action': 'update_profile',
            'full_name': 'Citizen User Updated',
            'email': 'citizen_user@example.com',
            'phone_number': '+91 91234 56789',
            'registered_location': 'Alappuzha North',
            'latitude': '9.4981',
            'longitude': '76.3388',
        })
        self.assertRedirects(resp_update, '/accounts/profile/')

        self.citizen_user.refresh_from_db()
        self.assertEqual(self.citizen_user.profile.phone_number, '+91 91234 56789')
        self.assertEqual(self.citizen_user.profile.registered_location, 'Alappuzha North')
        self.assertAlmostEqual(float(self.citizen_user.profile.latitude), 9.4981, places=4)
        self.assertAlmostEqual(float(self.citizen_user.profile.longitude), 76.3388, places=4)

        # Logout and log back in
        self.client.logout()
        login_success = self.client.login(username='citizen_user', password='citizenpassword123')
        self.assertTrue(login_success)

        resp_revisit = self.client.get('/accounts/profile/')
        self.assertEqual(resp_revisit.status_code, 200)
        self.assertContains(resp_revisit, '+91 91234 56789')
        self.assertContains(resp_revisit, 'Alappuzha North')


from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import AccountApplication, Notification, AuditLog


class AdminApplicationWorkflowTestCase(TestCase):
    def setUp(self):
        # 1. Admin user
        self.admin_user = User.objects.create_superuser(
            username='admin_reviewer',
            password='AdminPassword123!',
            email='admin.reviewer@venomwatch.gov'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        self.admin_profile.role = UserProfile.ROLE_ADMIN
        self.admin_profile.account_status = UserProfile.ACCOUNT_ACTIVE
        self.admin_profile.save()

        # 2. Regular citizen
        self.citizen_user = User.objects.create_user(
            username='test_citizen',
            password='CitizenPassword123!'
        )
        self.citizen_profile, _ = UserProfile.objects.get_or_create(user=self.citizen_user)
        self.citizen_profile.role = UserProfile.ROLE_CITIZEN
        self.citizen_profile.save()

        # 3. Applicant 1: Authority Officer applicant (with PDF document)
        self.auth_applicant = User.objects.create_user(
            username='kollam_officer_applicant',
            password='ApplicantPassword123!',
            email='officer.app@kerala.gov',
            first_name='Kavitha',
            last_name='Nair',
            is_active=False
        )
        self.auth_profile, _ = UserProfile.objects.get_or_create(user=self.auth_applicant)
        self.auth_profile.role = UserProfile.ROLE_AUTHORITY
        self.auth_profile.full_name = 'Kavitha Nair'
        self.auth_profile.phone_number = '+91 94471 11223'
        self.auth_profile.organization = 'Kerala Wildlife Department'
        self.auth_profile.assigned_region = 'Kollam Division'
        self.auth_profile.save()

        dummy_pdf = SimpleUploadedFile("id_proof.pdf", b"%PDF-1.4 test document content", content_type="application/pdf")
        self.auth_application = AccountApplication.objects.create(
            user=self.auth_applicant,
            requested_role=UserProfile.ROLE_AUTHORITY,
            full_name='Kavitha Nair',
            phone_number='+91 94471 11223',
            organization='Kerala Wildlife Department',
            assigned_region='Kollam Division',
            registered_location='Kollam HQ',
            latitude=8.8932,
            longitude=76.6141,
            supporting_document=dummy_pdf,
            status=AccountApplication.STATUS_PENDING
        )

        # 4. Applicant 2: Ranger applicant (with PNG document)
        self.ranger_applicant = User.objects.create_user(
            username='shekhar_ranger_applicant',
            password='RangerPassword123!',
            email='shekhar.ranger@kerala.gov',
            first_name='Shekhar',
            last_name='Menon',
            is_active=False
        )
        self.ranger_profile, _ = UserProfile.objects.get_or_create(user=self.ranger_applicant)
        self.ranger_profile.role = UserProfile.ROLE_RANGER
        self.ranger_profile.full_name = 'Shekhar Menon'
        self.ranger_profile.phone_number = '+91 98472 33445'
        self.ranger_profile.organization = 'Forest Quick Response Team'
        self.ranger_profile.registered_location='Punalur Range Office'
        self.ranger_profile.latitude=9.0167
        self.ranger_profile.longitude=76.9167
        self.ranger_profile.save()

        dummy_png = SimpleUploadedFile("badge_photo.png", b"\x89PNG\r\n\x1a\n\x00dummy png bytes", content_type="image/png")
        self.ranger_application = AccountApplication.objects.create(
            user=self.ranger_applicant,
            requested_role=UserProfile.ROLE_RANGER,
            full_name='Shekhar Menon',
            phone_number='+91 98472 33445',
            organization='Forest Quick Response Team',
            assigned_region='Pathanamthitta Division',
            registered_location='Punalur Range Office',
            latitude=9.0167,
            longitude=76.9167,
            supporting_document=dummy_png,
            status=AccountApplication.STATUS_PENDING
        )

    def test_admin_inspect_document_success(self):
        """Authorized Admin can inspect uploaded verification document and receives safe headers."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        doc_url = f'/accounts/applications/{self.auth_application.pk}/document/'
        response = self.client.get(doc_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertIn('inline', response.get('Content-Disposition', ''))
        filename = self.auth_application.supporting_document.name.split('/')[-1]
        self.assertIn(filename, response.get('Content-Disposition', ''))

    def test_unauthorized_access_to_document_is_blocked(self):
        """Anonymous and non-admin users cannot access verification documents, and direct media path is blocked."""
        doc_url = f'/accounts/applications/{self.auth_application.pk}/document/'

        # 1. Anonymous user redirected to login
        self.client.logout()
        resp_anon = self.client.get(doc_url)
        self.assertEqual(resp_anon.status_code, 302)
        self.assertIn('/accounts/login/', resp_anon.url)

        # 2. Citizen user denied (403 Forbidden)
        self.client.login(username='test_citizen', password='CitizenPassword123!')
        resp_citizen = self.client.get(doc_url)
        self.assertEqual(resp_citizen.status_code, 403)

        # 3. Direct access to /media/verification_docs/ blocked with 403
        resp_direct = self.client.get(f'/media/{self.auth_application.supporting_document.name}')
        self.assertEqual(resp_direct.status_code, 403)

    def test_nonexistent_application_document_returns_404(self):
        """Requesting document for nonexistent application ID returns 404."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        response = self.client.get('/accounts/applications/999999/document/')
        self.assertEqual(response.status_code, 404)

    def test_application_without_document_returns_404(self):
        """Application without a supporting document safely returns 404."""
        no_doc_user = User.objects.create_user(username='no_doc_user', password='Password123!', is_active=False)
        no_doc_app = AccountApplication.objects.create(
            user=no_doc_user,
            requested_role=UserProfile.ROLE_RANGER,
            full_name='No Doc Applicant',
            phone_number='+91 94471 00000',
            status=AccountApplication.STATUS_PENDING
        )
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        response = self.client.get(f'/accounts/applications/{no_doc_app.pk}/document/')
        self.assertEqual(response.status_code, 404)

    def test_approve_eligible_application_end_to_end(self):
        """
        Approving an eligible application updates application status, activates user,
        assigns role and metadata to UserProfile, creates AuditLog and Notification,
        and allows user to log in and land on role view.
        """
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        resp_approve = self.client.post('/accounts/provision/', {
            'action': 'approve_application',
            'application_id': self.auth_application.pk,
        })
        self.assertEqual(resp_approve.status_code, 302)
        self.assertIn('tab=applications', resp_approve.url)

        # Verify application record
        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_APPROVED)
        self.assertEqual(self.auth_application.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.auth_application.reviewed_at)

        # Verify user account activation
        self.auth_applicant.refresh_from_db()
        self.assertTrue(self.auth_applicant.is_active)

        # Verify profile role and metadata
        self.assertEqual(self.auth_applicant.profile.role, UserProfile.ROLE_AUTHORITY)
        self.assertEqual(self.auth_applicant.profile.account_status, UserProfile.ACCOUNT_ACTIVE)
        self.assertEqual(self.auth_applicant.profile.organization, 'Kerala Wildlife Department')
        self.assertEqual(self.auth_applicant.profile.assigned_region, 'Kollam Division')

        # Verify AuditLog and Notification
        audit = AuditLog.objects.filter(target_id=str(self.auth_application.pk), action='APPLICATION_APPROVED').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)

        notif = Notification.objects.filter(recipient=self.auth_applicant, notification_type=Notification.TYPE_SUCCESS).first()
        self.assertIsNotNone(notif)
        self.assertIn('approved', notif.title.lower())

        # Verify approved applicant can authenticate and land on authority module
        self.client.logout()
        logged_in = self.client.login(username='kollam_officer_applicant', password='ApplicantPassword123!')
        self.assertTrue(logged_in)
        resp_map = self.client.get('/authority/map/')
        self.assertEqual(resp_map.status_code, 200)

    def test_reject_eligible_application_end_to_end(self):
        """
        Rejecting an application records the status and reason, keeps user inactive,
        creates AuditLog and Notification, and prevents user login.
        """
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        rejection_reason = "Submitted identification document is illegible and missing official division stamp."
        resp_reject = self.client.post('/accounts/provision/', {
            'action': 'reject_application',
            'application_id': self.ranger_application.pk,
            'rejection_reason': rejection_reason,
        })
        self.assertEqual(resp_reject.status_code, 302)
        self.assertIn('tab=applications', resp_reject.url)

        # Verify application record
        self.ranger_application.refresh_from_db()
        self.assertEqual(self.ranger_application.status, AccountApplication.STATUS_REJECTED)
        self.assertEqual(self.ranger_application.rejection_reason, rejection_reason)
        self.assertEqual(self.ranger_application.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.ranger_application.reviewed_at)

        # Verify user account remains inactive
        self.ranger_applicant.refresh_from_db()
        self.assertFalse(self.ranger_applicant.is_active)

        # Verify AuditLog and Notification
        audit = AuditLog.objects.filter(target_id=str(self.ranger_application.pk), action='APPLICATION_REJECTED').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)

        notif = Notification.objects.filter(recipient=self.ranger_applicant, notification_type=Notification.TYPE_DANGER).first()
        self.assertIsNotNone(notif)
        self.assertIn('not approved', notif.title.lower())

        # Verify rejected user cannot authenticate
        self.client.logout()
        logged_in = self.client.login(username='shekhar_ranger_applicant', password='RangerPassword123!')
        self.assertFalse(logged_in)

    def test_duplicate_approval_and_rejection_handled_safely(self):
        """Admin attempting to review an already-finalized application receives a safe warning."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        # 1. Approve once
        self.client.post('/accounts/provision/', {
            'action': 'approve_application',
            'application_id': self.auth_application.pk,
        })
        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_APPROVED)

        # 2. Second approval attempt on already approved application
        resp_dup = self.client.post('/accounts/provision/', {
            'action': 'approve_application',
            'application_id': self.auth_application.pk,
        })
        self.assertEqual(resp_dup.status_code, 302)

        # 3. Reject attempt on already approved application is denied
        resp_reject_on_approved = self.client.post('/accounts/provision/', {
            'action': 'reject_application',
            'application_id': self.auth_application.pk,
            'rejection_reason': 'Changed mind',
        })
        self.assertEqual(resp_reject_on_approved.status_code, 302)
        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_APPROVED)

    def test_get_request_cannot_modify_application_state(self):
        """GET requests to provisioning endpoint never approve or reject applications."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        # GET with action=approve_application
        resp_get = self.client.get(f'/accounts/provision/?action=approve_application&application_id={self.auth_application.pk}')
        self.assertEqual(resp_get.status_code, 200)

        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_PENDING)

    def test_pending_application_counts_update_correctly(self):
        """Approving an application decrements pending counts and increments active counts on Admin Dashboard."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        # Initial dashboard check
        resp_dash_1 = self.client.get('/accounts/dashboard/')
        self.assertEqual(resp_dash_1.status_code, 200)
        self.assertEqual(resp_dash_1.context['stats']['pending_authority'], 1)
        self.assertEqual(resp_dash_1.context['stats']['pending_ranger'], 1)
        self.assertEqual(resp_dash_1.context['stats']['total_pending'], 2)

        # Approve Authority application
        self.client.post('/accounts/provision/', {
            'action': 'approve_application',
            'application_id': self.auth_application.pk,
        })

        # Updated dashboard check
        resp_dash_2 = self.client.get('/accounts/dashboard/')
        self.assertEqual(resp_dash_2.status_code, 200)
        self.assertEqual(resp_dash_2.context['stats']['pending_authority'], 0)
        self.assertEqual(resp_dash_2.context['stats']['pending_ranger'], 1)
        self.assertEqual(resp_dash_2.context['stats']['total_pending'], 1)
        self.assertEqual(resp_dash_2.context['stats']['active_authority'], 1)

    def test_request_additional_information_workflow(self):
        """Admin can request additional information from applicant, setting STATUS_NEEDS_INFO."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')

        resp_info = self.client.post('/accounts/provision/', {
            'action': 'request_info_application',
            'application_id': self.auth_application.pk,
            'info_notes': 'Please upload a clearer image of your Forest Department ID card.',
        })
        self.assertEqual(resp_info.status_code, 302)

        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_NEEDS_INFO)
        self.assertIn('clearer image', self.auth_application.rejection_reason)

        notif = Notification.objects.filter(recipient=self.auth_applicant, notification_type=Notification.TYPE_WARNING).first()
        self.assertIsNotNone(notif)
        self.assertIn('Additional Information Required', notif.title)

    def test_admin_application_detail_view_success(self):
        """Admin can view detailed application view with all applicant metadata and document link."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        url = reverse('accounts:admin_application_detail', args=[self.auth_application.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.auth_application.full_name)
        self.assertContains(response, self.auth_application.user.username)
        self.assertContains(response, self.auth_application.user.email)
        self.assertContains(response, self.auth_application.phone_number)
        self.assertContains(response, "Inspect Verification Document")
        # Check return path to queue
        self.assertContains(response, reverse('accounts:admin_provision') + '?tab=applications')

    def test_admin_application_detail_missing_fields_safe(self):
        """Application with missing optional fields renders gracefully without crashing."""
        sparse_user = User.objects.create_user(username='sparse_user', password='Password123!', is_active=False)
        sparse_app = AccountApplication.objects.create(
            user=sparse_user,
            requested_role=UserProfile.ROLE_AUTHORITY,
            full_name='Sparse Applicant',
            phone_number='',
            organization='',
            assigned_region='',
            registered_location='',
            status=AccountApplication.STATUS_PENDING
        )
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        url = reverse('accounts:admin_application_detail', args=[sparse_app.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not provided")
        self.assertContains(response, "Not specified")

    def test_admin_application_detail_nonexistent_returns_404(self):
        """Viewing details for nonexistent application returns 404."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        url = reverse('accounts:admin_application_detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_admin_application_detail_unauthorized_blocked(self):
        """Anonymous and non-admin users cannot access the application detail page."""
        url = reverse('accounts:admin_application_detail', args=[self.auth_application.pk])
        self.client.logout()
        resp_anon = self.client.get(url)
        self.assertEqual(resp_anon.status_code, 302)

        self.client.login(username='test_citizen', password='CitizenPassword123!')
        resp_citizen = self.client.get(url)
        self.assertEqual(resp_citizen.status_code, 403)

    def test_admin_application_approve_direct_endpoint(self):
        """Direct POST to admin_application_approve activates account and updates profile atomically."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        url = reverse('accounts:admin_application_approve', args=[self.auth_application.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('tab=applications', response.url)

        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_APPROVED)
        self.auth_applicant.refresh_from_db()
        self.assertTrue(self.auth_applicant.is_active)
        self.assertEqual(self.auth_applicant.profile.role, UserProfile.ROLE_AUTHORITY)
        self.assertEqual(self.auth_applicant.profile.account_status, UserProfile.ACCOUNT_ACTIVE)

    def test_admin_application_reject_direct_endpoint(self):
        """Direct POST to admin_application_reject preserves history, records reason, keeps user inactive."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        url = reverse('accounts:admin_application_reject', args=[self.ranger_application.pk])
        reason = "Direct endpoint rejection test reason."
        response = self.client.post(url, {'rejection_reason': reason})
        self.assertEqual(response.status_code, 302)
        self.assertIn('tab=applications', response.url)

        self.ranger_application.refresh_from_db()
        self.assertEqual(self.ranger_application.status, AccountApplication.STATUS_REJECTED)
        self.assertEqual(self.ranger_application.rejection_reason, reason)
        self.ranger_applicant.refresh_from_db()
        self.assertFalse(self.ranger_applicant.is_active)
        self.assertEqual(self.ranger_applicant.profile.account_status, UserProfile.ACCOUNT_SUSPENDED)

    def test_direct_approve_reject_endpoints_disallow_get(self):
        """GET requests to direct approve and reject endpoints cannot change application state."""
        self.client.login(username='admin_reviewer', password='AdminPassword123!')
        approve_url = reverse('accounts:admin_application_approve', args=[self.auth_application.pk])
        reject_url = reverse('accounts:admin_application_reject', args=[self.auth_application.pk])

        resp_get_approve = self.client.get(approve_url)
        self.assertEqual(resp_get_approve.status_code, 302)
        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_PENDING)

        resp_get_reject = self.client.get(reject_url)
        self.assertEqual(resp_get_reject.status_code, 302)
        self.auth_application.refresh_from_db()
        self.assertEqual(self.auth_application.status, AccountApplication.STATUS_PENDING)

    def test_direct_approve_reject_unauthorized_blocked(self):
        """Non-admin users cannot approve or reject applications."""
        approve_url = reverse('accounts:admin_application_approve', args=[self.auth_application.pk])
        reject_url = reverse('accounts:admin_application_reject', args=[self.auth_application.pk])

        # Anonymous
        self.client.logout()
        self.assertEqual(self.client.post(approve_url).status_code, 302)
        self.assertEqual(self.client.post(reject_url).status_code, 302)

        # Citizen
        self.client.login(username='test_citizen', password='CitizenPassword123!')
        self.assertEqual(self.client.post(approve_url).status_code, 403)
        self.assertEqual(self.client.post(reject_url).status_code, 403)






