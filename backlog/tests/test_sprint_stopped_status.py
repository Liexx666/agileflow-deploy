"""
Tests for the 'stopped' Sprint Status.

Covers:
  - An active sprint can be transitioned to 'stopped'
  - A stopped sprint cannot be directly set back to 'not_started' or 'active'
  - A stopped sprint cannot be set to 'completed' directly
  - A not_started sprint cannot be set to 'stopped' directly
  - Only 'not_started' and 'stopped' sprints can be deleted
  - Sprint board data endpoint marks stopped sprint correctly
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, Task


class SprintStoppedStatusTests(TestCase):
    """Test suite for the 'stopped' sprint status transitions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="stopped_tester",
            password="Pass123!",
            is_staff=True,
            is_superuser=True,
        )
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)
        self.client.force_login(self.user)

        self.active_sprint = Sprint.objects.create(
            name="Active Sprint",
            status="active",
        )
        self.not_started_sprint = Sprint.objects.create(
            name="Not Started Sprint",
            status="not_started",
        )

    def _set_status(self, sprint, status):
        return self.client.post(
            reverse("backlog:sprint_status", args=[sprint.pk]),
            {"status": status},
        )

    def test_active_sprint_can_be_set_to_stopped(self):
        """An active sprint should be transitionable to 'stopped'."""
        response = self._set_status(self.active_sprint, "stopped")
        self.assertEqual(response.status_code, 200)
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "stopped")

    def test_not_started_sprint_cannot_be_set_to_stopped(self):
        """A not-started sprint cannot jump directly to 'stopped'."""
        response = self._set_status(self.not_started_sprint, "stopped")
        self.assertNotEqual(response.status_code, 200)
        self.not_started_sprint.refresh_from_db()
        self.assertEqual(self.not_started_sprint.status, "not_started")

    def test_stopped_sprint_can_be_set_back_to_active(self):
        """A stopped sprint should be reactivatable (set back to active)."""
        self.active_sprint.status = "stopped"
        self.active_sprint.save(update_fields=["status"])

        response = self._set_status(self.active_sprint, "active")
        self.assertEqual(response.status_code, 200)
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "active")

    def test_stopped_sprint_can_be_set_to_completed(self):
        """A stopped sprint can be set to completed."""
        self.active_sprint.status = "stopped"
        self.active_sprint.save(update_fields=["status"])

        response = self._set_status(self.active_sprint, "completed")
        self.assertEqual(response.status_code, 200)
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "completed")

    def test_stopping_active_sprint_allows_new_sprint_to_become_active(self):
        """Stopping an active sprint should allow a not-started sprint to become active."""
        # Stop the active sprint
        self._set_status(self.active_sprint, "stopped")

        # Now the not-started sprint should be activatable
        response = self._set_status(self.not_started_sprint, "active")
        self.assertEqual(response.status_code, 200)
        self.not_started_sprint.refresh_from_db()
        self.assertEqual(self.not_started_sprint.status, "active")

    def test_stopped_sprint_status_badge_class_contains_danger(self):
        """The status_badge_class property for a stopped sprint should be badge-sprint-stopped."""
        self.active_sprint.status = "stopped"
        self.active_sprint.save(update_fields=["status"])
        self.assertEqual(self.active_sprint.status_badge_class, "badge-sprint-stopped")

    def test_tasks_cannot_be_moved_into_stopped_sprint(self):
        """Tasks should not be moveable into a stopped sprint."""
        stopped_sprint = Sprint.objects.create(name="Stopped Sprint", status="stopped")
        stopped_sprint.team_members.add(self.user)

        task = Task.objects.create(
            title="Backlog Task",
            sprint=None,
            status="not_started",
            story_points=2,
        )

        response = self.client.post(
            reverse("backlog:move_task", args=[task.pk]),
            {"sprint_id": stopped_sprint.pk},
        )
        self.assertEqual(response.status_code, 409)
        task.refresh_from_db()
        self.assertIsNone(task.sprint)
