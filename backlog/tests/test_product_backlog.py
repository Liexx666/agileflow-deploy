from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Task, Tag, Sprint


class ProductBacklogTests(TestCase):
    """
    Automated tests for viewing and interacting with the Product Backlog.
    """

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
