from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Task, Tag


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
        Required task information (title, description) cannot be empty.
        """
        invalid_data = self.valid_data.copy()
        invalid_data["title"] = ""
        invalid_data["description"] = ""

        response = self.client.post(
            self.url,
            invalid_data,
        )

        form = response.context["form"]

        self.assertEqual(response.status_code, 200)
        self.assertIn("title", form.errors)
        self.assertIn("description", form.errors)
        self.assertEqual(Task.objects.count(), 0)

    def test_create_task_with_empty_assignee(self):
        """
        Task assignee is optional and can be left empty.
        """
        data = self.valid_data.copy()
        data["assignee"] = ""

        response = self.client.post(
            self.url,
            data,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.count(), 1)
        task = Task.objects.first()
        self.assertIsNone(task.assignee)

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
