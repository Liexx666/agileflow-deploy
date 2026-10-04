from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="login_test",
            email="member@example.com",
            password="TestPassword123!",
        )

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
