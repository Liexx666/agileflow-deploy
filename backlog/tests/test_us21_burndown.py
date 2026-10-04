from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from backlog.burndown import (
    build_sprint_burndown,
    percentage_left,
    sprint_workload,
)
from backlog.models import (
    Sprint,
    SprintBurndownSnapshot,
    Task,
)


class US21BurndownTests(TestCase):
    """US-21: View Sprint Burndown Chart."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="burndown_member"
        )
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)

        today = timezone.localdate()

        self.sprint = Sprint.objects.create(
            name="Burndown Sprint",
            status="active",
            start_date=today,
            end_date=today + timedelta(days=6),
        )

        self.sprint.team_members.add(
            self.user
        )

        self.task_a = Task.objects.create(
            title="Story A",
            sprint=self.sprint,
            assignee=self.user,
            story_points=5,
            status="not_started",
        )

        self.task_b = Task.objects.create(
            title="Story B",
            sprint=self.sprint,
            assignee=self.user,
            story_points=3,
            status="completed",
        )

        self.client.force_login(
            self.user
        )

    def test_work_left_percentage_uses_incomplete_over_total_story_points(self):
        total, remaining = sprint_workload(
            self.sprint
        )

        self.assertEqual(
            total,
            8,
        )

        self.assertEqual(
            remaining,
            5,
        )

        self.assertEqual(
            percentage_left(
                total,
                remaining,
            ),
            62.5,
        )

        data = build_sprint_burndown(
            self.sprint
        )

        self.assertEqual(
            data["total_story_points"],
            8,
        )

        self.assertEqual(
            data["remaining_story_points"],
            5,
        )

        self.assertEqual(
            data["remaining_percentage"],
            62.5,
        )

    def test_chart_contains_sprint_dates_ideal_and_actual_lines(self):
        data = build_sprint_burndown(
            self.sprint
        )

        self.assertTrue(
            data["available"]
        )

        self.assertEqual(
            data["labels"][0],
            f"{self.sprint.start_date.isoformat()} (start)",
        )

        self.assertEqual(
            data["labels"][1],
            self.sprint.start_date.isoformat(),
        )

        self.assertEqual(
            len(data["labels"]),
            8,
        )

        self.assertEqual(
            len(data["ideal"]),
            len(data["labels"]),
        )

        self.assertEqual(
            len(data["actual"]),
            len(data["labels"]),
        )

        self.assertEqual(
            data["ideal"][0],
            100,
        )

        self.assertEqual(
            data["actual"][0],
            100,
        )

    def test_initial_remaining_work_represents_all_planned_work(self):
        data = build_sprint_burndown(
            self.sprint
        )

        self.assertEqual(
            data["actual"][0],
            100,
        )

        self.assertEqual(
            data["ideal"][0],
            100,
        )

    def test_completing_task_reduces_remaining_story_points(self):
        before = build_sprint_burndown(
            self.sprint
        )

        self.assertEqual(
            before["remaining_story_points"],
            5,
        )

        self.task_a.status = "completed"
        self.task_a.save(
            update_fields=["status"]
        )

        after = build_sprint_burndown(
            self.sprint
        )

        self.assertEqual(
            after["remaining_story_points"],
            0,
        )

        self.assertEqual(
            after["remaining_percentage"],
            0,
        )

    def test_deleted_tasks_are_not_counted_in_burndown(self):
        self.task_a.is_deleted = True
        self.task_a.save(
            update_fields=["is_deleted"]
        )

        total, remaining = sprint_workload(
            self.sprint
        )

        self.assertEqual(
            total,
            3,
        )

        self.assertEqual(
            remaining,
            0,
        )

    def test_burndown_endpoint_returns_current_chart_data(self):
        response = self.client.get(
            reverse(
                "backlog:sprint_burndown",
                args=[self.sprint.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["ok"]
        )

        self.assertEqual(
            payload["burndown"]["sprint_id"],
            self.sprint.pk,
        )

        self.assertEqual(
            payload["burndown"]["remaining_percentage"],
            62.5,
        )

    def test_sprint_board_displays_line_chart_container_and_summary(self):
        response = self.client.get(
            reverse(
                "backlog:sprint_board_detail",
                args=[self.sprint.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'id="burndownChart"',
        )

        self.assertContains(
            response,
            "ideal and actual remaining work",
        )

        self.assertContains(
            response,
            "Remaining: 5 / 8 story points (62.5%)",
        )

    def test_invalid_sprint_dates_make_chart_unavailable(self):
        self.sprint.end_date = (
            self.sprint.start_date
            - timedelta(days=1)
        )

        self.sprint.save(
            update_fields=["end_date"]
        )

        data = build_sprint_burndown(
            self.sprint
        )

        self.assertFalse(
            data["available"]
        )

        self.assertIn(
            "valid Sprint start and end date",
            data["note"],
        )

    def test_snapshot_model_stores_daily_actual_progress(self):
        snapshot = SprintBurndownSnapshot.objects.create(
            sprint=self.sprint,
            date=timezone.localdate(),
            total_story_points=8,
            remaining_story_points=5,
        )

        data = build_sprint_burndown(
            self.sprint
        )

        self.assertEqual(
            snapshot.remaining_story_points,
            5,
        )

        self.assertIn(
            62.5,
            [
                value
                for value in data["actual"]
                if value is not None
            ],
        )

    def test_task_status_change_endpoint_returns_updated_burndown_simultaneously(self):
        # Before: 8 total, 5 remaining (task_a is 5 pts not_started, task_b is 3 pts completed) -> 62.5%
        response = self.client.post(
            reverse("backlog:sprint_task_status", args=[self.task_a.pk]),
            {"status": "completed"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["changed"])
        burndown = payload["burndown"]
        self.assertIsNotNone(burndown)
        self.assertEqual(burndown["total_story_points"], 8)
        self.assertEqual(burndown["remaining_story_points"], 0)
        self.assertEqual(burndown["remaining_percentage"], 0.0)