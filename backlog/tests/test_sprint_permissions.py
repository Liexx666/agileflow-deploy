"""
Tests for Sprint Permission / Authorization System.

Covers:
  - check_sprint_permission helper (admin bypass, member access, non-member denial)
  - edit_task: blocked for non-sprint-members, allowed for members/admin
  - delete_task: blocked if task is in a sprint; allowed only for Product Backlog tasks
  - update_task_status: blocked for non-sprint-members
  - sprint_task_status (kanban drag): blocked for non-sprint-members
  - can_edit_task context variable injected into task_detail
"""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, Task
from backlog.sprint_services import check_sprint_permission


class CheckSprintPermissionHelperTests(TestCase):
    """Unit tests for the check_sprint_permission service helper."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_perm", password="Pass123!", is_staff=True, is_superuser=True
        )
        self.member = User.objects.create_user(username="member_perm", password="Pass123!")
        self.outsider = User.objects.create_user(username="outsider_perm", password="Pass123!")

        self.sprint = Sprint.objects.create(name="Perm Sprint", status="active")
        self.sprint.team_members.add(self.member)

    def test_admin_always_passes(self):
        """Admin/superuser should never raise a ValidationError."""
        try:
            check_sprint_permission(self.sprint, self.admin)
        except ValidationError:
            self.fail("check_sprint_permission raised ValidationError for admin")

    def test_sprint_member_passes(self):
        """An assigned team member should be granted access."""
        try:
            check_sprint_permission(self.sprint, self.member)
        except ValidationError:
            self.fail("check_sprint_permission raised ValidationError for sprint member")

    def test_non_member_raises_validation_error(self):
        """A user not in the sprint should be denied with a ValidationError."""
        with self.assertRaises(ValidationError):
            check_sprint_permission(self.sprint, self.outsider)

    def test_none_sprint_always_passes(self):
        """A None sprint (product backlog task) should never raise."""
        try:
            check_sprint_permission(None, self.outsider)
        except ValidationError:
            self.fail("check_sprint_permission raised ValidationError for None sprint")


class EditTaskPermissionTests(TestCase):
    """Tests that edit_task enforces sprint membership."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_edit", password="Pass123!", is_staff=True, is_superuser=True
        )
        self.member = User.objects.create_user(username="member_edit", password="Pass123!")
        self.outsider = User.objects.create_user(username="outsider_edit", password="Pass123!")
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user__in=[self.admin, self.member, self.outsider]).update(must_change_password=False)

        self.sprint = Sprint.objects.create(name="Edit Sprint", status="active")
        self.sprint.team_members.add(self.member)

        self.task = Task.objects.create(
            title="Sprint Task",
            sprint=self.sprint,
            status="not_started",
            story_points=3,
        )
        self.backlog_task = Task.objects.create(
            title="Backlog Task",
            sprint=None,
            status="not_started",
            story_points=2,
        )

    def test_non_member_cannot_edit_sprint_task(self):
        """Non-sprint-member should be redirected away from edit page."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("backlog:edit_task", args=[self.task.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("backlog:task_detail", args=[self.task.pk]))

    def test_sprint_member_can_access_edit_task(self):
        """Sprint member should be able to access the edit task page."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("backlog:edit_task", args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_edit_task(self):
        """Admin should be able to access the edit task page for any sprint."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("backlog:edit_task", args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)

    def test_any_user_can_edit_backlog_task(self):
        """Any logged-in user can edit a task that is not in a sprint."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("backlog:edit_task", args=[self.backlog_task.pk]))
        self.assertEqual(response.status_code, 200)


