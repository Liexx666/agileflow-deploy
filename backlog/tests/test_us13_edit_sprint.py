from datetime import date, timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Sprint, SprintHistory


class EditSprintTests(TestCase):
    """
    Automated tests for User Story US-13: Edit Sprint.
    Tests all acceptance criteria for sprint editing backend logic and permissions.
    """

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username="admin_editor",
            email="admin_editor@example.com",
            password="Password123!",
        )

        # Authorized Sprint Members
        self.po_user = User.objects.create_user(
            username="po_user",
            first_name="Alice",
            last_name="PO",
            email="alice.po@example.com",
        )
        self.sm_user = User.objects.create_user(
            username="sm_user",
            first_name="Bob",
            last_name="SM",
            email="bob.sm@example.com",
        )
        self.member1 = User.objects.create_user(
            username="dev_member1",
            first_name="Charlie",
            last_name="Dev",
            email="charlie.dev@example.com",
        )
        self.new_po_user = User.objects.create_user(
            username="new_po_user",
            first_name="David",
            last_name="NewPO",
            email="david.po@example.com",
        )
        self.new_sm_user = User.objects.create_user(
            username="new_sm_user",
            first_name="Eve",
            last_name="NewSM",
            email="eve.sm@example.com",
        )
        self.new_member = User.objects.create_user(
            username="new_member",
            first_name="Frank",
            last_name="NewDev",
            email="frank.dev@example.com",
        )

        # Unauthorized regular user (not part of this sprint)
        self.unauthorized_user = User.objects.create_user(
            username="unauthorized_user",
            email="unauth@example.com",
            password="Password123!",
            is_staff=False,
            is_superuser=False,
        )

        self.today = date.today()
        self.end_date = self.today + timedelta(days=14)

        # Create base sprint for testing
        self.sprint = Sprint.objects.create(
            name="Sprint 1 - Original",
            start_date=self.today,
            end_date=self.end_date,
            product_owner=self.po_user,
            scrum_master=self.sm_user,
            goal="Original goal statement.",
            status="not_started",
        )
        self.sprint.team_members.add(self.member1)

        self.url = reverse("backlog:edit_sprint", kwargs={"sprint_id": self.sprint.id})

        self.valid_edit_data = {
            "name": "Sprint 1 - Renamed",
            "start_date": (self.today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "end_date": (self.end_date + timedelta(days=7)).strftime("%Y-%m-%d"),
            "team_members": [self.member1.id, self.new_member.id],
            "goal": "Updated sprint goal.",
            "status": "active",
        }

    # AC: Anonymous user redirected to login
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    # AC: Unauthorized user cannot access sprint edit page
    def test_unauthorized_user_denied_access(self):
        self.client.force_login(self.unauthorized_user)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("backlog:product_backlog"))
        self.assertContains(
            response,
            "Access denied: You do not have permission to edit this sprint.",
        )

    # AC: Authorized users (Admin, PO, SM, Team Member) can access edit sprint page
    def test_authorized_users_can_access_edit_page(self):
        for user in [self.admin, self.po_user, self.sm_user, self.member1]:
            self.client.force_login(user)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "backlog/edit_sprint.html")
            self.assertIn("form", response.context)
            self.assertEqual(response.context["sprint"], self.sprint)

    # AC: Sprint name can be changed
    def test_sprint_name_can_be_changed(self):
        self.client.force_login(self.admin)
        data = self.valid_edit_data.copy()
        data["name"] = "Sprint Alpha - New Name"

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("backlog:product_backlog"))

        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.name, "Sprint Alpha - New Name")

    # AC: Start and end dates can be changed
    def test_start_and_end_dates_can_be_changed(self):
        self.client.force_login(self.admin)
        new_start = self.today + timedelta(days=3)
        new_end = self.today + timedelta(days=20)
        data = self.valid_edit_data.copy()
        data["start_date"] = new_start.strftime("%Y-%m-%d")
        data["end_date"] = new_end.strftime("%Y-%m-%d")

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("backlog:product_backlog"))

        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.start_date, new_start)
        self.assertEqual(self.sprint.end_date, new_end)

    # AC: Team members can be changed
    def test_team_members_can_be_changed(self):
        self.client.force_login(self.admin)
        data = self.valid_edit_data.copy()
        data["team_members"] = [self.new_member.id]

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("backlog:product_backlog"))

        self.sprint.refresh_from_db()
        team_members = list(self.sprint.team_members.all())
        self.assertEqual(team_members, [self.new_member])
        self.assertNotIn(self.member1, team_members)



    # AC: Changes are recorded in sprint history
    def test_changes_are_recorded_in_sprint_history(self):
        self.client.force_login(self.admin)
        initial_history_count = SprintHistory.objects.filter(sprint=self.sprint).count()

        response = self.client.post(self.url, self.valid_edit_data)
        self.assertRedirects(response, reverse("backlog:product_backlog"))

        history_entries = SprintHistory.objects.filter(sprint=self.sprint).order_by("-timestamp")
        self.assertGreater(history_entries.count(), initial_history_count)

        # Check descriptions recorded for changes
        descriptions = [h.description for h in history_entries]
        self.assertTrue(any("edited sprint name to \"Sprint 1 - Renamed\"" in desc for desc in descriptions))
        self.assertTrue(any("edited goal" in desc for desc in descriptions))
        for h in history_entries:
            self.assertEqual(h.changed_by, self.admin)

    def test_remove_member_with_task_reassigned_to_sprint_member(self):
        """When a member is removed from a sprint, their sprint task can be reassigned to a remaining sprint member."""
        from backlog.models import Task, TaskHistory
        self.client.force_login(self.admin)
        task = Task.objects.create(
            title="Sprint Subtask 1",
            sprint=self.sprint,
            assignee=self.member1,
        )

        data = self.valid_edit_data.copy()
        data["team_members"] = [self.new_member.id]
        data[f"reassign_task_{task.id}"] = self.new_member.id

        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("backlog:product_backlog"))

        task.refresh_from_db()
        self.assertEqual(task.assignee, self.new_member)
        self.assertTrue(TaskHistory.objects.filter(task=task).exists())
