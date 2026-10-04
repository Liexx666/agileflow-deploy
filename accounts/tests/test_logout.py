from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class LogoutTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="logout_test",
            email="logout@example.com",
            password="TestPassword123!",
        )

        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.backlog_url = reverse("backlog:product_backlog")

        self.client.force_login(self.user)

    def test_logout_button_is_visible_when_logged_in(self):
        response = self.client.get(self.backlog_url)

        self.assertContains(response, "Log out")
        self.assertContains(response, f'action="{self.logout_url}"')

    def test_logout_clears_session_and_redirects(self):
        session = self.client.session
        session["test_marker"] = "saved before logout"
        session.save()

        response = self.client.post(self.logout_url)

        self.assertRedirects(response, self.login_url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn("test_marker", self.client.session)

        response = self.client.get(self.backlog_url)
        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.backlog_url}",
        )

    def test_logout_button_is_hidden_when_logged_out(self):
        self.client.logout()

        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Log out")

    def test_get_request_does_not_log_user_out(self):
        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.user.pk),
        )

    def test_logout_requires_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        # Open the page to obtain its CSRF cookie.
        page = client.get(self.backlog_url)
        self.assertEqual(page.status_code, 200)
        token = client.cookies["csrftoken"].value

        # A request without a token must not log the user out.
        response = client.post(self.logout_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            client.session.get("_auth_user_id"),
            str(self.user.pk),
        )

        # A request with a valid token should log the user out.
        response = client.post(
            self.logout_url,
            {"csrfmiddlewaretoken": token},
        )

        self.assertRedirects(response, self.login_url)
        self.assertNotIn("_auth_user_id", client.session)
