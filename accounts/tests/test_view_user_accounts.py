from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from backlog.models import Sprint, Task, TaskWorkSession


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

    # -------------------------------------------------------------------------
    # Acceptance Criteria: Remove account from admin side
    # An account can ONLY be removed when there are NO tasks assigned to it.
    # -------------------------------------------------------------------------
    def test_admin_can_remove_account_when_no_tasks_assigned(self):
        """When a user has 0 tasks assigned, admin can successfully remove the account."""
        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, f"Account for {self.regular_user.get_full_name()} (@{self.regular_user.username}) has been successfully removed.")
        self.assertFalse(self.User.objects.filter(id=self.regular_user.id).exists())

    def test_admin_cannot_remove_account_when_tasks_assigned(self):
        """When a user has active tasks assigned, removal is blocked with an error message."""
        Task.objects.create(
            title="Assigned Task 1",
            assignee=self.regular_user,
            story_points=3,
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, "Cannot remove")
        self.assertContains(response, "This account has 1 assigned task(s). Please reassign or unassign all tasks before removing the account.")
        # User must still exist
        self.assertTrue(self.User.objects.filter(id=self.regular_user.id).exists())

    def test_admin_cannot_remove_own_account(self):
        """An admin cannot remove their own account."""
        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.admin_user.id})
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, "You cannot remove your own account.")
        self.assertTrue(self.User.objects.filter(id=self.admin_user.id).exists())

    def test_regular_user_cannot_remove_account(self):
        """A non-admin user cannot remove accounts."""
        self.client.force_login(self.regular_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.admin_user.id})
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.backlog_url)
        self.assertContains(response, "Access denied: You do not have permission to remove user accounts.")
        self.assertTrue(self.User.objects.filter(id=self.admin_user.id).exists())

    def test_anonymous_user_cannot_remove_account(self):
        """Unauthenticated user cannot remove accounts."""
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(remove_endpoint)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={remove_endpoint}")
        self.assertTrue(self.User.objects.filter(id=self.regular_user.id).exists())

    def test_admin_remove_user_account_cleans_up_memberships_and_sessions(self):
        """
        When a user with 0 assigned tasks is removed, any sprint team memberships,
        sprint roles, and historical work sessions are cleanly removed without raising ProtectedError.
        """
        sprint = Sprint.objects.create(name="Sprint Clean", status="planning", product_owner=self.regular_user)
        sprint.team_members.add(self.regular_user)

        # Other task with different assignee, but work session logged by regular_user
        other_task = Task.objects.create(title="Other Task", assignee=self.admin_user)
        now = timezone.now()
        TaskWorkSession.objects.create(
            task=other_task,
            user=self.regular_user,
            started_at=now - timedelta(hours=2),
            ended_at=now - timedelta(hours=1),
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertFalse(self.User.objects.filter(id=self.regular_user.id).exists())
        sprint.refresh_from_db()
        self.assertIsNone(sprint.product_owner)
        self.assertNotIn(self.regular_user, sprint.team_members.all())

    def test_user_accounts_ui_shows_task_badge_and_modal_attributes(self):
        """UI shows assigned task count badge and data-tasks-count on the Remove button."""
        Task.objects.create(
            title="Task for member",
            assignee=self.regular_user,
            story_points=5,
        )
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)

        # Badge and data attribute
        self.assertContains(response, 'data-tasks-count="1"')
        self.assertContains(response, "1 task")
        self.assertContains(response, "Remove User Account")

    def test_admin_can_remove_account_with_reassignment_of_product_backlog_task(self):
        """When an account has an active Product Backlog task, admin can reassign to another non-admin and remove."""
        other_user = self.User.objects.create_user(
            username="other_dev",
            email="other@example.com",
            password="OtherPassword123!",
            first_name="Other",
            last_name="Dev",
        )
        task = Task.objects.create(
            title="Product Backlog Feature",
            assignee=self.regular_user,
            story_points=5,
            status="in_progress",
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(
            remove_endpoint,
            data={f"reassign_task_{task.id}": other_user.id},
            follow=True,
        )

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, f"Account for {self.regular_user.get_full_name()} (@{self.regular_user.username}) has been successfully removed and 1 assigned task(s) were reassigned.")
        self.assertFalse(self.User.objects.filter(id=self.regular_user.id).exists())

        task.refresh_from_db()
        self.assertEqual(task.assignee, other_user)
        # Verify TaskHistory created
        self.assertTrue(
            task.history.filter(
                changed_by=self.admin_user,
                description__contains="reassigned task from Regular Member to Other Dev",
            ).exists()
        )

    def test_admin_can_remove_account_with_reassignment_of_sprint_task(self):
        """When an account has a Sprint task, admin can reassign to another member of that sprint and remove."""
        sprint_member = self.User.objects.create_user(
            username="sprint_dev",
            email="sprint_dev@example.com",
            password="DevPassword123!",
            first_name="Sprint",
            last_name="Dev",
        )
        sprint = Sprint.objects.create(name="Sprint 10", status="active")
        sprint.team_members.add(self.regular_user, sprint_member)

        task = Task.objects.create(
            title="Sprint Work Item",
            assignee=self.regular_user,
            sprint=sprint,
            story_points=3,
            status="not_started",
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(
            remove_endpoint,
            data={f"reassign_task_{task.id}": sprint_member.id},
            follow=True,
        )

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, "successfully removed and 1 assigned task(s) were reassigned.")
        self.assertFalse(self.User.objects.filter(id=self.regular_user.id).exists())

        task.refresh_from_db()
        self.assertEqual(task.assignee, sprint_member)

    def test_admin_cannot_reassign_sprint_task_to_non_sprint_member(self):
        """Sprint tasks cannot be reassigned to users who are not in the sprint team."""
        outsider = self.User.objects.create_user(
            username="outsider_user",
            email="outsider@example.com",
            password="OutsiderPassword123!",
            first_name="Outsider",
            last_name="User",
        )
        sprint = Sprint.objects.create(name="Sprint 11", status="active")
        sprint.team_members.add(self.regular_user)  # outsider is not in sprint

        task = Task.objects.create(
            title="Sprint Secret Item",
            assignee=self.regular_user,
            sprint=sprint,
            story_points=2,
            status="in_progress",
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(
            remove_endpoint,
            data={f"reassign_task_{task.id}": outsider.id},
            follow=True,
        )

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, "can only be reassigned to members of that sprint.")
        self.assertTrue(self.User.objects.filter(id=self.regular_user.id).exists())
        task.refresh_from_db()
        self.assertEqual(task.assignee, self.regular_user)

    def test_admin_cannot_reassign_task_to_administrator(self):
        """Tasks cannot be reassigned to administrators."""
        task = Task.objects.create(
            title="Backlog Item",
            assignee=self.regular_user,
            story_points=2,
            status="not_started",
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        response = self.client.post(
            remove_endpoint,
            data={f"reassign_task_{task.id}": self.admin_user.id},
            follow=True,
        )

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, "Tasks cannot be reassigned to administrators")
        self.assertTrue(self.User.objects.filter(id=self.regular_user.id).exists())
        task.refresh_from_db()
        self.assertEqual(task.assignee, self.regular_user)

    def test_admin_can_remove_account_with_completed_tasks_without_reassignment(self):
        """
        Tasks that are completed do not need to be reassigned and remain locked.
        An account with only completed tasks can be removed without reassignments.
        """
        completed_task = Task.objects.create(
            title="Finished Task",
            assignee=self.regular_user,
            story_points=3,
            status="completed",
        )

        self.client.force_login(self.admin_user)
        remove_endpoint = reverse("accounts:admin_remove_user_account", kwargs={"user_id": self.regular_user.id})
        # Standard post without any reassignment fields
        response = self.client.post(remove_endpoint, follow=True)

        self.assertRedirects(response, self.user_accounts_url)
        self.assertContains(response, f"Account for {self.regular_user.get_full_name()} (@{self.regular_user.username}) has been successfully removed.")
        self.assertFalse(self.User.objects.filter(id=self.regular_user.id).exists())

        completed_task.refresh_from_db()
        self.assertEqual(completed_task.status, "completed")
        self.assertIsNone(completed_task.assignee)

    def test_user_accounts_ui_renders_reassignment_data_json(self):
        """The user accounts page injects active tasks JSON with eligible members."""
        other_user = self.User.objects.create_user(
            username="eligible_dev",
            email="eligible@example.com",
            password="DevPassword123!",
            first_name="Eligible",
            last_name="Dev",
        )
        task = Task.objects.create(
            title="UI Feature Task",
            assignee=self.regular_user,
            story_points=5,
            status="not_started",
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)

        # JSON script tag should contain task and eligible dev, but not admin
        self.assertContains(response, "user-active-tasks-data")
        self.assertContains(response, "UI Feature Task")
        self.assertContains(response, "eligible_dev")
        self.assertNotContains(response, f'"username": "{self.admin_user.username}"')

    def test_user_accounts_ui_renders_reassignment_prompt_and_button_styles(self):
        """Verify the modal includes the reassignment prompt banner and button dark/bright styling classes."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Reassign Tasks Before Account Removal")
        self.assertContains(response, "btn-reassign-dark")
        self.assertContains(response, "btn-reassign-bright")
        self.assertContains(response, "removeTasksReassignSection")

    def test_user_accounts_includes_both_active_and_completed_tasks_from_database(self):
        """
        When a user has both active and completed tasks in the database,
        all tasks are retrieved from the database and passed into the modal data payload.
        """
        active_task = Task.objects.create(
            title="Database Active Task",
            assignee=self.regular_user,
            story_points=3,
            status="not_started",
        )
        completed_task = Task.objects.create(
            title="Database Completed Task",
            assignee=self.regular_user,
            story_points=5,
            status="completed",
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)

        # Both task titles must be in the JSON data payload retrieved from DB
        self.assertContains(response, "Database Active Task")
        self.assertContains(response, "Database Completed Task")

        # Table badge reflects total and breakdown from database
        self.assertContains(response, "2 tasks")
        self.assertContains(response, "(1 active, 1 completed)")

        # Verify context data structure
        user_tasks = response.context["user_active_tasks"].get(str(self.regular_user.id), [])
        self.assertEqual(len(user_tasks), 2)

        task_titles = {t["title"]: t for t in user_tasks}
        self.assertTrue(task_titles["Database Active Task"]["requires_reassign"])
        self.assertFalse(task_titles["Database Active Task"]["is_completed"])

        self.assertFalse(task_titles["Database Completed Task"]["requires_reassign"])
        self.assertTrue(task_titles["Database Completed Task"]["is_completed"])

    def test_modal_has_dynamic_database_count_elements(self):
        """Verify modal template includes dynamic database count containers and locked note."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.user_accounts_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'id="reassignTotalTasksCount"')
        self.assertContains(response, 'id="reassignActiveTasksCount"')
        self.assertContains(response, 'id="reassignCompletedTasksCount"')
        self.assertContains(response, 'id="reassignCompletedSubnote"')

