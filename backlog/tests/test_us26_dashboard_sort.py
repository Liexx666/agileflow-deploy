from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backlog.models import Task, TaskWorkSession


TEST_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {
                        "backlog/admin_dashboard.html": "{{ members }}",
                    },
                ),
            ],
        },
    },
]


@override_settings(TEMPLATES=TEST_TEMPLATES)
class US26DashboardSortingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="dashboard_admin",
            email="admin@example.com",
            password="password123",
            is_staff=True,
        )

        self.low_member = User.objects.create_user(
            username="low_member",
            email="low@example.com",
            password="password123",
        )

        self.medium_member = User.objects.create_user(
            username="medium_member",
            email="medium@example.com",
            password="password123",
        )

        self.high_member = User.objects.create_user(
            username="high_member",
            email="high@example.com",
            password="password123",
        )

        self.task = Task.objects.create(
            title="Dashboard sorting test task",
        )

        self.url = reverse("backlog:admin_dashboard")
        self.test_date = timezone.localdate()

        self.create_session(
            self.low_member,
            1,
        )

        self.create_session(
            self.medium_member,
            3,
        )

        self.create_session(
            self.high_member,
            5,
        )

        self.client.force_login(self.admin)

    def create_session(self, user, hours):
        current_timezone = timezone.get_current_timezone()

        started_at = timezone.make_aware(
            datetime.combine(
                self.test_date,
                datetime.min.time(),
            ).replace(hour=9),
            current_timezone,
        )

        ended_at = started_at + timedelta(
            hours=hours,
        )

        TaskWorkSession.objects.create(
            task=self.task,
            user=user,
            started_at=started_at,
            ended_at=ended_at,
        )

    def get_dashboard(self, sort_order):
        return self.client.get(
            self.url,
            {
                "start_date": self.test_date.isoformat(),
                "end_date": self.test_date.isoformat(),
                "sort": sort_order,
            },
        )

    def test_sort_lowest_to_highest(self):
        response = self.get_dashboard(
            "low_to_high"
        )

        usernames = [
            item["user"].username
            for item in response.context["members"]
        ]

        self.assertEqual(
            usernames,
            [
                "low_member",
                "medium_member",
                "high_member",
            ],
        )

    def test_sort_highest_to_lowest(self):
        response = self.get_dashboard(
            "high_to_low"
        )

        usernames = [
            item["user"].username
            for item in response.context["members"]
        ]

        self.assertEqual(
            usernames,
            [
                "high_member",
                "medium_member",
                "low_member",
            ],
        )

    def test_low_to_high_average_values_are_correctly_ordered(self):
        response = self.get_dashboard(
            "low_to_high"
        )

        averages = [
            item["average_seconds"]
            for item in response.context["members"]
        ]

        self.assertEqual(
            averages,
            sorted(averages),
        )

    def test_high_to_low_average_values_are_correctly_ordered(self):
        response = self.get_dashboard(
            "high_to_low"
        )

        averages = [
            item["average_seconds"]
            for item in response.context["members"]
        ]

        self.assertEqual(
            averages,
            sorted(
                averages,
                reverse=True,
            ),
        )

    def test_sorting_uses_calculated_average_time(self):
        response = self.get_dashboard(
            "high_to_low"
        )

        members = response.context["members"]

        self.assertEqual(
            members[0]["average_hours"],
            5.0,
        )

        self.assertEqual(
            members[1]["average_hours"],
            3.0,
        )

        self.assertEqual(
            members[2]["average_hours"],
            1.0,
        )