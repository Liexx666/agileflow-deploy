from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, SprintBoardPreference, Task


class US17BoardViewTestCase(TestCase):
    """
    Test suite for US-17: Toggle Sprint Board Kanban/List View.
    Verifies:
      - Retrieving sprint board data grouped by status
      - Excluding deleted tasks from board data
      - Saving and loading user view preference (Kanban vs List)
      - Rejecting invalid view mode values
      - Unauthenticated access handling
      - Sprint board UI rendering
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_viewer",
            password="TestPassword123!",
            first_name="Sprint",
            last_name="Viewer",
        )
        self.client.force_login(self.user)

        self.sprint = Sprint.objects.create(
            name="Sprint 1 - Board Test",
            status="active",
        )

        self.task_not_started = Task.objects.create(
            title="Design landing page",
            priority="important",
            story_points=5,
            status="not_started",
            sprint=self.sprint,
        )
        self.task_in_progress = Task.objects.create(
            title="Implement user auth",
            priority="urgent",
            story_points=8,
            status="in_progress",
            sprint=self.sprint,
        )
        self.task_completed = Task.objects.create(
            title="Configure CI linting",
            priority="low",
            story_points=2,
            status="completed",
            sprint=self.sprint,
        )
        self.deleted_task = Task.objects.create(
            title="Discarded task",
            priority="medium",
            story_points=1,
            status="not_started",
            is_deleted=True,
            sprint=self.sprint,
        )

    def test_board_data_groups_tasks_by_status(self):
        """AC 1: Board data API returns tasks correctly grouped by status and excludes deleted tasks."""
        response = self.client.get(
            reverse("backlog:sprint_board_data", args=[self.sprint.pk])
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["view_mode"], "kanban")
        self.assertEqual(len(data["tasks"]), 3)

        self.assertEqual(len(data["tasks_by_status"]["not_started"]), 1)
        self.assertEqual(len(data["tasks_by_status"]["in_progress"]), 1)
        self.assertEqual(len(data["tasks_by_status"]["completed"]), 1)

    def test_save_and_retrieve_list_view_preference(self):
        """AC 2, AC 3, AC 4: Toggle to list view and persist user preference."""
        view_url = reverse("backlog:sprint_board_view", args=[self.sprint.pk])

        post_response = self.client.post(view_url, {"view_mode": "list"})
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(post_response.json()["view_mode"], "list")

        preference = SprintBoardPreference.objects.get(
            user=self.user,
            sprint=self.sprint,
        )
        self.assertEqual(preference.view_mode, "list")

        board_response = self.client.get(
            reverse("backlog:sprint_board_data", args=[self.sprint.pk])
        )
        self.assertEqual(board_response.json()["view_mode"], "list")

    def test_save_kanban_view_preference(self):
        """AC 2, AC 3: Toggle back to kanban view mode and verify preference update."""
        view_url = reverse("backlog:sprint_board_view", args=[self.sprint.pk])

        # Set to list first
        self.client.post(view_url, {"view_mode": "list"})
        # Switch to kanban
        response = self.client.post(view_url, {"view_mode": "kanban"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["view_mode"], "kanban")

        preference = SprintBoardPreference.objects.get(
            user=self.user,
            sprint=self.sprint,
        )
        self.assertEqual(preference.view_mode, "kanban")

    def test_reject_invalid_view_mode(self):
        """AC 5: Reject invalid view mode with 400 Bad Request."""
        response = self.client.post(
            reverse("backlog:sprint_board_view", args=[self.sprint.pk]),
            {"view_mode": "table_view_invalid"},
        )
        self.assertEqual(response.status_code, 400)

    def test_board_view_requires_login(self):
        """AC 6: Unauthenticated user is redirected to login."""
        self.client.logout()
        response = self.client.get(
            reverse("backlog:sprint_board_data", args=[self.sprint.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_sprint_board_page_renders_successfully(self):
        """AC 7: Sprint board HTML view renders with 200 OK for logged-in user."""
        response = self.client.get(reverse("backlog:sprint_board"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backlog/sprint_board.html")
