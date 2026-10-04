from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ViewUserAccountsTests(TestCase):
    """
    Automated unit tests for US-27: View user accounts.
    Tests all acceptance criteria for viewing the user-management area.
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
        self.regular_user = self.User.objects.create_user(
            username="regular_member",
            email="member@example.com",
            password="MemberPassword123!",
            first_name="Regular",
            last_name="Member",
            is_staff=False,
            is_superuser=False,
        )
        self.user_accounts_url = reverse("accounts:user_accounts")
        self.backlog_url = reverse("backlog:product_backlog")

    # -------------------------------------------------------------------------
    # AC1: Admin can access the user-management area.
    # -------------------------------------------------------------------------
    def test_admin_can_access_user_management_area(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/user_accounts.html")

    def test_regular_user_cannot_access_user_management_area(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.user_accounts_url)
        self.assertRedirects(response, self.backlog_url)
        
    def test_anonymous_user_cannot_access_user_management_area(self):
        response = self.client.get(self.user_accounts_url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.user_accounts_url}")

    # -------------------------------------------------------------------------
    # AC2 & AC3: Registered users, names, and emails are displayed.
    # -------------------------------------------------------------------------
    def test_registered_users_names_and_emails_are_displayed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        
        # Check Admin User details
        self.assertContains(response, "Admin User")
        self.assertContains(response, "@admin_user")
        self.assertContains(response, "admin@example.com")
        
        # Check Regular Member details
        self.assertContains(response, "Regular Member")
        self.assertContains(response, "@regular_member")
        self.assertContains(response, "member@example.com")

    # -------------------------------------------------------------------------
    # AC4: User roles are displayed.
    # -------------------------------------------------------------------------
    def test_user_roles_are_displayed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        
        self.assertContains(response, "Administrator")
        self.assertContains(response, "Team member")

    # -------------------------------------------------------------------------
    # AC5: Passwords are never displayed.
    # -------------------------------------------------------------------------
    def test_passwords_are_never_displayed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        
        # Raw passwords should not be in the HTML
        self.assertNotContains(response, "AdminPassword123!")
        self.assertNotContains(response, "MemberPassword123!")
        
        # Hashed passwords should also not be rendered in the HTML
        self.assertNotContains(response, self.admin_user.password)
        self.assertNotContains(response, self.regular_user.password)

    # -------------------------------------------------------------------------
    # AC6: Admin can reset another user's password to default 'password123'.
    # -------------------------------------------------------------------------
    def test_admin_can_reset_user_password_to_default(self):
        self.client.force_login(self.admin_user)
        reset_endpoint = reverse("accounts:admin_reset_user_password", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(reset_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(
            response,
            "has been successfully reset to default (password123)",
        )

        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password("password123"))

    def test_regular_user_cannot_reset_other_user_password(self):
        self.client.force_login(self.regular_user)
        reset_endpoint = reverse("accounts:admin_reset_user_password", kwargs={"user_id": self.admin_user.id})
        response = self.client.post(reset_endpoint, follow=True)

        self.assertRedirects(response, self.backlog_url)
        self.assertContains(
            response,
            "Access denied: You do not have permission to reset user passwords.",
        )

    def test_anonymous_user_cannot_reset_password(self):
        reset_endpoint = reverse("accounts:admin_reset_user_password", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(reset_endpoint)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reset_endpoint}")

    def test_admin_reset_nonexistent_user_returns_404(self):
        self.client.force_login(self.admin_user)
        reset_endpoint = reverse("accounts:admin_reset_user_password", kwargs={"user_id": 99999})
        response = self.client.post(reset_endpoint)
        self.assertEqual(response.status_code, 404)
