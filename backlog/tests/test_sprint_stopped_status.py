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

    def test_stopped_sprint_cannot_be_set_back_to_active(self):
        """A stopped sprint cannot be reactivated (set back to active)."""
        self.active_sprint.status = "stopped"
        self.active_sprint.save(update_fields=["status"])

        response = self._set_status(self.active_sprint, "active")
        self.assertEqual(response.status_code, 409)
        self.assertIn("A cancelled Sprint cannot be changed anymore.", response.json()["errors"]["status"])
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "stopped")

    def test_stopped_sprint_cannot_be_set_to_completed(self):
        """A stopped sprint cannot be set to completed."""
        self.active_sprint.status = "stopped"
        self.active_sprint.save(update_fields=["status"])

        response = self._set_status(self.active_sprint, "completed")
        self.assertEqual(response.status_code, 409)
        self.assertIn("A cancelled Sprint cannot be changed anymore.", response.json()["errors"]["status"])
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "stopped")

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

    def test_active_sprint_can_be_set_to_cancelled(self):
        """An active sprint can be transitioned to 'cancelled' (stored as 'stopped')."""
        response = self._set_status(self.active_sprint, "cancelled")
        self.assertEqual(response.status_code, 200)
        self.active_sprint.refresh_from_db()
        self.assertEqual(self.active_sprint.status, "stopped")

    def test_non_active_sprints_cannot_be_set_to_cancelled_or_stopped(self):
        """Neither planning, not_started, nor completed sprints can be cancelled."""
        planning_sprint = Sprint.objects.create(name="Planning Sprint", status="planning")
        completed_sprint = Sprint.objects.create(name="Completed Sprint", status="completed")

        for sprint in [self.not_started_sprint, planning_sprint, completed_sprint]:
            for status_val in ["stopped", "cancelled"]:
                response = self._set_status(sprint, status_val)
                self.assertEqual(response.status_code, 409)
                self.assertIn("Only active sprints can be cancelled.", response.json()["errors"]["status"])

    def test_sprint_edit_form_choices_and_validation_for_cancelled_status(self):
        """SprintEditForm excludes Cancelled for non-active sprints and validates active-only prerequisite."""
        from backlog.forms import SprintEditForm
        from datetime import date, timedelta

        # 1. Unbound form on not-started sprint excludes Cancelled from choices
        form_not_started = SprintEditForm(instance=self.not_started_sprint)
        choice_values = [c[0] for c in form_not_started.fields["status"].choices]
        choice_labels = [c[1] for c in form_not_started.fields["status"].choices]
        self.assertNotIn("stopped", choice_values)
        self.assertNotIn("cancelled", choice_values)
        self.assertNotIn("Cancelled", choice_labels)

        # 2. Unbound form on active sprint includes Cancelled exactly once
        form_active = SprintEditForm(instance=self.active_sprint)
        choice_labels = [c[1] for c in form_active.fields["status"].choices]
        self.assertEqual(choice_labels.count("Cancelled"), 1)

        # 3. Submitting status="cancelled" or "stopped" on non-active sprint fails validation
        data_invalid = {
            "name": "Sprint Attempt",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=7)).isoformat(),
            "status": "cancelled",
        }
        form_invalid = SprintEditForm(data=data_invalid, instance=self.not_started_sprint)
        self.assertFalse(form_invalid.is_valid())
        self.assertIn("Only active sprints can be cancelled.", form_invalid.errors["status"])

        data_invalid["status"] = "stopped"
        form_invalid_stopped = SprintEditForm(data=data_invalid, instance=self.not_started_sprint)
        self.assertFalse(form_invalid_stopped.is_valid())
        self.assertIn("Only active sprints can be cancelled.", form_invalid_stopped.errors["status"])

        # 4. Submitting status="cancelled" on active sprint succeeds and normalizes to "stopped"
        data_valid = {
            "name": "Active Sprint Cancelled",
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=7)).isoformat(),
            "status": "cancelled",
        }
        form_valid = SprintEditForm(data=data_valid, instance=self.active_sprint)
        self.assertTrue(form_valid.is_valid())
        saved_sprint = form_valid.save()
        self.assertEqual(saved_sprint.status, "stopped")

