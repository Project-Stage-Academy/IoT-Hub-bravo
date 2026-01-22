"""
Admin Smoke Tests

These tests verify that the main admin pages render without errors.
They use Django's test client to simulate HTTP requests.

Run with: python manage.py test apps.users.tests.test_admin_smoke
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.devices.models import Device, Metric, DeviceMetric, Telemetry
from apps.rules.models import Rule, Event

User = get_user_model()


class AdminSmokeTest(TestCase):
    """
    Smoke tests to verify admin pages load without errors.
    Tests login, list pages, and basic navigation.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create test users and sample data once for all tests.
        """
        # Create superuser
        cls.superuser = User.objects.create_superuser(
            username='test_admin',
            email='test_admin@example.com',
            password='testpass123'
        )

        # Create regular user for device ownership
        cls.regular_user = User.objects.create_user(
            username='test_regular',
            email='test_regular@example.com',
            password='testpass123'
        )
        cls.regular_user.is_staff = True
        cls.regular_user.save()

        # Create test device
        cls.device = Device.objects.create(
            serial_id='SN-SMOKE-001',
            name='Smoke Test Device',
            description='Device for smoke testing',
            user=cls.regular_user,
            is_active=True
        )

        # Create test metric
        cls.metric = Metric.objects.create(
            metric_type='temperature',
            data_type='numeric'
        )

        # Create device-metric association
        cls.device_metric = DeviceMetric.objects.create(
            device=cls.device,
            metric=cls.metric
        )

        # Create test telemetry
        cls.telemetry = Telemetry.objects.create(
            device_metric=cls.device_metric,
            value_jsonb={'t': 'numeric', 'v': '25.5'}
        )

        # Create test rule
        cls.rule = Rule.objects.create(
            name='Smoke Test Rule',
            description='Rule for smoke testing',
            device_metric=cls.device_metric,
            condition={'type': 'threshold', 'value': 30},
            action={'type': 'log', 'message': 'Test'},
            is_active=True
        )

        # Create test event
        cls.event = Event.objects.create(
            rule=cls.rule
        )

    def setUp(self):
        """
        Create a client and login before each test.
        """
        self.client = Client()
        self.client.login(username='test_admin', password='testpass123')

    def test_admin_login_page_loads(self):
        """
        Test that admin login page renders successfully.
        """
        self.client.logout()
        response = self.client.get('/admin/login/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django administration')

    def test_admin_login_success(self):
        """
        Test that login with valid credentials works.
        """
        self.client.logout()
        response = self.client.post('/admin/login/', {
            'username': 'test_admin',
            'password': 'testpass123',
            'next': '/admin/'
        })

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/', response.url)

    def test_admin_index_page_loads(self):
        """
        Test that admin index/dashboard page loads.
        """
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Site administration')
        self.assertContains(response, 'Devices')
        self.assertContains(response, 'Users')

    def test_devices_list_page_loads(self):
        """
        Test that devices admin list page renders.
        """
        response = self.client.get('/admin/devices/device/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select device to change')
        self.assertContains(response, 'Smoke Test Device')

    def test_device_detail_page_loads(self):
        """
        Test that device detail/edit page renders.
        """
        url = f'/admin/devices/device/{self.device.id}/change/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SN-SMOKE-001')
        self.assertContains(response, 'Smoke Test Device')

    def test_device_add_page_loads(self):
        """
        Test that add device page renders.
        """
        response = self.client.get('/admin/devices/device/add/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add device')

    def test_telemetry_list_page_loads(self):
        """
        Test that telemetry admin list page renders.
        """
        response = self.client.get('/admin/devices/telemetry/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select telemetry to change')

    def test_telemetry_detail_page_loads(self):
        """
        Test that telemetry detail page renders.
        """
        url = f'/admin/devices/telemetry/{self.telemetry.id}/change/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_metrics_list_page_loads(self):
        """
        Test that metrics admin list page renders.
        """
        response = self.client.get('/admin/devices/metric/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select metric to change')
        self.assertContains(response, 'temperature')

    def test_device_metrics_list_page_loads(self):
        """
        Test that device metrics admin list page renders.
        """
        response = self.client.get('/admin/devices/devicemetric/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select device metric to change')

    def test_rules_list_page_loads(self):
        """
        Test that rules admin list page renders.
        """
        response = self.client.get('/admin/rules/rule/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select rule to change')
        self.assertContains(response, 'Smoke Test Rule')

    def test_rule_detail_page_loads(self):
        """
        Test that rule detail page renders.
        """
        url = f'/admin/rules/rule/{self.rule.id}/change/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smoke Test Rule')

    def test_rule_add_page_loads(self):
        """
        Test that add rule page renders.
        """
        response = self.client.get('/admin/rules/rule/add/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add rule')

    def test_events_list_page_loads(self):
        """
        Test that events admin list page renders.
        """
        response = self.client.get('/admin/rules/event/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select event to change')

    def test_event_detail_page_loads(self):
        """
        Test that event detail page renders.
        """
        url = f'/admin/rules/event/{self.event.id}/change/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_users_list_page_loads(self):
        """
        Test that users admin list page renders.
        """
        response = self.client.get('/admin/users/user/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select user to change')
        self.assertContains(response, 'test_admin')

    def test_admin_logout_works(self):
        """
        Test that logout functionality works.
        """
        # Logout requires POST in newer Django versions
        response = self.client.post('/admin/logout/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged out')

    def test_device_search_works(self):
        """
        Test that device search returns results.
        """
        response = self.client.get('/admin/devices/device/?q=SMOKE')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smoke Test Device')

    def test_device_filter_by_active_works(self):
        """
        Test that filtering devices by active status works.
        """
        response = self.client.get('/admin/devices/device/?is_active__exact=1')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smoke Test Device')

    def test_rule_list_renders(self):
        """
        Test that rule list page renders.
        """
        response = self.client.get('/admin/rules/rule/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smoke Test Rule')

    def test_device_enable_action_works(self):
        """
        Test that enable devices admin action works.
        """
        # First disable the device
        self.device.is_active = False
        self.device.save()

        # Use admin action to enable
        response = self.client.post('/admin/devices/device/', {
            'action': 'enable_devices',
            '_selected_action': [self.device.id]
        })

        self.device.refresh_from_db()
        self.assertTrue(self.device.is_active)


class AdminPermissionsTest(TestCase):
    """
    Test that non-staff users cannot access admin.
    """

    def setUp(self):
        """
        Create a non-staff user.
        """
        self.user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        self.client = Client()

    def test_non_staff_user_cannot_access_admin(self):
        """
        Test that regular users are redirected from admin.
        """
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get('/admin/')

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_anonymous_user_redirected_to_login(self):
        """
        Test that anonymous users are redirected to login.
        """
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
