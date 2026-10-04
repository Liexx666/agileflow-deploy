from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, Task, TaskHistory


class US16TaskStatusTestCase(TestCase):
    """
    Test suite for US-16: Manage Sprint Task Status.
    Verifies:
      - Changing status of a task in an active sprint (not_started, in_progress, completed)
      - History logging for status transitions
      - Rejecting status updates on tasks in Product Backlog
      - Rejecting status updates on tasks in non-active (completed/planning) sprints
      - Rejecting invalid status values
      - No-op when setting identical status
      - Authentication requirements
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_tester",
            password="TestPassword123!",
            first_name="Sprint",
            last_name="Tester",
        )
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)
        self.client.force_login(self.user)

        self.active_sprint = Sprint.objects.create(
            name="Sprint 1 - Active",
            status="active",
        )
        self.active_sprint.team_members.add(self.user)
        self.completed_sprint = Sprint.objects.create(
            name="Sprint 0 - Completed",
            status="completed",
        )
        self.completed_sprint.team_members.add(self.user)
        self.planning_sprint = Sprint.objects.create(
            name="Sprint 2 - Planning",
            status="planning",
        )
        self.planning_sprint.team_members.add(self.user)

        self.sprint_task = Task.objects.create(
            title="Setup CI pipeline",
            priority="urgent",
            story_points=3,
            status="not_started",
            sprint=self.active_sprint,
        )
        self.backlog_task = Task.objects.create(
            title="Write API documentation",
            priority="medium",
            story_points=2,
            status="not_started",
        )

    def test_change_task_status_to_in_progress(self):
        """AC 1: Change status from not_started to in_progress."""
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertIn("burndown", response.json())
        self.assertEqual(response.json()["burndown"]["remaining_story_points"], 3)

        self.sprint_task.refresh_from_db()
        self.assertEqual(self.sprint_task.status, "in_progress")

    def test_change_task_status_to_completed(self):
        """AC 1: Change status to completed and verify burndown is simultaneously updated."""
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "completed"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertIn("burndown", response.json())
        self.assertEqual(response.json()["burndown"]["remaining_story_points"], 0)
        self.assertEqual(response.json()["burndown"]["remaining_percentage"], 0.0)

        self.sprint_task.refresh_from_db()
        self.assertEqual(self.sprint_task.status, "completed")

    def test_status_change_records_task_history(self):
        """AC 2: Status transition is logged in TaskHistory with user and change details."""
        self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "in_progress"},
        )
        history_entry = TaskHistory.objects.filter(task=self.sprint_task).latest("timestamp")
        self.assertEqual(history_entry.changed_by, self.user)
        self.assertIn("Not Started to In Progress", history_entry.description)

    def test_reject_status_change_for_backlog_task(self):
        """AC 3: Reject status change for tasks not assigned to any sprint."""
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.backlog_task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 409)

        self.backlog_task.refresh_from_db()
        self.assertEqual(self.backlog_task.status, "not_started")

    def test_reject_status_change_in_completed_sprint(self):
        """AC 4: Reject status change for tasks in completed sprint."""
        completed_task = Task.objects.create(
            title="Archived Task",
            sprint=self.completed_sprint,
            status="completed",
        )
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[completed_task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 409)

    def test_reject_status_change_in_planning_sprint(self):
        """AC 4: Reject status change for tasks in planning sprint."""
        planning_task = Task.objects.create(
            title="Planned Task",
            sprint=self.planning_sprint,
            status="not_started",
        )
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[planning_task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 409)

    def test_reject_invalid_task_status(self):
        """AC 5: Reject invalid status value with 400 Bad Request."""
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "invalid_status_xyz"},
        )
        self.assertEqual(response.status_code, 400)

        self.sprint_task.refresh_from_db()
        self.assertEqual(self.sprint_task.status, "not_started")

    def test_same_status_change_is_noop(self):
        """AC 6: Setting identical status returns changed=False."""
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "not_started"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])

    def test_task_status_endpoint_requires_login(self):
        """AC 7: Unauthenticated users are redirected to login."""
        self.client.logout()
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.sprint_task.pk]),
            {"status": "in_progress"},
        )
        self.assertEqual(response.status_code, 302)