class DeleteTaskPermissionTests(TestCase):
    """Tests that delete_task enforces the 'product backlog only' rule."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_del", password="Pass123!", is_staff=True, is_superuser=True
        )
        self.member = User.objects.create_user(username="member_del", password="Pass123!")
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user__in=[self.admin, self.member]).update(must_change_password=False)

        self.sprint = Sprint.objects.create(name="Del Sprint", status="active")
        self.sprint.team_members.add(self.member)

        self.sprint_task = Task.objects.create(
            title="Sprint Task to Delete",
            sprint=self.sprint,
            status="not_started",
            story_points=2,
        )
        self.backlog_task = Task.objects.create(
            title="Backlog Task to Delete",
            sprint=None,
            status="not_started",
            story_points=2,
        )

    def test_cannot_delete_task_in_sprint_as_member(self):
        """Even sprint members should be blocked from deleting tasks in a sprint."""
        self.client.force_login(self.member)
        self.client.get(reverse("backlog:delete_task", args=[self.sprint_task.pk]))
        self.sprint_task.refresh_from_db()
        self.assertFalse(self.sprint_task.is_deleted)

    def test_cannot_delete_task_in_sprint_as_admin(self):
        """Even admins should be blocked from deleting a task that is still in a sprint."""
        self.client.force_login(self.admin)
        self.client.get(reverse("backlog:delete_task", args=[self.sprint_task.pk]))
        self.sprint_task.refresh_from_db()
        self.assertFalse(self.sprint_task.is_deleted)

    def test_backlog_task_can_be_deleted_by_any_user(self):
        """Any logged-in user can delete a task sitting in the Product Backlog."""
        from accounts.models import AccountSecurity
        outsider = User.objects.create_user(username="outsider_del2", password="Pass123!")
        AccountSecurity.objects.filter(user=outsider).update(must_change_password=False)
        self.client.force_login(outsider)
        response = self.client.post(reverse("backlog:delete_task", args=[self.backlog_task.pk]))
        self.assertEqual(response.status_code, 302)
        self.backlog_task.refresh_from_db()
        self.assertTrue(self.backlog_task.is_deleted)

    def test_delete_task_confirmation_page_shown_for_backlog_task(self):
        """GET on delete_task for a backlog task should show the confirmation page."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("backlog:delete_task", args=[self.backlog_task.pk]))
        self.assertEqual(response.status_code, 200)

    def test_completed_backlog_task_cannot_be_deleted(self):
        """A completed task in the product backlog cannot be deleted."""
        completed_task = Task.objects.create(
            title="Completed Backlog Task",
            sprint=None,
            status="completed",
            story_points=1,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("backlog:delete_task", args=[completed_task.pk]))
        self.assertEqual(response.status_code, 302)
        completed_task.refresh_from_db()
        self.assertFalse(completed_task.is_deleted)

    def test_delete_sprint_task_redirects_with_error(self):
        """Attempting to delete a sprint task redirects to task detail with an error message."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("backlog:delete_task", args=[self.sprint_task.pk]))
        self.assertRedirects(response, reverse("backlog:task_detail", args=[self.sprint_task.pk]))


class TaskDetailPermissionContextTests(TestCase):
    """Tests that the can_edit_task flag is set correctly in the task detail context."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_ctx", password="Pass123!", is_staff=True, is_superuser=True
        )
        self.member = User.objects.create_user(username="member_ctx", password="Pass123!")
        self.outsider = User.objects.create_user(username="outsider_ctx", password="Pass123!")
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user__in=[self.admin, self.member, self.outsider]).update(must_change_password=False)

        self.sprint = Sprint.objects.create(name="Context Sprint", status="active")
        self.sprint.team_members.add(self.member)

        self.sprint_task = Task.objects.create(
            title="Context Sprint Task",
            sprint=self.sprint,
            status="not_started",
            story_points=1,
        )
        self.backlog_task = Task.objects.create(
            title="Context Backlog Task",
            sprint=None,
            status="not_started",
            story_points=1,
        )

    def test_outsider_gets_can_edit_task_false_for_sprint_task(self):
        """Non-member viewing a sprint task should have can_edit_task=False."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("backlog:task_detail", args=[self.sprint_task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_edit_task"])

    def test_member_gets_can_edit_task_true_for_sprint_task(self):
        """Sprint member viewing a sprint task should have can_edit_task=True."""
        self.client.force_login(self.member)
        response = self.client.get(reverse("backlog:task_detail", args=[self.sprint_task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_edit_task"])

    def test_admin_gets_can_edit_task_true_for_sprint_task(self):
        """Admin viewing any sprint task should have can_edit_task=True."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("backlog:task_detail", args=[self.sprint_task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_edit_task"])

    def test_any_user_gets_can_edit_task_true_for_backlog_task(self):
        """Any user viewing a backlog task should have can_edit_task=True."""
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("backlog:task_detail", args=[self.backlog_task.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_edit_task"])


class SprintTaskStatusPermissionTests(TestCase):
    """Tests that the kanban drag-and-drop status endpoint enforces sprint membership."""

    def setUp(self):
        self.member = User.objects.create_user(username="member_sts", password="Pass123!")
        self.outsider = User.objects.create_user(username="outsider_sts", password="Pass123!")
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user__in=[self.member, self.outsider]).update(must_change_password=False)

        self.sprint = Sprint.objects.create(name="Status Sprint", status="active")
        self.sprint.team_members.add(self.member)

        self.task = Task.objects.create(
            title="Status Task",
            sprint=self.sprint,
            status="not_started",
            story_points=2,
        )

    def test_non_member_cannot_change_kanban_status(self):
        """Non-sprint-member should be blocked from changing task status via the endpoint."""
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task.pk]),
            {"status": "in_progress"},
        )
        self.assertNotEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "not_started")

    def test_sprint_member_can_change_kanban_status(self):
        """Sprint member should be able to change task status via the endpoint."""
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_progress")

    def test_status_endpoint_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "not_started")
