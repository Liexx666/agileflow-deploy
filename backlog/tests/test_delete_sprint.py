"""
Tests for Sprint Deletion.

Covers:
  - Only admins/superusers can delete sprints
  - Only 'not_started' or 'stopped' sprints can be deleted
  - Active, completed sprints cannot be deleted
  - Delete is a soft-delete (is_deleted=True)
  - Confirmation page is shown on GET
  - POST actually deletes the sprint
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint


class DeleteSprintTests(TestCase):
    """Test suite for the delete_sprint view."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_sprint_del",
            password="Pass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.regular_user = User.objects.create_user(
            username="regular_sprint_del",
            password="Pass123!",
        )
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user__in=[self.admin, self.regular_user]).update(must_change_password=False)

        self.not_started_sprint = Sprint.objects.create(
            name="Not Started Sprint",
            status="not_started",
        )
        self.stopped_sprint = Sprint.objects.create(
            name="Stopped Sprint",
            status="stopped",
        )
        self.active_sprint = Sprint.objects.create(
            name="Active Sprint",
            status="active",
        )
        self.completed_sprint = Sprint.objects.create(
            name="Completed Sprint",
            status="completed",
        )

    def test_non_admin_cannot_delete_sprint(self):
        """Regular users should be redirected and denied from deleting a sprint."""
        self.client.force_login(self.regular_user)
        response = self.client.post(
            reverse("backlog:delete_sprint", args=[self.not_started_sprint.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.not_started_sprint.refresh_from_db()
        self.assertFalse(self.not_started_sprint.is_deleted)

    def test_admin_can_delete_not_started_sprint(self):
        """Admin should be able to soft-delete a not-started sprint."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("backlog:delete_sprint", args=[self.not_started_sprint.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.not_started_sprint.refresh_from_db()
        self.assertTrue(self.not_started_sprint.is_deleted)

    def test_admin_can_delete_stopped_sprint(self):
        """Admin should be able to soft-delete a stopped sprint."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("backlog:delete_sprint", args=[self.stopped_sprint.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.stopped_sprint.refresh_from_db()
        self.assertTrue(self.stopped_sprint.is_deleted)

    def test_admin_cannot_delete_active_sprint(self):
        """Admin should NOT be able to delete an active sprint directly."""
        self.client.force_login(self.admin)
        self.client.post(
            reverse("backlog:delete_sprint", args=[self.active_sprint.pk])
        )
        self.active_sprint.refresh_from_db()
        self.assertFalse(self.active_sprint.is_deleted)

    def test_admin_can_delete_completed_sprint(self):
        """Admin should be able to soft-delete a completed sprint."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("backlog:delete_sprint", args=[self.completed_sprint.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.completed_sprint.refresh_from_db()
        self.assertTrue(self.completed_sprint.is_deleted)

    def test_get_request_shows_confirmation_page(self):
        """GET on delete_sprint should display the confirmation template."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("backlog:delete_sprint", args=[self.not_started_sprint.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backlog/delete_sprint.html")

    def test_deleted_sprint_does_not_appear_in_product_backlog(self):
        """After deletion, the sprint should not appear in the product backlog."""
        self.client.force_login(self.admin)
        self.client.post(
            reverse("backlog:delete_sprint", args=[self.not_started_sprint.pk])
        )
        # Flush the flash message
        self.client.get(reverse("backlog:product_backlog"))
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertNotContains(response, self.not_started_sprint.name)
        self.assertNotIn(self.not_started_sprint, response.context["sprints"])

    def test_delete_sprint_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        self.client.logout()
        response = self.client.post(
            reverse("backlog:delete_sprint", args=[self.not_started_sprint.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.not_started_sprint.refresh_from_db()
        self.assertFalse(self.not_started_sprint.is_deleted)

    def test_active_sprint_requires_stop_before_deletion(self):
        """To delete an active sprint, it must first be stopped."""
        self.client.force_login(self.admin)

        # Try deleting active sprint — should fail
        self.client.post(reverse("backlog:delete_sprint", args=[self.active_sprint.pk]))
        self.active_sprint.refresh_from_db()
        self.assertFalse(self.active_sprint.is_deleted)

        # Stop the sprint
        self.client.post(
            reverse("backlog:sprint_status", args=[self.active_sprint.pk]),
            {"status": "stopped"},
        )

        # Now delete should succeed
        self.client.post(reverse("backlog:delete_sprint", args=[self.active_sprint.pk]))
        self.active_sprint.refresh_from_db()
        self.assertTrue(self.active_sprint.is_deleted)
