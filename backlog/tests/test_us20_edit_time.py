from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from backlog.models import Sprint, Task, TaskHistory, TaskWorkSession


class US20EditTimeTests(TestCase):
    """US-20: Edit Time Entry."""

    def setUp(self):
        self.user = User.objects.create_user(username="member_one")
        self.other = User.objects.create_user(username="member_two")

        self.sprint = Sprint.objects.create(
            name="US20 Sprint",
            status="active",
        )
        self.sprint.team_members.add(self.user, self.other)

        self.task = Task.objects.create(
            title="US20 Task",
            sprint=self.sprint,
            assignee=self.user,
            status="in_progress",
        )

        self.client.force_login(self.user)

        self.record_url = reverse(
            "backlog:record_task_time",
            args=[self.task.pk],
        )

        self.client.post(
            self.record_url,
            self.payload("09:00", "10:00"),
        )

        self.session = TaskWorkSession.objects.get()

        self.edit_url = reverse(
            "backlog:edit_task_time",
            args=[self.task.pk, self.session.pk],
        )

    def payload(self, start="09:00", end="10:00", **overrides):
        data = {
            "start_date": "2026-10-01",
            "start_time": start,
            "end_date": "2026-10-01",
            "end_time": end,
        }

        return {
            **data,
            **overrides,
        }

    def test_owner_can_edit_start_and_end_before_task_completion(self):
        response = self.client.post(
            self.edit_url,
            self.payload("08:30", "10:30"),
        )

        self.assertEqual(response.status_code, 302)

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.duration,
            timedelta(hours=2),
        )

        self.assertEqual(
            self.session.started_at.astimezone().strftime("%H:%M"),
            "08:30",
        )

        self.assertEqual(
            self.session.ended_at.astimezone().strftime("%H:%M"),
            "10:30",
        )

    def test_edit_recalculates_duration_and_task_total(self):
        response = self.client.post(
            self.edit_url,
            self.payload("09:00", "11:30"),
        )

        self.assertEqual(response.status_code, 302)

        self.session.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(
            self.session.duration,
            timedelta(hours=2, minutes=30),
        )

        self.assertEqual(
            self.task.accumulated_hours,
            Decimal("2.50"),
        )

        self.assertEqual(
            TaskWorkSession.objects.count(),
            1,
        )

    def test_edit_prevents_overlap_with_another_entry(self):
        self.client.post(
            self.record_url,
            self.payload("10:00", "11:00"),
        )

        response = self.client.post(
            self.edit_url,
            self.payload("09:00", "10:30"),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertContains(
            response,
            "overlaps another",
            status_code=400,
        )

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.duration,
            timedelta(hours=1),
        )

    def test_successful_edit_creates_time_entry_history(self):
        response = self.client.post(
            self.edit_url,
            self.payload("09:00", "11:00"),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        history = TaskHistory.objects.get(
            task=self.task,
            changed_by=self.user,
            is_time_entry_change=True,
        )

        self.assertIn(
            "Edited work session",
            history.description,
        )

    def test_identical_edit_does_not_create_false_history(self):
        response = self.client.post(
            self.edit_url,
            self.payload(),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            TaskHistory.objects.filter(
                task=self.task,
                is_time_entry_change=True,
            ).exists()
        )

    def test_completed_task_time_entry_cannot_be_edited(self):
        self.task.status = "completed"
        self.task.save(update_fields=["status"])

        response = self.client.post(
            self.edit_url,
            self.payload("09:00", "12:00"),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.duration,
            timedelta(hours=1),
        )

    def test_non_active_sprint_time_entry_cannot_be_edited(self):
        self.sprint.status = "completed"
        self.sprint.save(update_fields=["status"])

        response = self.client.post(
            self.edit_url,
            self.payload("09:00", "12:00"),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.duration,
            timedelta(hours=1),
        )

    def test_other_member_cannot_edit_someone_elses_entry(self):
        self.task.assignee = self.other
        self.task.save(update_fields=["assignee"])

        self.client.force_login(self.other)

        response = self.client.post(
            self.edit_url,
            self.payload(),
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.user,
            self.user,
        )

    def test_edit_form_uses_native_calendar_and_clock_inputs(self):
        response = self.client.get(
            reverse(
                "backlog:task_detail",
                args=[self.task.pk],
            )
        )

        self.assertContains(
            response,
            'id="edit_start_date"',
        )

        self.assertContains(
            response,
            'id="edit_end_date"',
        )

        self.assertContains(
            response,
            'type="date"',
        )

        self.assertContains(
            response,
            'type="time"',
        )

    def test_edit_is_persisted_in_database(self):
        self.client.post(
            self.edit_url,
            self.payload("07:45", "09:15"),
        )

        persisted = TaskWorkSession.objects.get(
            pk=self.session.pk
        )

        self.assertEqual(
            persisted.duration,
            timedelta(minutes=90),
        )

        self.assertEqual(
            TaskWorkSession.objects.filter(
                task=self.task
            ).count(),
            1,
        )