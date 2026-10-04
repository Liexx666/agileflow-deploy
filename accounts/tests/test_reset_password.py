from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ResetPasswordTests(TestCase):
    """
    Automated unit tests for US-11: Password reset for users.
    Tests all acceptance criteria for resetting a password.
    """

    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="reset_user",
            email="reset@example.com",
            password="OldPassword123!",
        )
        self.reset_url = reverse("accounts:reset_password")
        self.login_url = reverse("accounts:login")
        self.backlog_url = reverse("backlog:product_backlog")

    # -------------------------------------------------------------------------
    # AC1: User can access the password reset function when logged in.
    # -------------------------------------------------------------------------
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

    def test_logged_in_user_can_access_password_reset_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/reset_password.html")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="new_password"')
        self.assertContains(response, 'name="confirm_password"')

    # -------------------------------------------------------------------------
    # AC2: User can only reset their own password (correct email required).
    # -------------------------------------------------------------------------
    def test_user_cannot_reset_with_wrong_email(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "different@example.com",
                "new_password": "NewSecurePass123",
                "confirm_password": "NewSecurePass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "You can only reset your own account password. Please enter your registered email address.",
        )

    # -------------------------------------------------------------------------
    # AC3: Password complexity requirements (8-20 chars, letters and numbers).
    # -------------------------------------------------------------------------
    def test_password_too_short(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "Pass1",
                "confirm_password": "Pass1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password", response.context["form"].errors)

    def test_password_too_long(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "A1" * 15,  # 30 chars
                "confirm_password": "A1" * 15,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password", response.context["form"].errors)

    def test_password_missing_number(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "OnlyLettersHere",
                "confirm_password": "OnlyLettersHere",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "new_password",
            "Password must contain at least one number.",
        )

    def test_password_missing_letter(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "1234567890",
                "confirm_password": "1234567890",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "new_password",
            "Password must contain at least one letter.",
        )

    # -------------------------------------------------------------------------
    # AC4: User can securely set a new password and log in.
    # -------------------------------------------------------------------------
    def test_user_can_set_new_password_securely(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "NewSecurePass123",
                "confirm_password": "NewSecurePass123",
            },
        )
        # Should redirect to login on success
        self.assertRedirects(response, self.login_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass123"))

    def test_passwords_must_match(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "NewSecurePass123",
                "confirm_password": "DifferentPass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "confirm_password",
            "Passwords do not match.",
        )

    def test_existing_password_is_not_displayed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.reset_url)
        self.assertNotContains(response, "OldPassword123!")
        self.assertNotContains(response, self.user.password)

    def test_user_can_login_with_new_password(self):
        self.client.force_login(self.user)
        self.client.post(
            self.reset_url,
            {
                "email": "reset@example.com",
                "new_password": "NewSecurePass123",
                "confirm_password": "NewSecurePass123",
            },
        )
        
        # Try to log in with the old password (should fail)
        login_fail_response = self.client.post(
            self.login_url,
            {
                "email": "reset@example.com",
                "password": "OldPassword123!",
            },
        )
        self.assertContains(login_fail_response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)
        
        # Try to log in with the new password (should succeed)
        login_success_response = self.client.post(
            self.login_url,
            {
                "email": "reset@example.com",
                "password": "NewSecurePass123",
            },
        )
        self.assertRedirects(login_success_response, self.backlog_url)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(self.user.pk),
        )
