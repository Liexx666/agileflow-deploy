from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountSecurity


class LoginTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="login_test",
            email="member@example.com",
            password="TestPassword123!",
        )
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)

        self.login_url = reverse("accounts:login")
        self.backlog_url = reverse("backlog:product_backlog")

    def test_login_page_displays_email_and_password(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'type="password"')

    def test_valid_login_redirects_to_backlog(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "member@example.com",
                "password": "TestPassword123!",
            },
        )

        self.assertRedirects(response, self.backlog_url)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.user.pk),
        )

    def test_invalid_password_displays_error(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "member@example.com",
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_valid_login_with_username_redirects_to_backlog(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "login_test",
                "password": "TestPassword123!",
            },
        )

        self.assertRedirects(response, self.backlog_url)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.user.pk),
        )

    def test_nonexistent_user_displays_error(self):
        response = self.client.post(
            self.login_url,
            {
                "email": "nonexistent_user@example.com",
                "password": "AnyPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_first_time_login_with_default_password_redirects_to_change_password(self):
        User = get_user_model()
        new_user = User.objects.create_user(
            username="new_member",
            email="new_member@example.com",
            password="password123",
        )
        AccountSecurity.objects.update_or_create(user=new_user, defaults={"must_change_password": True})
        response = self.client.post(
            self.login_url,
            {
                "email": "new_member@example.com",
                "password": "password123",
            },
        )
        self.assertRedirects(response, reverse("accounts:change_password"))
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(new_user.pk),
        )

    def test_first_time_login_user_blocked_from_other_pages_until_password_changed(self):
        User = get_user_model()
        new_user = User.objects.create_user(
            username="blocked_member",
            email="blocked@example.com",
            password="password123",
        )
        AccountSecurity.objects.update_or_create(user=new_user, defaults={"must_change_password": True})
        self.client.login(username="blocked_member", password="password123")
        response = self.client.get(self.backlog_url)
        self.assertRedirects(response, reverse("accounts:change_password"))

    def test_successful_password_change_enables_normal_access(self):
        User = get_user_model()
        new_user = User.objects.create_user(
            username="changed_member",
            email="changed@example.com",
            password="password123",
        )
        AccountSecurity.objects.update_or_create(user=new_user, defaults={"must_change_password": True})
        self.client.login(username="changed_member", password="password123")
        change_url = reverse("accounts:change_password")

        # Submit new valid password
        response = self.client.post(
            change_url,
            {
                "old_password": "password123",
                "new_password1": "SecurePass2026",
                "new_password2": "SecurePass2026",
            },
        )
        self.assertRedirects(response, reverse("backlog:home"), target_status_code=302)

        # Verify password updated and security flag cleared
        new_user.refresh_from_db()
        self.assertTrue(new_user.check_password("SecurePass2026"))
        self.assertFalse(new_user.account_security.must_change_password)

        # Direct access to backlog is now allowed
        backlog_res = self.client.get(self.backlog_url)
        self.assertEqual(backlog_res.status_code, 200)


