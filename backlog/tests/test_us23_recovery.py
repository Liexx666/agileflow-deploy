from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountSecurity
from backlog.models import Sprint, Task, TaskHistory


class US23RecoveryTests(TestCase):
    """ US-23: Recover Deleted Sprint/Task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="recovery_admin",
            password="Password123",
            is_staff=True,
            is_superuser=True,
        )
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)

        self.client.force_login(
            self.user
        )

        self.active_sprint = Sprint.objects.create(
            name="Active Recovery Sprint",
            goal="Recover me",
            status="active",
        )

        self.task = Task.objects.create(
            title="Recoverable Task",
            sprint=self.active_sprint,
            assignee=self.user,
            status="in_progress",
            is_deleted=True,
        )

    def test_product_backlog_has_deleted_tasks_and_deleted_sprints_links(self):
        # Product Backlog view has Deleted Tasks link
        pb_response = self.client.get(
            reverse("backlog:product_backlog_only")
        )
        self.assertEqual(pb_response.status_code, 200)
        self.assertContains(pb_response, reverse("backlog:deleted_tasks"))
        self.assertContains(pb_response, "Deleted Tasks")

        # Sprint Board (/backlog/) has Deleted Sprints link, but no Deleted Tasks
        response = self.client.get(
            reverse("backlog:product_backlog")
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("backlog:deleted_tasks"))
        self.assertNotContains(response, "Deleted Tasks")
        self.assertContains(response, reverse("backlog:deleted_sprints"))
        self.assertContains(response, "Deleted Sprints")

        # But in single sprint view, Deleted Sprints is removed
        sprint_response = self.client.get(
            reverse("backlog:sprint_backlog", args=[self.active_sprint.id])
        )
        self.assertEqual(sprint_response.status_code, 200)
        self.assertNotContains(sprint_response, "Deleted Tasks")
        self.assertNotContains(sprint_response, "Deleted Sprints")

    def test_deleted_tasks_page_shows_required_table_information(self):
        response = self.client.get(
            reverse(
                "backlog:deleted_tasks"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Task Name",
        )

        self.assertContains(
            response,
            "Last Sprint Belonged",
        )

        self.assertContains(
            response,
            "Sprint Status",
        )

        self.assertContains(
            response,
            "Date",
        )

        self.assertContains(
            response,
            self.task.title,
        )

        self.assertContains(
            response,
            self.active_sprint.name,
        )

        self.assertContains(
            response,
            "Active",
        )

    def test_deleted_sprints_page_shows_required_table_information(self):
        sprint = Sprint.objects.create(
            name="Deleted Sprint",
            goal="Archived goal",
            status="planning",
            is_deleted=True,
        )

        response = self.client.get(
            reverse(
                "backlog:deleted_sprints"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Sprint Name",
        )

        self.assertContains(
            response,
            "Goal",
        )

        self.assertContains(
            response,
            "Status",
        )

        self.assertContains(
            response,
            sprint.name,
        )

        self.assertContains(
            response,
            sprint.goal,
        )

    def test_deleted_task_page_contains_selection_confirmation_and_pagination_controls(self):
        for index in range(10):
            Task.objects.create(
                title=f"Deleted {index}",
                sprint=self.active_sprint,
                is_deleted=True,
            )

        response = self.client.get(
            reverse(
                "backlog:deleted_tasks"
            )
        )

        self.assertEqual(
            response.context["paginator"].per_page,
            10,
        )

        self.assertGreaterEqual(
            response.context["paginator"].num_pages,
            2,
        )

        self.assertContains(
            response,
            "task-select-checkbox",
        )

        self.assertContains(
            response,
            "Recover Task",
        )

        self.assertContains(
            response,
            "Confirm Task Recovery",
        )

        self.assertContains(
            response,
            "Confirm &amp; Recover",
            html=False,
        )

        self.assertContains(
            response,
            "First Page",
        )

        self.assertContains(
            response,
            "Last Page",
        )

    def test_deleted_sprint_page_contains_selection_confirmation_and_pagination_controls(self):
        for index in range(11):
            Sprint.objects.create(
                name=f"Deleted Sprint {index}",
                status="planning",
                is_deleted=True,
            )

        response = self.client.get(
            reverse(
                "backlog:deleted_sprints"
            )
        )

        self.assertEqual(
            response.context["paginator"].per_page,
            10,
        )

        self.assertGreaterEqual(
            response.context["paginator"].num_pages,
            2,
        )

        self.assertContains(
            response,
            "sprint-select-checkbox",
        )

        self.assertContains(
            response,
            "Recover Sprint",
        )

        self.assertContains(
            response,
            "Confirm Sprint Recovery",
        )

        self.assertContains(
            response,
            "First Page",
        )

        self.assertContains(
            response,
            "Last Page",
        )

    def test_recover_task_preserves_previous_status_and_sprint(self):
        response = self.client.post(
            reverse(
                "backlog:recover_task",
                args=[self.task.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.task.refresh_from_db()

        self.assertFalse(
            self.task.is_deleted
        )

        self.assertEqual(
            self.task.status,
            "in_progress",
        )

        self.assertEqual(
            self.task.sprint,
            self.active_sprint,
        )

        history = TaskHistory.objects.filter(
            task=self.task
        ).latest(
            "timestamp"
        )

        self.assertIn(
            "recovered",
            history.description,
        )

    def test_recovered_task_reappears_on_sprint_board(self):
        self.client.post(
            reverse(
                "backlog:recover_task",
                args=[self.task.pk],
            )
        )

        response = self.client.get(
            reverse(
                "backlog:sprint_board_detail",
                args=[self.active_sprint.pk],
            )
        )

        self.assertContains(
            response,
            self.task.title,
        )

    def test_task_from_completed_sprint_cannot_be_recovered(self):
        completed_sprint = Sprint.objects.create(
            name="Completed Sprint",
            status="completed",
        )

        task = Task.objects.create(
            title="Locked Deleted Task",
            sprint=completed_sprint,
            status="in_progress",
            is_deleted=True,
        )

        response = self.client.post(
            reverse(
                "backlog:recover_task",
                args=[task.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        task.refresh_from_db()

        self.assertTrue(
            task.is_deleted
        )

    def test_active_and_incomplete_task_can_be_recovered(self):
        self.assertTrue(
            self.task.is_deleted
        )

        self.client.post(
            reverse(
                "backlog:recover_task",
                args=[self.task.pk],
            )
        )

        self.task.refresh_from_db()

        self.assertFalse(
            self.task.is_deleted
        )

        self.assertEqual(
            self.task.status,
            "in_progress",
        )

    def test_deleted_sprint_can_be_recovered_without_resetting_status(self):
        self.active_sprint.status = "completed"
        self.active_sprint.save(
            update_fields=["status"]
        )

        sprint = Sprint.objects.create(
            name="Recover Active Sprint",
            status="active",
            is_deleted=True,
        )

        response = self.client.post(
            reverse(
                "backlog:recover_sprint",
                args=[sprint.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        sprint.refresh_from_db()

        self.assertFalse(
            sprint.is_deleted
        )

        self.assertEqual(
            sprint.status,
            "active",
        )

    def test_recovered_sprint_reappears_in_product_backlog(self):
        sprint = Sprint.objects.create(
            name="Restored Planning Sprint",
            status="planning",
            is_deleted=True,
        )

        self.client.post(
            reverse(
                "backlog:recover_sprint",
                args=[sprint.pk],
            )
        )

        response = self.client.get(
            reverse(
                "backlog:product_backlog"
            )
        )

        self.assertContains(
            response,
            sprint.name,
        )

    def test_recovery_endpoints_require_post(self):
        task_response = self.client.get(
            reverse(
                "backlog:recover_task",
                args=[self.task.pk],
            )
        )

        self.assertRedirects(
            task_response,
            reverse(
                "backlog:deleted_tasks"
            ),
        )

        sprint = Sprint.objects.create(
            name="Deleted GET Sprint",
            status="planning",
            is_deleted=True,
        )

        sprint_response = self.client.get(
            reverse(
                "backlog:recover_sprint",
                args=[sprint.pk],
            )
        )

        self.assertRedirects(
            sprint_response,
            reverse(
                "backlog:deleted_sprints"
            ),
        )