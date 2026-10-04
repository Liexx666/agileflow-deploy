from datetime import date, timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Sprint, SprintHistory


class CreateSprintTests(TestCase):
    """
    Automated tests for User Story US-12: Create a Sprint.
    Tests all acceptance criteria for sprint creation backend logic.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("backlog:create_sprint")

        # Admin user
        self.admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="Password123!",
        )

        # Regular user
        self.regular_user = User.objects.create_user(
            username="regular_member",
            email="member@example.com",
            password="Password123!",
            is_staff=False,
            is_superuser=False,
        )

        # Product Owner and Scrum Master
        self.po_user = User.objects.create_user(
            username="po_user",
            first_name="Product",
            last_name="Owner",
            email="po@example.com",
        )
        self.sm_user = User.objects.create_user(
            username="sm_user",
            first_name="Scrum",
            last_name="Master",
            email="sm@example.com",
        )
        self.dev1 = User.objects.create_user(
            username="dev1",
            first_name="Developer",
            last_name="One",
            email="dev1@example.com",
        )

        self.today = date.today()
        self.two_weeks_later = self.today + timedelta(days=14)

        self.valid_data = {
            "name": "Sprint 1 - Foundation",
            "start_date": self.today.strftime("%Y-%m-%d"),
            "end_date": self.two_weeks_later.strftime("%Y-%m-%d"),
            "team_members": [self.dev1.id],
            "goal": "Build foundation features and sprint setup.",
        }

    # AC: Only Admin can access sprint creation
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_regular_user_denied_access(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("backlog:product_backlog"))
        self.assertContains(
            response,
            "Access denied: You do not have permission to create a sprint.",
        )

    def test_admin_can_access_create_sprint_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    # AC: Admin can create a sprint, enter name, start date, end date, PO, SM, team members
    # AC: Newly created sprint has status Not Started
    def test_valid_sprint_creation(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(response, reverse("backlog:product_backlog"))
        self.assertEqual(Sprint.objects.count(), 1)

        sprint = Sprint.objects.get(name="Sprint 1 - Foundation")
        self.assertEqual(sprint.start_date, self.today)
        self.assertEqual(sprint.end_date, self.two_weeks_later)
        self.assertIsNone(sprint.product_owner)
        self.assertIsNone(sprint.scrum_master)
        self.assertIn(self.dev1, sprint.team_members.all())
        self.assertEqual(sprint.goal, "Build foundation features and sprint setup.")
        # AC: Newly created sprint has status Not Started
        self.assertEqual(sprint.status, "not_started")



    # AC: End date cannot be earlier than start date
    def test_end_date_before_start_date_fails_validation(self):
        self.client.force_login(self.admin)
        invalid_data = self.valid_data.copy()
        invalid_data["end_date"] = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")

        response = self.client.post(self.url, invalid_data)
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertIn("end_date", form.errors)
        self.assertIn(
            "End date cannot be earlier than start date.",
            form.errors["end_date"],
        )
        self.assertEqual(Sprint.objects.count(), 0)

    # AC: Required fields enforcement
    def test_required_fields_enforced(self):
        self.client.force_login(self.admin)
        invalid_data = {
            "name": "",
            "start_date": "",
            "end_date": "",
        }

        response = self.client.post(self.url, invalid_data)
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertIn("name", form.errors)
        self.assertIn("start_date", form.errors)
        self.assertIn("end_date", form.errors)
        self.assertEqual(Sprint.objects.count(), 0)

    # AC: Sprint creation is recorded in sprint history
    def test_sprint_creation_records_sprint_history(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, self.valid_data)

        sprint = Sprint.objects.get(name="Sprint 1 - Foundation")
        history_entries = SprintHistory.objects.filter(sprint=sprint)
        self.assertEqual(history_entries.count(), 1)

        history = history_entries.first()
        self.assertEqual(history.changed_by, self.admin)
        self.assertIn("created sprint 'Sprint 1 - Foundation'", history.description)
        self.assertIn("Not Started", history.description)
        self.assertIsNotNone(history.timestamp)

    # UI: Admin sees 'Create new sprint' button on backlog page, regular user does not
    def test_create_sprint_button_visibility(self):
        # Regular user should not see 'Create new sprint'
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertNotContains(response, "Create new sprint")

        # Admin user should see 'Create new sprint'
        self.client.force_login(self.admin)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertContains(response, "Create new sprint")
        self.assertContains(response, reverse("backlog:create_sprint"))
