from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from backlog.forms import TaskCreateForm, TaskEditForm
from backlog.models import Sprint, Tag, Task, TaskHistory, TaskWorkSession
from backlog.sprint_forms import WorkSessionForm


class US19RecordTimeTests(TestCase):
    """Acceptance coverage through the actual POST endpoints and rendered pages."""

    def setUp(self):
        self.user = User.objects.create_user(username="time_member")
        self.other = User.objects.create_user(username="other_member")
        self.sprint = Sprint.objects.create(name="Time tracking Sprint", status="active")
        self.sprint.team_members.add(self.user, self.other)
        self.task = Task.objects.create(title="US19 task", sprint=self.sprint, assignee=self.user)
        self.client.force_login(self.user)
        self.url = reverse("backlog:record_task_time", args=[self.task.pk])

    def payload(self, start="09:00", end="10:00", **overrides):
        data = {"start_date": "2026-09-30", "start_time": start,
                "end_date": "2026-09-30", "end_time": end}
        return {**data, **overrides}

    def record(self, start="09:00", end="10:00", **overrides):
        return self.client.post(self.url, self.payload(start, end, **overrides))

    def edit_url(self, session):
        return reverse("backlog:edit_task_time", args=[self.task.pk, session.pk])

    def test_record_calculates_duration_and_member_automatically(self):
        response = self.record("09:00", "10:30", user_id=self.other.pk, duration="999")
        self.assertRedirects(response, reverse("backlog:task_detail", args=[self.task.pk]))
        session = TaskWorkSession.objects.get()
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.task, self.task)
        self.assertEqual(session.duration, timedelta(minutes=90))
        self.assertEqual(timezone.localtime(session.started_at).strftime("%H:%M"), "09:00")
        self.assertTrue(timezone.is_aware(session.started_at))
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("1.50"))

    def test_multiple_sessions_accumulate_without_rounding_each_session(self):
        for hour in range(9, 14):
            self.assertEqual(self.record(f"{hour:02}:00", f"{hour:02}:01").status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(TaskWorkSession.objects.count(), 5)
        self.assertEqual(self.task.accumulated_hours, Decimal("0.08"))

    def test_overnight_and_multiple_day_sessions(self):
        self.assertEqual(self.record("23:30", "01:00", end_date="2026-10-02").status_code, 302)
        self.assertEqual(TaskWorkSession.objects.get().duration, timedelta(hours=25, minutes=30))

    def test_legacy_aggregate_hours_are_preserved(self):
        self.task.accumulated_hours = Decimal("4.50")
        self.task.save()
        self.record()
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("5.50"))

    def test_only_assigned_sprint_member_can_record(self):
        self.client.force_login(self.other)
        self.assertEqual(self.record().status_code, 403)
        self.assertFalse(TaskWorkSession.objects.exists())

    def test_assignee_must_also_be_a_sprint_member(self):
        self.sprint.team_members.remove(self.user)
        self.assertEqual(self.record().status_code, 403)
        self.assertFalse(TaskWorkSession.objects.exists())

    def test_admin_does_not_bypass_assignment(self):
        self.other.is_staff = self.other.is_superuser = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.record().status_code, 403)

    def test_login_required_for_create_and_edit(self):
        self.record()
        session = TaskWorkSession.objects.get()
        self.client.logout()
        self.assertEqual(self.record().status_code, 302)
        self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 302)
        self.assertEqual(TaskWorkSession.objects.count(), 1)

    def test_endpoints_require_post(self):
        self.record()
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.get(self.edit_url(TaskWorkSession.objects.get())).status_code, 405)

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        self.assertFalse(TaskWorkSession.objects.exists())

    def test_required_fields_and_malformed_dates_are_rejected(self):
        for field in self.payload():
            with self.subTest(field=field):
                data = self.payload()
                data.pop(field)
                self.assertEqual(self.client.post(self.url, data).status_code, 400)
        for overrides in ({"start_date": "2026-02-30"}, {"end_date": "invalid"},
                          {"start_time": "25:00"}, {"end_time": "invalid"}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.record(**overrides).status_code, 400)
        self.assertFalse(TaskWorkSession.objects.exists())

    def test_equal_or_reversed_timestamps_are_rejected(self):
        self.assertEqual(self.record("10:00", "10:00").status_code, 400)
        self.assertEqual(self.record("11:00", "10:00").status_code, 400)
        self.assertEqual(self.record(end_date="2026-09-29").status_code, 400)
        self.assertFalse(TaskWorkSession.objects.exists())

    def test_errors_preserve_values_and_reopen_record_modal(self):
        response = self.record("11:00", "10:00")
        self.assertContains(response, "End date and time must be after", status_code=400)
        self.assertContains(response, 'value="11:00"', status_code=400)
        self.assertContains(response, 'data-open-time-modal="recordTimeModal"', status_code=400)

    def test_same_user_overlap_in_all_directions_is_rejected(self):
        self.record("09:00", "10:00")
        for start, end in (("09:00", "10:00"), ("08:30", "09:30"), ("09:30", "10:30"),
                           ("09:15", "09:45"), ("08:00", "11:00")):
            with self.subTest(start=start, end=end):
                self.assertEqual(self.record(start, end).status_code, 400)
        self.assertEqual(TaskWorkSession.objects.count(), 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("1.00"))

    def test_adjacent_sessions_before_and_after_are_allowed(self):
        self.record("09:00", "10:00")
        self.assertEqual(self.record("08:00", "09:00").status_code, 302)
        self.assertEqual(self.record("10:00", "11:00").status_code, 302)

    def test_overlap_is_checked_across_tasks(self):
        self.record()
        other_task = Task.objects.create(title="Another task", sprint=self.sprint, assignee=self.user)
        response = self.client.post(reverse("backlog:record_task_time", args=[other_task.pk]),
                                    self.payload("09:30", "10:30"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(other_task.work_sessions.exists())

    def test_cross_midnight_overlap_is_rejected(self):
        self.record("23:00", "01:00", end_date="2026-10-01")
        self.assertEqual(self.record("00:30", "02:00", start_date="2026-10-01",
                                     end_date="2026-10-01").status_code, 400)

    def test_each_member_has_individual_history_and_combined_task_total(self):
        self.record()
        self.task.assignee = self.other
        self.task.save(update_fields=["assignee"])
        self.client.force_login(self.other)
        # Different users may work concurrently.
        self.assertEqual(self.record("09:00", "11:00").status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("3.00"))
        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
        self.assertEqual(list(response.context["time_entries"].values_list("user_id", flat=True)), [self.other.pk])
        self.assertContains(response, "Logged 2h 00m")
        self.assertNotContains(response, "Logged 1h 00m")
        self.assertFalse(TaskHistory.objects.filter(task=self.task).exists())

    def test_total_is_shown_in_all_board_columns_and_board_api(self):
        self.record("09:00", "10:30")
        for status in ("not_started", "in_progress", "completed"):
            with self.subTest(status=status):
                self.task.status = status
                self.task.save(update_fields=["status"])
                response = self.client.get(reverse("backlog:sprint_board_detail", args=[self.sprint.pk]))
                self.assertContains(response, "Total time: 1h 30m")
        response = self.client.get(reverse("backlog:sprint_board_data", args=[self.sprint.pk]))
        self.assertEqual(response.json()["tasks"][0]["accumulated_hours"], "1.50")

    def test_product_backlog_does_not_show_time_information(self):
        self.record("09:00", "10:30")
        response = self.client.get(reverse("backlog:product_backlog"))
        for text in ("Total time:", "Time Tracking", "1h 30m", "Logged 1h"):
            self.assertNotContains(response, text)
        self.task.sprint = None
        self.task.save(update_fields=["sprint"])
        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
        self.assertNotContains(response, "Time Tracking")
        self.assertNotContains(response, 'id="recordTimeModal"')

    def test_completed_task_rejects_new_and_edited_entries(self):
        self.record()
        session = TaskWorkSession.objects.get()
        self.task.status = "completed"
        self.task.save(update_fields=["status"])
        self.assertEqual(self.record("10:00", "11:00").status_code, 400)
        self.assertEqual(self.client.post(self.edit_url(session), self.payload("09:00", "11:00")).status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.duration, timedelta(hours=1))
        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
        self.assertNotContains(response, 'data-bs-target="#recordTimeModal"')
        self.assertNotContains(response, 'data-bs-target="#editTimeModal"')
        self.assertContains(response, "Logged 1h 00m")

    def test_non_active_sprints_reject_create_and_edit(self):
        self.record()
        session = TaskWorkSession.objects.get()
        for status in ("not_started", "planning", "completed"):
            with self.subTest(status=status):
                self.sprint.status = status
                self.sprint.save()
                self.assertEqual(self.record("10:00", "11:00").status_code, 400)
                self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 400)
        self.assertEqual(TaskWorkSession.objects.count(), 1)

    def test_backlog_deleted_and_missing_tasks_reject_entries(self):
        self.task.sprint = None
        self.task.save()
        self.assertEqual(self.record().status_code, 400)
        self.task.is_deleted = True
        self.task.save()
        self.assertEqual(self.record().status_code, 404)
        self.assertEqual(self.client.post(reverse("backlog:record_task_time", args=[999999]), self.payload()).status_code, 404)

    def test_edit_updates_existing_session_and_total_instead_of_adding(self):
        self.record()
        session = TaskWorkSession.objects.get()
        response = self.client.post(self.edit_url(session), self.payload("09:00", "11:30"))
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(TaskWorkSession.objects.count(), 1)
        self.assertEqual(session.duration, timedelta(minutes=150))
        self.assertEqual(self.task.accumulated_hours, Decimal("2.50"))
        # Saving the identical interval should not overlap itself.
        self.assertEqual(self.client.post(self.edit_url(session), self.payload("09:00", "11:30")).status_code, 302)

    def test_edit_cannot_overlap_another_session(self):
        self.record("09:00", "10:00")
        session = TaskWorkSession.objects.get()
        self.record("10:00", "11:00")
        response = self.client.post(self.edit_url(session), self.payload("09:00", "10:30"))
        self.assertContains(response, "overlaps another", status_code=400)
        self.assertContains(response, 'data-open-time-modal="editTimeModal"', status_code=400)
        session.refresh_from_db()
        self.assertEqual(session.duration, timedelta(hours=1))

    def test_other_members_cannot_edit_someone_elses_entry(self):
        self.record()
        session = TaskWorkSession.objects.get()
        self.task.assignee = self.other
        self.task.save(update_fields=["assignee"])
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.edit_url(session), self.payload()).status_code, 404)

    def test_session_cannot_be_edited_through_another_tasks_url(self):
        self.record()
        session = TaskWorkSession.objects.get()
        task = Task.objects.create(title="Other task", sprint=self.sprint, assignee=self.user)
        url = reverse("backlog:edit_task_time", args=[task.pk, session.pk])
        self.assertEqual(self.client.post(url, self.payload()).status_code, 404)

    def test_form_has_native_calendar_and_clock_inputs(self):
        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
        self.assertContains(response, 'type="date"', count=4)
        self.assertContains(response, 'type="time"', count=4)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, "Asia/Kuala_Lumpur")

    def test_ineligible_user_has_no_record_or_edit_buttons(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("backlog:task_detail", args=[self.task.pk]))
        self.assertNotContains(response, 'id="recordTimeModal"')
        self.assertNotContains(response, 'id="editTimeModal"')
        self.assertContains(response, "Only a Sprint member assigned")

    def test_total_cannot_be_set_through_backlog_forms(self):
        self.assertNotIn("accumulated_hours", TaskCreateForm().fields)
        self.assertNotIn("accumulated_hours", TaskEditForm(instance=self.task).fields)
        self.record()
        tag = Tag.objects.create(name="US19")
        response = self.client.post(reverse("backlog:edit_task", args=[self.task.pk]), {
            "title": self.task.title, "description": "Updated description", "item_type": "story",
            "story_points": 3, "tags": [tag.pk], "priority": "medium", "assignee": self.user.pk,
            "status": "not_started", "stage": "planning", "accumulated_hours": "9999",
        })
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("1.00"))

    def test_too_large_total_rolls_back_entire_submission(self):
        self.task.accumulated_hours = Decimal("9999.00")
        self.task.save()
        self.assertEqual(self.record("09:00", "11:00").status_code, 400)
        self.assertFalse(TaskWorkSession.objects.exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.accumulated_hours, Decimal("9999.00"))

    def test_database_rejects_non_positive_duration(self):
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskWorkSession.objects.create(task=self.task, user=self.user, started_at=now, ended_at=now)

    def test_dst_ambiguous_time_is_rejected(self):
        with timezone.override("America/New_York"):
            form = WorkSessionForm(self.payload("01:30", "03:30", start_date="2026-11-01", end_date="2026-11-01"))
            self.assertFalse(form.is_valid())
