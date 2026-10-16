"""
Tests for strict lockdown of completed and cancelled sprints, and completed tasks.

User Requirement:
If a task/sprint is on completed or cancelled (for sprint), you shouldn't be able to do
anything with it anymore (ie you shouldn't be able to edit sprint, delete the tasks
within the sprint, change the sprint status, change the task status).
"""
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import AccountSecurity
from backlog.forms import SprintEditForm, TaskEditForm
from backlog.models import Sprint, Task
from backlog.sprint_services import (
    change_sprint_status,
    change_sprint_task_status,
    move_task,
)


class CompletedAndCancelledLockdownTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="lockdown_admin",
            email="admin@example.com",
            password="Password123!",
        )
        self.dev = User.objects.create_user(
            username="lockdown_dev",
            email="dev@example.com",
            password="Password123!",
        )
        AccountSecurity.objects.filter(user__in=[self.admin, self.dev]).update(must_change_password=False)
        self.client.force_login(self.admin)

        self.today = date.today()

        # 1. Completed Sprint with a completed task
        self.completed_sprint = Sprint.objects.create(
            name="Completed Sprint 2026",
            status="completed",
            start_date=self.today - timedelta(days=20),
            end_date=self.today - timedelta(days=6),
            product_owner=self.admin,
            scrum_master=self.admin,
        )
        self.completed_sprint.team_members.add(self.admin, self.dev)

        self.task_in_completed_sprint = Task.objects.create(
            title="Task Inside Completed Sprint",
            status="completed",
            sprint=self.completed_sprint,
            story_points=3,
        )

        # 2. Cancelled / Stopped Sprint with a completed task
        self.cancelled_sprint = Sprint.objects.create(
            name="Cancelled Sprint 2026",
            status="stopped",
            start_date=self.today - timedelta(days=10),
            end_date=self.today - timedelta(days=2),
            product_owner=self.admin,
            scrum_master=self.admin,
        )
        self.cancelled_sprint.team_members.add(self.admin, self.dev)

        self.task_in_cancelled_sprint = Task.objects.create(
            title="Task Inside Cancelled Sprint",
            status="completed",
            sprint=self.cancelled_sprint,
            story_points=2,
        )

        # 3. Active Sprint with an active task and a completed task
        self.active_sprint = Sprint.objects.create(
            name="Active Sprint 2026",
            status="active",
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=13),
            product_owner=self.admin,
            scrum_master=self.admin,
        )
        self.active_sprint.team_members.add(self.admin, self.dev)

        self.completed_task_in_active_sprint = Task.objects.create(
            title="Completed Task in Active Sprint",
            status="completed",
            sprint=self.active_sprint,
            story_points=5,
        )

        self.active_task = Task.objects.create(
            title="In Progress Task in Active Sprint",
            status="in_progress",
            sprint=self.active_sprint,
            story_points=4,
        )

    # -------------------------------------------------------------
    # 1. CANNOT EDIT SPRINT
    # -------------------------------------------------------------
    def test_cannot_edit_completed_sprint_via_view(self):
        """Visiting or submitting edit_sprint for a completed sprint redirects with error."""
        url = reverse("backlog:edit_sprint", args=[self.completed_sprint.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

        post_resp = self.client.post(url, {"name": "New Name"})
        self.assertEqual(post_resp.status_code, 302)
        self.completed_sprint.refresh_from_db()
        self.assertEqual(self.completed_sprint.name, "Completed Sprint 2026")

    def test_cannot_edit_cancelled_sprint_via_view(self):
        """Visiting or submitting edit_sprint for a cancelled sprint redirects with error."""
        url = reverse("backlog:edit_sprint", args=[self.cancelled_sprint.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

        post_resp = self.client.post(url, {"name": "New Name"})
        self.assertEqual(post_resp.status_code, 302)
        self.cancelled_sprint.refresh_from_db()
        self.assertEqual(self.cancelled_sprint.name, "Cancelled Sprint 2026")

    def test_sprint_edit_form_rejects_completed_and_cancelled(self):
        """SprintEditForm clean rejects modifications to completed or cancelled sprints."""
        form_comp = SprintEditForm(
            instance=self.completed_sprint,
            data={
                "name": "Try Edit",
                "start_date": self.completed_sprint.start_date.isoformat(),
                "end_date": self.completed_sprint.end_date.isoformat(),
                "status": "completed",
            },
        )
        self.assertFalse(form_comp.is_valid())
        self.assertTrue(any("completed sprint cannot be changed" in str(e) for e in form_comp.non_field_errors()))

        form_canc = SprintEditForm(
            instance=self.cancelled_sprint,
            data={
                "name": "Try Edit",
                "start_date": self.cancelled_sprint.start_date.isoformat(),
                "end_date": self.cancelled_sprint.end_date.isoformat(),
                "status": "stopped",
            },
        )
        self.assertFalse(form_canc.is_valid())
        self.assertTrue(any("cancelled sprint cannot be changed" in str(e) for e in form_canc.non_field_errors()))

    # -------------------------------------------------------------
    # 2. CANNOT CHANGE SPRINT STATUS
    # -------------------------------------------------------------
    def test_cannot_change_completed_sprint_status(self):
        """Completed sprint status cannot be changed via service or API."""
        with self.assertRaises(ValidationError) as ctx:
            change_sprint_status(sprint_id=self.completed_sprint.pk, status="active")
        self.assertIn("A completed Sprint cannot be changed anymore", str(ctx.exception))

        resp = self.client.post(
            reverse("backlog:sprint_status", args=[self.completed_sprint.pk]),
            {"status": "active"},
        )
        self.assertEqual(resp.status_code, 409)

    def test_cannot_change_cancelled_sprint_status(self):
        """Cancelled sprint status cannot be changed via service or API."""
        with self.assertRaises(ValidationError) as ctx:
            change_sprint_status(sprint_id=self.cancelled_sprint.pk, status="active")
        self.assertIn("A cancelled Sprint cannot be changed anymore", str(ctx.exception))

        resp = self.client.post(
            reverse("backlog:sprint_status", args=[self.cancelled_sprint.pk]),
            {"status": "active"},
        )
        self.assertEqual(resp.status_code, 409)

    # -------------------------------------------------------------
    # 3. CANNOT DELETE TASKS WITHIN SPRINT OR COMPLETED TASKS
    # -------------------------------------------------------------
    def test_cannot_delete_task_within_completed_sprint(self):
        """Deleting a task in a completed sprint is rejected."""
        url = reverse("backlog:delete_task", args=[self.task_in_completed_sprint.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        post_resp = self.client.post(url)
        self.assertEqual(post_resp.status_code, 302)
        self.task_in_completed_sprint.refresh_from_db()
        self.assertFalse(self.task_in_completed_sprint.is_deleted)

    def test_cannot_delete_task_within_cancelled_sprint(self):
        """Deleting a task in a cancelled sprint is rejected."""
        url = reverse("backlog:delete_task", args=[self.task_in_cancelled_sprint.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        post_resp = self.client.post(url)
        self.assertEqual(post_resp.status_code, 302)
        self.task_in_cancelled_sprint.refresh_from_db()
        self.assertFalse(self.task_in_cancelled_sprint.is_deleted)

    def test_cannot_delete_completed_task(self):
        """Deleting any completed task is rejected."""
        url = reverse("backlog:delete_task", args=[self.completed_task_in_active_sprint.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.completed_task_in_active_sprint.refresh_from_db()
        self.assertFalse(self.completed_task_in_active_sprint.is_deleted)

    # -------------------------------------------------------------
    # 4. CANNOT CHANGE TASK STATUS
    # -------------------------------------------------------------
    def test_cannot_change_task_status_in_completed_sprint(self):
        """Tasks in completed sprints cannot change their status."""
        resp = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task_in_completed_sprint.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(resp.status_code, 409)

        resp2 = self.client.post(
            reverse("backlog:update_task_status", args=[self.task_in_completed_sprint.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(resp2.status_code, 302)
        self.task_in_completed_sprint.refresh_from_db()
        self.assertEqual(self.task_in_completed_sprint.status, "completed")

    def test_cannot_change_task_status_in_cancelled_sprint(self):
        """Tasks in cancelled sprints cannot change their status."""
        resp = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task_in_cancelled_sprint.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(resp.status_code, 409)

        resp2 = self.client.post(
            reverse("backlog:update_task_status", args=[self.task_in_cancelled_sprint.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(resp2.status_code, 302)
        self.task_in_cancelled_sprint.refresh_from_db()
        self.assertEqual(self.task_in_cancelled_sprint.status, "completed")

    def test_cannot_change_status_of_completed_task_even_in_active_sprint(self):
        """Once a task is completed, its status cannot be changed back."""
        with self.assertRaises(ValidationError) as ctx:
            change_sprint_task_status(
                task_id=self.completed_task_in_active_sprint.pk,
                status="in_progress",
                changed_by=self.admin,
            )
        self.assertIn("A completed task cannot change its status.", str(ctx.exception))

        resp = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.completed_task_in_active_sprint.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(resp.status_code, 409)

        resp2 = self.client.post(
            reverse("backlog:update_task_status", args=[self.completed_task_in_active_sprint.pk]),
            {"status": "not_started"},
        )
        self.assertEqual(resp2.status_code, 302)

        self.completed_task_in_active_sprint.refresh_from_db()
        self.assertEqual(self.completed_task_in_active_sprint.status, "completed")

    # -------------------------------------------------------------
    # 5. CANNOT EDIT COMPLETED TASKS OR TASKS IN COMPLETED/CANCELLED SPRINTS
    # -------------------------------------------------------------
    def test_cannot_edit_completed_task_or_task_in_locked_sprint(self):
        """Editing completed tasks or tasks in completed/cancelled sprints is rejected."""
        # Completed task in active sprint
        resp1 = self.client.get(reverse("backlog:edit_task", args=[self.completed_task_in_active_sprint.pk]))
        self.assertEqual(resp1.status_code, 302)

        # Task in completed sprint
        resp2 = self.client.get(reverse("backlog:edit_task", args=[self.task_in_completed_sprint.pk]))
        self.assertEqual(resp2.status_code, 302)

        # Task in cancelled sprint
        resp3 = self.client.get(reverse("backlog:edit_task", args=[self.task_in_cancelled_sprint.pk]))
        self.assertEqual(resp3.status_code, 302)

    # -------------------------------------------------------------
    # 6. CANNOT MOVE COMPLETED TASKS OR TASKS OUT OF LOCKED SPRINTS
    # -------------------------------------------------------------
    def test_cannot_move_completed_tasks_or_tasks_out_of_locked_sprints(self):
        """Moving completed task or moving out of completed/cancelled sprints is rejected."""
        # Move completed task
        resp1 = self.client.post(
            reverse("backlog:move_task", args=[self.completed_task_in_active_sprint.pk]),
            {"sprint_id": ""},
        )
        self.assertEqual(resp1.status_code, 409)

        # Move out of completed sprint
        resp2 = self.client.post(
            reverse("backlog:move_task", args=[self.task_in_completed_sprint.pk]),
            {"sprint_id": ""},
        )
        self.assertEqual(resp2.status_code, 409)

        # Move out of cancelled sprint
        resp3 = self.client.post(
            reverse("backlog:move_task", args=[self.task_in_cancelled_sprint.pk]),
            {"sprint_id": ""},
        )
        self.assertEqual(resp3.status_code, 409)
