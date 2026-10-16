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
                        "backlog/dashboard_member_detail.html": "{{ member }}",
                    },
                ),
            ],
        },
    },
]


@override_settings(TEMPLATES=TEST_TEMPLATES)
class US24AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="dashboard_admin",
            email="admin@example.com",
            password="password123",
            is_staff=True,
        )

        self.member_one = User.objects.create_user(
            username="member_one",
            email="member1@example.com",
            password="password123",
            first_name="Member",
            last_name="One",
        )

        self.member_two = User.objects.create_user(
            username="member_two",
            email="member2@example.com",
            password="password123",
            first_name="Member",
            last_name="Two",
        )

        self.task = Task.objects.create(
            title="Dashboard test task",
        )

        self.url = reverse("backlog:admin_dashboard")

        self.start_date = timezone.localdate() - timedelta(days=2)
        self.end_date = timezone.localdate()

    def create_session(self, user, date, start_hour, end_hour):
        current_timezone = timezone.get_current_timezone()

        started_at = timezone.make_aware(
            datetime.combine(
                date,
                datetime.min.time(),
            ).replace(hour=start_hour),
            current_timezone,
        )

        ended_at = timezone.make_aware(
            datetime.combine(
                date,
                datetime.min.time(),
            ).replace(hour=end_hour),
            current_timezone,
        )

        return TaskWorkSession.objects.create(
            task=self.task,
            user=user,
            started_at=started_at,
            ended_at=ended_at,
        )

    def get_dashboard(self, **extra):
        params = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }
        params.update(extra)

        return self.client.get(
            self.url,
            params,
        )

    def test_admin_can_access_dashboard(self):
        self.client.force_login(self.admin)

        response = self.get_dashboard()

        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_access_dashboard(self):
        self.client.force_login(self.member_one)

        response = self.get_dashboard()

        self.assertRedirects(
            response,
            reverse("backlog:product_backlog"),
            fetch_redirect_response=False,
        )

    def test_dashboard_contains_registered_team_members(self):
        self.client.force_login(self.admin)

        response = self.get_dashboard()

        users = [
            item["user"]
            for item in response.context["members"]
        ]

        self.assertIn(self.member_one, users)
        self.assertIn(self.member_two, users)
        self.assertNotIn(self.admin, users)

    def test_selected_date_range_is_used(self):
        self.client.force_login(self.admin)

        response = self.get_dashboard()

        self.assertEqual(
            response.context["start_date"],
            self.start_date,
        )

        self.assertEqual(
            response.context["end_date"],
            self.end_date,
        )

        self.assertEqual(
            response.context["day_count"],
            3,
        )

    def test_average_time_is_calculated_per_calendar_day(self):
        self.create_session(
            self.member_one,
            self.start_date,
            9,
            12,
        )

        self.create_session(
            self.member_one,
            self.end_date,
            9,
            12,
        )

        self.client.force_login(self.admin)

        response = self.get_dashboard()

        member_data = next(
            item
            for item in response.context["members"]
            if item["user"] == self.member_one
        )

        self.assertEqual(
            member_data["total_hours"],
            6.0,
        )

        self.assertEqual(
            member_data["average_hours"],
            2.0,
        )

    def test_days_without_recorded_work_count_as_zero(self):
        self.create_session(
            self.member_one,
            self.start_date,
            9,
            12,
        )

        self.client.force_login(self.admin)

        response = self.get_dashboard()

        member_data = next(
            item
            for item in response.context["members"]
            if item["user"] == self.member_one
        )

        self.assertEqual(
            member_data["total_hours"],
            3.0,
        )

        self.assertEqual(
            member_data["average_hours"],
            1.0,
        )

    def test_member_with_no_work_has_zero_average(self):
        self.client.force_login(self.admin)

        response = self.get_dashboard()

        member_data = next(
            item
            for item in response.context["members"]
            if item["user"] == self.member_two
        )

        self.assertEqual(
            member_data["total_hours"],
            0.0,
        )

        self.assertEqual(
            member_data["average_hours"],
            0.0,
        )

    def test_sessions_outside_selected_range_are_not_counted(self):
        outside_date = self.start_date - timedelta(days=1)

        self.create_session(
            self.member_one,
            outside_date,
            9,
            15,
        )

        self.create_session(
            self.member_one,
            self.start_date,
            9,
            12,
        )

        self.client.force_login(self.admin)

        response = self.get_dashboard()

        member_data = next(
            item
            for item in response.context["members"]
            if item["user"] == self.member_one
        )

        self.assertEqual(
            member_data["total_hours"],
            3.0,
        )

    def test_session_overlapping_selected_range_is_partially_counted(self):
        current_timezone = timezone.get_current_timezone()

        started_at = timezone.make_aware(
            datetime.combine(
                self.start_date - timedelta(days=1),
                datetime.min.time(),
            ).replace(hour=23),
            current_timezone,
        )

        ended_at = timezone.make_aware(
            datetime.combine(
                self.start_date,
                datetime.min.time(),
            ).replace(hour=2),
            current_timezone,
        )

        TaskWorkSession.objects.create(
            task=self.task,
            user=self.member_one,
            started_at=started_at,
            ended_at=ended_at,
        )

        self.client.force_login(self.admin)

        response = self.get_dashboard()

        member_data = next(
            item
            for item in response.context["members"]
            if item["user"] == self.member_one
        )

        self.assertEqual(
            member_data["total_hours"],
            2.0,
        )

    def test_admin_can_view_member_details(self):
        self.client.force_login(self.admin)

        detail_url = reverse(
            "backlog:dashboard_member_detail",
            args=[self.member_one.pk],
        )

        response = self.client.get(
            detail_url,
            {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["member"],
            self.member_one,
        )

    def test_non_admin_cannot_view_member_details(self):
        self.client.force_login(self.member_two)

        detail_url = reverse(
            "backlog:dashboard_member_detail",
            args=[self.member_one.pk],
        )

        response = self.client.get(detail_url)

        self.assertRedirects(
            response,
            reverse("backlog:product_backlog"),
            fetch_redirect_response=False,
        )