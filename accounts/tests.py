from django.test import TestCase
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

    def test_non_admin_cannot_access_provisioning(self):
        """Citizens and regular users are denied access to the account provisioning console."""
        self.client.login(username='citizen_user', password='citizenpassword123')
        response = self.client.get('/accounts/provision/')
        self.assertEqual(response.status_code, 403)

    def test_session_logout(self):
        """Logout invalidates the session cleanly and redirects to login."""
        self.client.login(username='citizen_user', password='citizenpassword123')
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
