"""
Tests for automatic movement of incomplete tasks back to the Product Backlog
when a sprint is cancelled (status set to 'stopped' or 'cancelled').

Requirement:
Whenever a sprint is cancelled (ie sprint status set to cancelled),
all incompleted tasks automatically go back to the product backlog
(this includes active/in_progress and not started tasks).
Every task except for those with a task status of 'completed' will move back
to the product backlog.
"""
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountSecurity
from backlog.models import Sprint, Task, TaskHistory
from backlog.sprint_services import change_sprint_status


class CancelSprintTaskMovementTests(TestCase):
    """Test suite for moving incomplete tasks back to product backlog upon sprint cancellation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_manager",
            first_name="Jane",
            last_name="Doe",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )
        self.member = User.objects.create_user(
            username="dev_member",
            first_name="Dev",
            last_name="Member",
            password="Password123!",
            is_staff=False,
            is_superuser=False,
        )
        AccountSecurity.objects.filter(user__in=[self.user, self.member]).update(must_change_password=False)
        self.client.force_login(self.user)

        self.today = timezone.localdate()
        self.sprint = Sprint.objects.create(
            name="Sprint 1",
            status="active",
            start_date=self.today,
            end_date=self.today + timedelta(days=14),
            product_owner=self.user,
            scrum_master=self.user,
        )
        self.sprint.team_members.add(self.member)

        # Create tasks with different statuses attached to the active sprint
        self.task_not_started = Task.objects.create(
            title="Design landing page wireframe",
            status="not_started",
            item_type="story",
            story_points=3,
            sprint=self.sprint,
        )
        self.task_in_progress = Task.objects.create(
            title="Implement OAuth authentication",
            status="in_progress",
            item_type="story",
            story_points=5,
            sprint=self.sprint,
        )
        self.task_completed = Task.objects.create(
            title="Set up PostgreSQL database schema",
            status="completed",
            item_type="story",
            story_points=2,
            sprint=self.sprint,
        )

    def test_change_sprint_status_moves_incomplete_tasks_to_product_backlog(self):
        """
        When change_sprint_status is used to cancel a sprint:
        - not_started tasks move to sprint=None (Product Backlog)
        - in_progress tasks move to sprint=None (Product Backlog)
        - completed tasks remain in the sprint
        - TaskHistory is recorded for each moved task
        """
        sprint, changed = change_sprint_status(
            sprint_id=self.sprint.pk,
            status="stopped",
            changed_by=self.user,
        )
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "stopped")

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        # Incomplete tasks moved back to product backlog
        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)

        # Completed task remains in sprint
        self.assertEqual(self.task_completed.sprint, self.sprint)

        # Verify TaskHistory was logged for moved tasks
        ns_history = TaskHistory.objects.filter(task=self.task_not_started).latest("timestamp")
        self.assertEqual(ns_history.changed_by, self.user)
        self.assertIn("back to Product Backlog because sprint 'Sprint 1' was cancelled", ns_history.description)

        ip_history = TaskHistory.objects.filter(task=self.task_in_progress).latest("timestamp")
        self.assertEqual(ip_history.changed_by, self.user)
        self.assertIn("back to Product Backlog because sprint 'Sprint 1' was cancelled", ip_history.description)

        # Completed task has no cancellation TaskHistory
        self.assertFalse(
            TaskHistory.objects.filter(
                task=self.task_completed,
                description__contains="was cancelled"
            ).exists()
        )

    def test_change_sprint_status_with_cancelled_alias(self):
        """
        Passing status='cancelled' should also move incomplete tasks to Product Backlog
        and preserve completed tasks.
        """
        sprint, changed = change_sprint_status(
            sprint_id=self.sprint.pk,
            status="cancelled",
            changed_by=self.user,
        )
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "stopped")

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)
        self.assertEqual(self.task_completed.sprint, self.sprint)

    def test_edit_sprint_view_moves_incomplete_tasks_on_cancellation(self):
        """
        When editing a sprint via the edit_sprint view and setting status to 'stopped',
        incomplete tasks are returned to the product backlog and completed tasks stay.
        """
        response = self.client.post(
            reverse("backlog:edit_sprint", args=[self.sprint.pk]),
            {
                "name": "Sprint 1 Updated",
                "start_date": self.sprint.start_date.isoformat(),
                "end_date": self.sprint.end_date.isoformat(),
                "goal": "Finish feature set",
                "status": "stopped",
                "team_members": [self.member.pk],
            },
        )
        self.assertEqual(response.status_code, 302)

        self.sprint.refresh_from_db()
        self.assertEqual(self.sprint.status, "stopped")

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)
        self.assertEqual(self.task_completed.sprint, self.sprint)

        # Check TaskHistory was created
        history_entry = TaskHistory.objects.filter(task=self.task_not_started).latest("timestamp")
        self.assertEqual(history_entry.changed_by, self.user)
        self.assertIn("back to Product Backlog", history_entry.description)

    def test_sprint_status_endpoint_moves_incomplete_tasks(self):
        """
        When cancelling via the sprint_status AJAX endpoint, incomplete tasks move to PB
        and completed tasks remain in the sprint.
        """
        response = self.client.post(
            reverse("backlog:sprint_status", args=[self.sprint.pk]),
            {"status": "stopped"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)
        self.assertEqual(self.task_completed.sprint, self.sprint)

    def test_direct_model_save_moves_incomplete_tasks(self):
        """
        Directly setting sprint.status = 'stopped' and saving invokes task return
        with 'System' as default actor when _changed_by is not set.
        """
        self.sprint.status = "stopped"
        self.sprint.save()

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)
        self.assertEqual(self.task_completed.sprint, self.sprint)

        history_entry = TaskHistory.objects.filter(task=self.task_not_started).latest("timestamp")
        self.assertIn("System moved", history_entry.description)

    def test_re_saving_already_cancelled_sprint_does_not_retrigger(self):
        """
        Saving an already stopped/cancelled sprint again does not re-run task movement
        or create duplicate TaskHistory records.
        """
        self.sprint.status = "stopped"
        self.sprint.save()

        initial_history_count = TaskHistory.objects.count()

        # Update sprint name and save again
        self.sprint.name = "Renamed Cancelled Sprint"
        self.sprint.save()

        self.assertEqual(TaskHistory.objects.count(), initial_history_count)

    def test_completing_sprint_moves_incomplete_tasks(self):
        """
        When an active sprint is completed (status set to 'completed'), incomplete tasks
        move back to the product backlog, and completed tasks remain in the sprint.
        """
        sprint, changed = change_sprint_status(
            sprint_id=self.sprint.pk,
            status="completed",
            changed_by=self.user,
        )
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "completed")

        self.task_not_started.refresh_from_db()
        self.task_in_progress.refresh_from_db()
        self.task_completed.refresh_from_db()

        # Incomplete tasks move back to product backlog, completed tasks remain
        self.assertIsNone(self.task_not_started.sprint)
        self.assertIsNone(self.task_in_progress.sprint)
        self.assertEqual(self.task_completed.sprint, self.sprint)
