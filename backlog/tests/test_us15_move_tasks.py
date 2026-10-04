from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, Task, TaskHistory


class US15MoveTasksTestCase(TestCase):
    """
    Test suite for US-15: Move Tasks Between Product Backlog and Sprint.
    Verifies:
      - Moving tasks from Product Backlog to an active sprint
      - Moving tasks from active sprint back to Product Backlog
      - Rejecting moves into non-active sprints (planning, completed)
      - Audit trail logging in TaskHistory
      - Moving to current sprint is a no-op
      - Authentication and validation requirements
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_dev",
            password="TestPassword123!",
            first_name="Sprint",
            last_name="Developer",
        )
        self.client.force_login(self.user)

        self.active_sprint = Sprint.objects.create(
            name="Sprint 1 - Core Features",
            status="active",
        )
        self.active_sprint.team_members.add(self.user)
        self.planning_sprint = Sprint.objects.create(
            name="Sprint 2 - Future Work",
            status="planning",
        )
        self.planning_sprint.team_members.add(self.user)
        self.completed_sprint = Sprint.objects.create(
            name="Sprint 0 - Inception",
            status="completed",
        )
        self.completed_sprint.team_members.add(self.user)

        self.backlog_task = Task.objects.create(
            title="Implement user profile page",
            priority="important",
            story_points=5,
            status="not_started",
        )
        self.sprint_task = Task.objects.create(
            title="Setup database backup",
            priority="urgent",
            story_points=8,
            status="not_started",
            sprint=self.active_sprint,
        )

    def test_move_backlog_task_to_active_sprint(self):
        """AC 1: Move a task from Product Backlog into the active sprint."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.active_sprint.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])

        self.backlog_task.refresh_from_db()
        self.assertEqual(self.backlog_task.sprint, self.active_sprint)

    def test_move_task_records_task_history(self):
        """AC 4: Moving a task creates a history log with user, from and to locations."""
        self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.active_sprint.pk},
        )
        history_entry = TaskHistory.objects.filter(task=self.backlog_task).latest("timestamp")
        self.assertEqual(history_entry.changed_by, self.user)
        self.assertIn("Product Backlog", history_entry.description)
        self.assertIn(self.active_sprint.name, history_entry.description)

    def test_move_sprint_task_back_to_product_backlog(self):
        """AC 2: Move a task from active sprint back to Product Backlog."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.sprint_task.pk]),
            {"sprint_id": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])

        self.sprint_task.refresh_from_db()
        self.assertIsNone(self.sprint_task.sprint)

        history_entry = TaskHistory.objects.filter(task=self.sprint_task).latest("timestamp")
        self.assertIn(self.active_sprint.name, history_entry.description)
        self.assertIn("Product Backlog", history_entry.description)

    def test_reject_move_into_planning_sprint(self):
        """AC 3: Reject moving tasks into a non-active sprint (planning)."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.planning_sprint.pk},
        )
        self.assertEqual(response.status_code, 409)

        self.backlog_task.refresh_from_db()
        self.assertIsNone(self.backlog_task.sprint)

    def test_reject_move_into_completed_sprint(self):
        """AC 3: Reject moving tasks into a completed sprint."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.completed_sprint.pk},
        )
        self.assertEqual(response.status_code, 409)

        self.backlog_task.refresh_from_db()
        self.assertIsNone(self.backlog_task.sprint)

    def test_move_to_same_sprint_is_noop(self):
        """AC 7: Moving a task to the sprint it already belongs to returns changed=False."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.sprint_task.pk]),
            {"sprint_id": self.active_sprint.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])

    def test_move_endpoint_requires_login(self):
        """AC 5: Unauthenticated users are redirected to login."""
        self.client.logout()
        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.active_sprint.pk},
        )
        self.assertEqual(response.status_code, 302)

    def test_move_nonexistent_task_returns_404(self):
        """AC 6: Non-existent task returns 404."""
        response = self.client.post(
            reverse("backlog:move_task", args=[99999]),
            {"sprint_id": self.active_sprint.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_move_into_nonexistent_sprint_returns_409(self):
        """AC 6: Non-existent target sprint returns 409 error."""
        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": 99999},
        )
        self.assertEqual(response.status_code, 409)

    def test_move_task_with_assignee_not_in_sprint_prompts_decision(self):
        """Moving task with assignee not in sprint returns needs_assignee_decision."""
        other_user = User.objects.create_user(username="other_dev", password="Password123!")
        self.backlog_task.assignee = other_user
        self.backlog_task.save(update_fields=["assignee"])

        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {"sprint_id": self.active_sprint.pk},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertTrue(data["needs_assignee_decision"])
        self.assertEqual(data["assignee_id"], other_user.id)

    def test_move_task_with_assignee_not_in_sprint_add_to_sprint(self):
        """Action add_to_sprint adds the assignee to team_members and keeps task assignee."""
        other_user = User.objects.create_user(username="other_dev_add", password="Password123!")
        self.backlog_task.assignee = other_user
        self.backlog_task.save(update_fields=["assignee"])

        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {
                "sprint_id": self.active_sprint.pk,
                "assignee_action": "add_to_sprint",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.backlog_task.refresh_from_db()
        self.assertEqual(self.backlog_task.sprint, self.active_sprint)
        self.assertEqual(self.backlog_task.assignee, other_user)
        self.assertTrue(self.active_sprint.team_members.filter(id=other_user.id).exists())

    def test_move_task_with_assignee_not_in_sprint_remove_assignee(self):
        """Action remove_assignee clears task assignee when moving into sprint."""
        other_user = User.objects.create_user(username="other_dev_remove", password="Password123!")
        self.backlog_task.assignee = other_user
        self.backlog_task.save(update_fields=["assignee"])

        response = self.client.post(
            reverse("backlog:move_task", args=[self.backlog_task.pk]),
            {
                "sprint_id": self.active_sprint.pk,
                "assignee_action": "remove_assignee",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.backlog_task.refresh_from_db()
        self.assertEqual(self.backlog_task.sprint, self.active_sprint)
        self.assertIsNone(self.backlog_task.assignee)

