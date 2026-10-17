from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.views import _calculate_dashboard_metrics
from backlog.models import Task, TaskWorkSession


class DashboardTimeAccuracyTests(TestCase):
    def setUp(self):
        self.member = get_user_model().objects.create_user(username="qa_accuracy", first_name="QA", last_name="Accuracy")
        self.task = Task.objects.create(title="QA time accuracy")
        self.start = date(2026, 10, 12)
        self.end = date(2026, 10, 14)

    def session(self, start, end):
        tz = timezone.get_current_timezone()
        return TaskWorkSession.objects.create(
            task=self.task, user=self.member,
            started_at=timezone.make_aware(datetime.fromisoformat(start), tz),
            ended_at=timezone.make_aware(datetime.fromisoformat(end), tz),
        )

    def metrics(self, start=None, end=None):
        rows, charts, days = _calculate_dashboard_metrics(start or self.start, end or self.end)
        row = next(r for r in rows if r["id"] == self.member.pk)
        return row, charts[self.member.username], days

    def test_cross_midnight_overlap_matches_daily_and_overall_totals(self):
        self.session("2026-10-11T22:00:00", "2026-10-12T01:00:00")
        self.session("2026-10-12T10:00:00", "2026-10-12T12:00:00")
        self.session("2026-10-14T10:00:00", "2026-10-14T14:00:00")
        self.session("2026-10-14T23:00:00", "2026-10-15T02:00:00")
        self.session("2026-10-15T02:00:00", "2026-10-15T03:00:00")
        row, chart, days = self.metrics()
        self.assertEqual(row["total_seconds"], 28800)
        self.assertEqual(row["avg_seconds"], 9600)
        self.assertEqual([d["seconds"] for d in chart], [10800, 0, 18000])
        self.assertEqual(sum(d["seconds"] for d in chart), row["total_seconds"])
        self.assertEqual(days, 3)

    def test_full_calendar_day_keeps_the_last_second(self):
        self.session("2026-10-12T00:00:00", "2026-10-13T00:00:00")
        row, chart, _ = self.metrics(self.start, self.start)
        self.assertEqual(row["total_seconds"], 86400)
        self.assertEqual(chart[0]["seconds"], 86400)

    def test_four_minutes_are_preserved_as_exact_seconds(self):
        self.session("2026-10-12T10:00:00", "2026-10-12T10:04:00")
        row, chart, _ = self.metrics(self.start, self.start)
        self.assertEqual(row["avg_seconds"], 240)
        self.assertEqual(chart[0]["seconds"], 240)

    def test_one_second_is_not_lost_when_display_hours_round_to_zero(self):
        self.session("2026-10-12T10:00:00", "2026-10-12T10:00:01")
        row, chart, _ = self.metrics(self.start, self.start)
        self.assertEqual(row["total_seconds"], 1)
        self.assertEqual(chart[0]["seconds"], 1)
        self.assertTrue(chart[0]["hasWork"])

    def test_same_day_sessions_are_added_before_rounding(self):
        self.session("2026-10-12T10:00:00", "2026-10-12T10:04:00")
        self.session("2026-10-12T11:00:00", "2026-10-12T11:04:00")
        row, chart, _ = self.metrics(self.start, self.start)
        self.assertEqual(row["total_seconds"], 480)
        self.assertEqual(chart[0]["seconds"], 480)
        self.assertEqual(chart[0]["startTime"], "10:00 AM")

    def test_no_overlap_and_zero_work_days_stay_zero(self):
        self.session("2026-10-11T23:00:00", "2026-10-12T00:00:00")
        self.session("2026-10-15T00:00:00", "2026-10-15T01:00:00")
        row, chart, days = self.metrics()
        self.assertEqual(row["total_seconds"], 0)
        self.assertEqual([d["seconds"] for d in chart], [0, 0, 0])
        self.assertFalse(any(d["hasWork"] for d in chart))
        self.assertEqual(days, 3)
