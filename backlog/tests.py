from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import Task, Tag, Sprint


class ProductBacklogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="backlog_reader")
        self.client.force_login(self.user)

        self.tag_ui = Tag.objects.create(name="UI")
        self.tag_ux = Tag.objects.create(name="UX")
        self.tag_fe = Tag.objects.create(name="Front-end")

        self.sprint1 = Sprint.objects.create(
            name="Sprint 1",
            status="completed",
        )

        self.sprint2 = Sprint.objects.create(
            name="Sprint 2",
            status="active",
        )

        self.task1 = Task.objects.create(
            title="Task 1",
            item_type="story",
            priority="low",
            story_points=3,
        )

        self.task1.tags.add(
            self.tag_ui,
            self.tag_ux,
        )

        self.task2 = Task.objects.create(
            title="Task 2",
            item_type="story",
            priority="urgent",
            story_points=10,
        )

        self.task2.tags.add(self.tag_fe)

    def test_backlog_view_status_code(self):
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "backlog/product_backlog.html",
        )

    def test_backlog_tasks_in_context(self):
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(
            response.context["total_items"],
            2,
        )

        self.assertEqual(
            response.context["total_points"],
            13,
        )

    def test_tag_filtering(self):
        url = (
            reverse("backlog:product_backlog")
            + "?tag=Front-end"
        )

        response = self.client.get(url)
        tasks = response.context["tasks"]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Task 2")

    def test_priority_sorting_urgent_first(self):
        url = (
            reverse("backlog:product_backlog")
            + "?sort=priority_desc"
        )

        response = self.client.get(url)
        tasks = list(response.context["tasks"])

        self.assertEqual(tasks[0].title, "Task 2")
        self.assertEqual(tasks[1].title, "Task 1")

    def test_priority_sorting_lowest_first(self):
        url = (
            reverse("backlog:product_backlog")
            + "?sort=priority_asc"
        )

        response = self.client.get(url)
        tasks = list(response.context["tasks"])

        self.assertEqual(tasks[0].title, "Task 1")
        self.assertEqual(tasks[1].title, "Task 2")


class CreateTaskTests(TestCase):
    """
    Automated tests for US-04:
    Create Product Backlog Task.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse("backlog:create_task")

        self.user = User.objects.create_user(
            username="siddharth",
            first_name="Siddharth",
            last_name="Mahendran",
        )
        self.client.force_login(self.user)

        self.tag = Tag.objects.create(name="UI")

        self.valid_data = {
            "title": "Create accessible task form",
            "item_type": "story",
            "story_points": 5,
            "tags": [self.tag.id],
            "priority": "important",
            "assignee": self.user.id,
            "description": (
                "Build a validated form for creating backlog tasks."
            ),
            "status": "not_started",
            "stage": "development",
        }

    def test_create_task_page_loads(self):
        """
        The create-task page should open successfully.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "backlog/create_task.html",
        )

    def test_story_is_selected_by_default(self):
        """
        Story should be the default task type.
        """
        response = self.client.get(self.url)
        form = response.context["form"]

        self.assertEqual(
            form.fields["item_type"].initial,
            "story",
        )

    def test_valid_submission_creates_task(self):
        """
        Valid information should create and save a task.
        """
        response = self.client.post(
            self.url,
            self.valid_data,
        )

        self.assertRedirects(
            response,
            reverse("backlog:product_backlog"),
        )

        task = Task.objects.get(
            title="Create accessible task form"
        )

        self.assertEqual(task.item_type, "story")
        self.assertEqual(task.story_points, 5)
        self.assertEqual(task.priority, "important")
        self.assertEqual(task.assignee, self.user)
        self.assertEqual(task.status, "not_started")
        self.assertEqual(task.stage, "development")

        self.assertIn(
            self.tag,
            task.tags.all(),
        )

    def test_created_task_appears_in_backlog(self):
        """
        A newly created task should appear in the backlog.
        """
        self.client.post(
            self.url,
            self.valid_data,
        )

        response = self.client.get(
            reverse("backlog:product_backlog")
        )

        self.assertContains(
            response,
            "Create accessible task form",
        )

    def test_story_points_above_ten_are_rejected(self):
        """
        Story points outside the 0-10 range should fail.
        """
        invalid_data = self.valid_data.copy()
        invalid_data["story_points"] = 11

        response = self.client.post(
            self.url,
            invalid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            response.context["form"],
            "story_points",
            "Story points must be a whole number from 0 to 10.",
        )

        self.assertEqual(Task.objects.count(), 0)

    def test_at_least_one_tag_is_required(self):
        """
        A task cannot be created without a tag.
        """
        invalid_data = self.valid_data.copy()
        invalid_data["tags"] = []

        response = self.client.post(
            self.url,
            invalid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            response.context["form"],
            "tags",
            "This field is required.",
        )

        self.assertEqual(Task.objects.count(), 0)

    def test_required_information_is_enforced(self):
        """
        Required task information cannot be empty.
        """
        invalid_data = self.valid_data.copy()
        invalid_data["title"] = ""
        invalid_data["description"] = ""
        invalid_data["assignee"] = ""

        response = self.client.post(
            self.url,
            invalid_data,
        )

        form = response.context["form"]

        self.assertEqual(response.status_code, 200)
        self.assertIn("title", form.errors)
        self.assertIn("description", form.errors)
        self.assertIn("assignee", form.errors)
        self.assertEqual(Task.objects.count(), 0)

    def test_removed_fields_are_not_in_create_form(self):
        """
        Removed fields should not appear in the create-task form.
        """
        response = self.client.get(self.url)
        form = response.context["form"]

        self.assertNotIn("acceptance_criteria", form.fields)
        self.assertNotIn("attachment", form.fields)
        self.assertNotContains(response, "Acceptance criteria")
        self.assertNotContains(response, "Task attachment")