from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint


class US18SprintStatusTestCase(TestCase):
    """
    Test suite for US-18: Manage Sprint Status.
    Verifies:
      - Updating sprint status (planning, active, completed)
      - Single active sprint constraint enforcement at API level (409 Conflict)
      - Transition from active to completed enabling new active sprint
      - Database IntegrityError constraint for single active sprint
      - Rejecting invalid status choices
      - Authentication requirements
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_manager",
            password="TestPassword123!",
            first_name="Sprint",
            last_name="Manager",
        )
        self.client.force_login(self.user)

        self.active_sprint = Sprint.objects.create(
            name="Sprint 1 - In Progress",
            status="active",
        )
        self.planning_sprint = Sprint.objects.create(
            name="Sprint 2 - Planned",
            status="planning",
        )

    def test_reject_second_active_sprint_via_api(self):
        """AC 2, AC 3: Attempting to activate a second sprint returns 409 Conflict."""
        response = self.client.post(
            reverse("backlog:sprint_status", args=[self.planning_sprint.pk]),
            {"status": "active"},
        )
        self.assertEqual(response.status_code, 409)

        self.planning_sprint.refresh_from_db()
        self.assertEqual(self.planning_sprint.status, "planning")

    def test_complete_active_sprint_then_activate_next_sprint(self):
        """AC 4: Completing an active sprint allows another sprint to become active."""
        # 1. Complete active sprint
        complete_resp = self.client.post(
            reverse("backlog:sprint_status", args=[self.active_sprint.pk]),
            {"status": "completed"},
        )
        self.assertEqual(complete_resp.status_code, 200)

        # 2. Activate planning sprint
        activate_resp = self.client.post(
            reverse("backlog:sprint_status", args=[self.planning_sprint.pk]),
            {"status": "active"},
        )
        self.assertEqual(activate_resp.status_code, 200)

        self.active_sprint.refresh_from_db()
        self.planning_sprint.refresh_from_db()

        self.assertEqual(self.active_sprint.status, "completed")
        self.assertEqual(self.planning_sprint.status, "active")

    def test_database_constraint_prevents_two_active_sprints(self):
        """AC 5: Database constraint throws IntegrityError if second active sprint is created."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Sprint.objects.create(
                    name="Illegal Second Active Sprint",
                    status="active",
                )

    def test_reject_invalid_sprint_status(self):
        """AC 6: Reject invalid sprint status with 400 Bad Request."""
        response = self.client.post(
            reverse("backlog:sprint_status", args=[self.planning_sprint.pk]),
            {"status": "archived_cancelled"},
        )
        self.assertEqual(response.status_code, 400)

    def test_same_status_update_is_noop(self):
        """Updating to identical status returns changed=False."""
        response = self.client.post(
            reverse("backlog:sprint_status", args=[self.planning_sprint.pk]),
            {"status": "planning"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])

    def test_sprint_status_endpoint_requires_login(self):
        """AC 7: Unauthenticated users are redirected to login."""
        self.client.logout()
        response = self.client.post(
            reverse("backlog:sprint_status", args=[self.planning_sprint.pk]),
            {"status": "completed"},
        )
        self.assertEqual(response.status_code, 302)
