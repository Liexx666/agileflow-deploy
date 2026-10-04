from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountSecurity


class RegisterAccountTests(TestCase):
    """
    Automated unit tests for US-33: Registering a new account.
    Tests all acceptance criteria for admin user registration.
    """

    def setUp(self):
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
        )
        AccountSecurity.objects.filter(user=self.admin_user).update(must_change_password=False)

        self.regular_user = self.User.objects.create_user(
            username="regular_member",
            email="member@example.com",
            password="MemberPassword123!",
            first_name="Regular",
            last_name="Member",
            is_staff=False,
            is_superuser=False,
        )
        AccountSecurity.objects.filter(user=self.regular_user).update(must_change_password=False)

        self.register_url = reverse("accounts:register_account")
        self.user_accounts_url = reverse("accounts:user_accounts")
        self.login_url = reverse("accounts:login")
        self.backlog_url = reverse("backlog:product_backlog")

        self.valid_registration_data = {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@example.com",
            "username": "alicesmith",
            "role": "member",
            "status": "active",
        }

    # -------------------------------------------------------------------------
    # AC1: Only the Admin can access the user registration function.
    # -------------------------------------------------------------------------

    def test_anonymous_user_cannot_access_register_page(self):
        response = self.client.get(self.register_url)
        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.register_url}",
        )

    def test_anonymous_user_cannot_submit_registration(self):
        response = self.client.post(
            self.register_url,
            self.valid_registration_data,
        )
        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.register_url}",
        )
        self.assertFalse(
            self.User.objects.filter(username="alicesmith").exists()
        )

    def test_regular_user_denied_access_to_register_page(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.register_url, follow=True)
        self.assertRedirects(response, self.backlog_url)
        self.assertContains(
            response,
            "Access denied: You do not have permission to register new accounts.",
        )

    def test_regular_user_cannot_submit_registration(self):
        self.client.force_login(self.regular_user)
        response = self.client.post(
            self.register_url,
            self.valid_registration_data,
            follow=True,
        )
        self.assertRedirects(response, self.backlog_url)
        self.assertContains(
            response,
            "Access denied: You do not have permission to register new accounts.",
        )
        self.assertFalse(
            self.User.objects.filter(username="alicesmith").exists()
        )

    def test_admin_can_access_register_page(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register_account.html")

    # -------------------------------------------------------------------------
    # AC2: Admin can enter the new user's email address.
    # -------------------------------------------------------------------------

    def test_register_page_contains_email_field(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'type="email"')

    # -------------------------------------------------------------------------
    # AC3: New accounts receive the default temporary password.
    # -------------------------------------------------------------------------

    def test_register_page_does_not_contain_password_fields(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.register_url)
        self.assertNotContains(response, 'name="password"')
        self.assertNotContains(response, 'name="password_confirm"')

    def test_new_account_uses_default_password(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.register_url, self.valid_registration_data)
        user = self.User.objects.get(username="alicesmith")
        self.assertTrue(user.check_password("password123"))

    # -------------------------------------------------------------------------
    # AC4: The password is securely stored and cannot be viewed by other users.
    # -------------------------------------------------------------------------

    def test_password_is_securely_hashed_in_database(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.register_url, self.valid_registration_data)
        user = self.User.objects.get(username="alicesmith")
        self.assertNotEqual(user.password, "password123")
        self.assertTrue(user.check_password("password123"))

    def test_user_accounts_page_does_not_reveal_passwords(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.register_url, self.valid_registration_data)
        user = self.User.objects.get(username="alicesmith")
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, user.password)

    # -------------------------------------------------------------------------
    # AC5: The system validates that the email address is in a valid format.
    # -------------------------------------------------------------------------

    def test_invalid_email_format_fails_validation(self):
        self.client.force_login(self.admin_user)
        invalid_emails = [
            "plainaddress",
            "@missinguser.com",
            "missing-domain@",
            "user@domain..com",
        ]
        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                data = self.valid_registration_data.copy()
                data["email"] = invalid_email
                response = self.client.post(self.register_url, data)
                self.assertEqual(response.status_code, 200)
                form = response.context["form"]
                self.assertIn("email", form.errors)
                self.assertFalse(
                    self.User.objects.filter(username="alicesmith").exists()
                )

    # -------------------------------------------------------------------------
    # AC6: The system prevents registration if email is already associated.
    # -------------------------------------------------------------------------

    def test_duplicate_email_prevents_registration(self):
        self.client.force_login(self.admin_user)
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data["email"] = "admin@example.com"
        response = self.client.post(self.register_url, duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email address already exists.",
        )
        self.assertFalse(
            self.User.objects.filter(username="alicesmith").exists()
        )

    def test_duplicate_email_case_insensitive_prevents_registration(self):
        self.client.force_login(self.admin_user)
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data["email"] = "ADMIN@EXAMPLE.COM"
        response = self.client.post(self.register_url, duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email address already exists.",
        )

    def test_duplicate_username_prevents_registration(self):
        self.client.force_login(self.admin_user)
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data["username"] = "admin_user"
        response = self.client.post(self.register_url, duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "username",
            "This username is already taken.",
        )

    # -------------------------------------------------------------------------
    # AC7: Default password is assigned automatically by the system.
    # -------------------------------------------------------------------------

    def test_submitted_password_fields_do_not_override_default_password(self):
        self.client.force_login(self.admin_user)
        data = self.valid_registration_data.copy()
        data["password"] = "SomethingElse123!"
        data["password_confirm"] = "SomethingElse123!"
        self.client.post(self.register_url, data)
        user = self.User.objects.get(username="alicesmith")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.check_password("SomethingElse123!"))

    # -------------------------------------------------------------------------
    # AC8: The new account is successfully saved in the database.
    # -------------------------------------------------------------------------

    def test_successful_registration_saves_user_in_database(self):
        self.client.force_login(self.admin_user)
        initial_count = self.User.objects.count()
        response = self.client.post(
            self.register_url,
            self.valid_registration_data,
        )
        self.assertRedirects(response, self.user_accounts_url)
        self.assertEqual(self.User.objects.count(), initial_count + 1)
        user = self.User.objects.get(username="alicesmith")
        self.assertEqual(user.first_name, "Alice")
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.email, "alice.smith@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_invalid_role_fails_validation(self):
        self.client.force_login(self.admin_user)
        owner_data = self.valid_registration_data.copy()
        owner_data["username"] = "bob_owner"
        owner_data["email"] = "bob@example.com"
        owner_data["role"] = "owner"
        response = self.client.post(self.register_url, owner_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("role", form.errors)
        self.assertFalse(
            self.User.objects.filter(username="bob_owner").exists()
        )

    def test_successful_registration_sets_superuser_for_admin_role(self):
        self.client.force_login(self.admin_user)
        admin_data = self.valid_registration_data.copy()
        admin_data["username"] = "carol_admin"
        admin_data["email"] = "carol@example.com"
        admin_data["role"] = "admin"
        response = self.client.post(self.register_url, admin_data)
        self.assertRedirects(response, self.user_accounts_url)
        user = self.User.objects.get(username="carol_admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    # -------------------------------------------------------------------------
    # AC9: Newly registered user can use email and default password to log in.
    # -------------------------------------------------------------------------

    def test_newly_registered_user_can_log_in(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.register_url, self.valid_registration_data)
        self.client.logout()
        login_response = self.client.post(
            self.login_url,
            {
                "email": "alice.smith@example.com",
                "password": "password123",
            },
        )
        self.assertRedirects(login_response, reverse("accounts:change_password"))
        new_user = self.User.objects.get(username="alicesmith")
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(new_user.pk),
        )

    # -------------------------------------------------------------------------
    # AC10: The new account is included in registered user accounts list.
    # -------------------------------------------------------------------------

    def test_newly_registered_user_appears_in_user_accounts_list(self):
        self.client.force_login(self.admin_user)
        self.client.post(self.register_url, self.valid_registration_data)
        accounts_response = self.client.get(self.user_accounts_url)
        self.assertEqual(accounts_response.status_code, 200)
        self.assertTemplateUsed(
            accounts_response,
            "accounts/user_accounts.html",
        )
        self.assertContains(accounts_response, "Alice Smith")
        self.assertContains(accounts_response, "@alicesmith")
        self.assertContains(accounts_response, "alice.smith@example.com")
        self.assertContains(accounts_response, "Team member")
        self.assertContains(accounts_response, "Active")