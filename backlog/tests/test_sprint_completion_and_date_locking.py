"""
Tests for:
1. When a sprint reaches its end date (or is completed), incomplete tasks move back to Product Backlog,
   completed tasks stay in the sprint, and the sprint cannot be changed anymore.
2. Sprint start date and end date can be changed before the sprint starts; after start, dates cannot be changed.
"""
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountSecurity
from backlog.forms import SprintEditForm
from backlog.models import Sprint, Task, TaskHistory
from backlog.sprint_services import auto_update_sprint_statuses, change_sprint_status
from backlog.views import available_sprints


class SprintCompletionAndDateLockingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint_tester",
            first_name="Alice",
            last_name="Smith",
            password="TestPassword123!",
            is_staff=True,
            is_superuser=True,
        )
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    def test_auto_complete_moves_incomplete_tasks_to_product_backlog_and_retains_completed(self):
        """When end date arrives, sprint auto-completes, incomplete tasks return to PB, completed tasks stay."""
        sprint = Sprint.objects.create(
            name="Ending Sprint",
            start_date=self.today - timedelta(days=7),
            end_date=self.today,
            status="active",
            product_owner=self.user,
            scrum_master=self.user,
        )
        task_not_started = Task.objects.create(
            title="Task 1 Not Started",
            status="not_started",
            item_type="story",
            story_points=3,
            sprint=sprint,
        )
        task_in_progress = Task.objects.create(
            title="Task 2 In Progress",
            status="in_progress",
            item_type="story",
            story_points=5,
            sprint=sprint,
        )
        task_completed = Task.objects.create(
            title="Task 3 Completed",
            status="completed",
            item_type="story",
            story_points=2,
            sprint=sprint,
        )

        updated = auto_update_sprint_statuses(reference_date=self.today)
        sprint.refresh_from_db()
        task_not_started.refresh_from_db()
        task_in_progress.refresh_from_db()
        task_completed.refresh_from_db()

        self.assertIn(sprint, updated)
        self.assertEqual(sprint.status, "completed")

        # Incomplete tasks return to product backlog
        self.assertIsNone(task_not_started.sprint)
        self.assertIsNone(task_in_progress.sprint)

        # Completed tasks stay in the sprint
        self.assertEqual(task_completed.sprint, sprint)

        # History logged
        ns_hist = TaskHistory.objects.filter(task=task_not_started).latest("timestamp")
        self.assertIn("was completed", ns_hist.description)
        ip_hist = TaskHistory.objects.filter(task=task_in_progress).latest("timestamp")
        self.assertIn("was completed", ip_hist.description)

    def test_manual_complete_moves_incomplete_tasks_and_retains_completed(self):
        """When an active sprint is manually completed, incomplete tasks return to PB, completed tasks stay."""
        sprint = Sprint.objects.create(
            name="Manual Complete Sprint",
            start_date=self.today - timedelta(days=3),
            end_date=self.today + timedelta(days=4),
            status="active",
            product_owner=self.user,
            scrum_master=self.user,
        )
        task_incomplete = Task.objects.create(
            title="Incomplete Task",
            status="in_progress",
            item_type="story",
            story_points=3,
            sprint=sprint,
        )
        task_done = Task.objects.create(
            title="Finished Task",
            status="completed",
            item_type="story",
            story_points=2,
            sprint=sprint,
        )

        sprint, changed = change_sprint_status(
            sprint_id=sprint.pk,
            status="completed",
            changed_by=self.user,
        )
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "completed")

        task_incomplete.refresh_from_db()
        task_done.refresh_from_db()

        self.assertIsNone(task_incomplete.sprint)
        self.assertEqual(task_done.sprint, sprint)

    def test_completed_sprint_cannot_be_changed(self):
        """A completed sprint cannot be changed via service, edit form, or view."""
        completed_sprint = Sprint.objects.create(
            name="Locked Completed Sprint",
            start_date=self.today - timedelta(days=14),
            end_date=self.today - timedelta(days=7),
            status="completed",
            product_owner=self.user,
            scrum_master=self.user,
        )

        # Service rejects status change
        with self.assertRaises(ValidationError) as ctx:
            change_sprint_status(sprint_id=completed_sprint.pk, status="active")
        self.assertIn("A completed Sprint cannot be changed anymore", str(ctx.exception))

        # SprintEditForm clean() rejects modifying a completed sprint
        form = SprintEditForm(
            instance=completed_sprint,
            data={
                "name": "Try Renaming",
                "start_date": (self.today - timedelta(days=14)).isoformat(),
                "end_date": (self.today - timedelta(days=7)).isoformat(),
                "status": "completed",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(any("completed sprint cannot be changed" in str(err) for err in form.non_field_errors()))

        # edit_sprint view redirects with error
        response = self.client.get(reverse("backlog:edit_sprint", args=[completed_sprint.id]))
        self.assertEqual(response.status_code, 302)

    def test_dates_can_be_changed_before_sprint_starts(self):
        """Before the sprint starts (not_started/planning), start_date and end_date can be changed."""
        unstarted = Sprint.objects.create(
            name="Unstarted Sprint",
            start_date=self.today + timedelta(days=5),
            end_date=self.today + timedelta(days=12),
            status="not_started",
            product_owner=self.user,
            scrum_master=self.user,
        )

        new_start = self.today + timedelta(days=6)
        new_end = self.today + timedelta(days=15)
        form = SprintEditForm(
            instance=unstarted,
            data={
                "name": "Unstarted Sprint",
                "start_date": new_start.isoformat(),
                "end_date": new_end.isoformat(),
                "status": "not_started",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.start_date, new_start)
        self.assertEqual(saved.end_date, new_end)

    def test_dates_cannot_be_changed_after_sprint_starts(self):
        """After sprint starts (active), changing start_date or end_date is rejected."""
        active_sprint = Sprint.objects.create(
            name="Running Sprint",
            start_date=self.today - timedelta(days=2),
            end_date=self.today + timedelta(days=5),
            status="active",
            product_owner=self.user,
            scrum_master=self.user,
        )

        # Attempt to change start date on active sprint
        form_start = SprintEditForm(
            instance=active_sprint,
            data={
                "name": "Running Sprint",
                "start_date": (self.today - timedelta(days=4)).isoformat(),
                "end_date": (self.today + timedelta(days=5)).isoformat(),
                "status": "active",
            },
        )
        self.assertFalse(form_start.is_valid())
        self.assertIn("start_date", form_start.errors)
        self.assertTrue(any("only be changed before the sprint starts" in err for err in form_start.errors["start_date"]))

        # Attempt to change end date on active sprint
        form_end = SprintEditForm(
            instance=active_sprint,
            data={
                "name": "Running Sprint",
                "start_date": (self.today - timedelta(days=2)).isoformat(),
                "end_date": (self.today + timedelta(days=10)).isoformat(),
                "status": "active",
            },
        )
        self.assertFalse(form_end.is_valid())
        self.assertIn("end_date", form_end.errors)
        self.assertTrue(any("only be changed before the sprint starts" in err for err in form_end.errors["end_date"]))

    def test_available_sprints_auto_completes_sprints_reaching_end_date(self):
        """When views call available_sprints, sprints reaching end_date are auto-completed in real time."""
        sprint = Sprint.objects.create(
            name="View Check Sprint",
            start_date=self.today - timedelta(days=7),
            end_date=self.today,
            status="active",
        )
        incomplete_task = Task.objects.create(
            title="View Check Task",
            status="in_progress",
            item_type="story",
            story_points=2,
            sprint=sprint,
        )

        sprints = available_sprints(self.user)
        sprint.refresh_from_db()
        incomplete_task.refresh_from_db()

        self.assertEqual(sprint.status, "completed")
        self.assertIsNone(incomplete_task.sprint)

    def test_tasks_can_be_added_to_not_started_and_planning_sprints(self):
        """Tasks can be moved into not_started or planning sprints (not only active)."""
        not_started_sprint = Sprint.objects.create(
            name="Upcoming Sprint",
            start_date=self.today + timedelta(days=2),
            end_date=self.today + timedelta(days=9),
            status="not_started",
        )
        not_started_sprint.team_members.add(self.user)

        planning_sprint = Sprint.objects.create(
            name="Planning Sprint",
            start_date=self.today + timedelta(days=10),
            end_date=self.today + timedelta(days=17),
            status="planning",
        )
        planning_sprint.team_members.add(self.user)

        task1 = Task.objects.create(title="Task for Unstarted", status="not_started")
        task2 = Task.objects.create(title="Task for Planning", status="not_started")

        res1 = self.client.post(reverse("backlog:move_task", args=[task1.pk]), {"sprint_id": not_started_sprint.pk})
        self.assertEqual(res1.status_code, 200)
        task1.refresh_from_db()
        self.assertEqual(task1.sprint, not_started_sprint)

        res2 = self.client.post(reverse("backlog:move_task", args=[task2.pk]), {"sprint_id": planning_sprint.pk})
        self.assertEqual(res2.status_code, 200)
        task2.refresh_from_db()
        self.assertEqual(task2.sprint, planning_sprint)

    def test_tasks_cannot_be_added_to_completed_or_stopped_sprints(self):
        """Tasks cannot be added into completed or cancelled/stopped sprints."""
        completed_sprint = Sprint.objects.create(
            name="Old Done Sprint",
            start_date=self.today - timedelta(days=14),
            end_date=self.today - timedelta(days=7),
            status="completed",
        )
        completed_sprint.team_members.add(self.user)

        stopped_sprint = Sprint.objects.create(
            name="Halted Sprint",
            start_date=self.today - timedelta(days=6),
            end_date=self.today - timedelta(days=1),
            status="stopped",
        )
        stopped_sprint.team_members.add(self.user)

        task = Task.objects.create(title="Task Try Add", status="not_started")

        res_comp = self.client.post(reverse("backlog:move_task", args=[task.pk]), {"sprint_id": completed_sprint.pk})
        self.assertEqual(res_comp.status_code, 409)
        self.assertIn("Tasks cannot be moved into a Completed Sprint.", res_comp.json()["errors"]["sprint_id"][0])

        res_stop = self.client.post(reverse("backlog:move_task", args=[task.pk]), {"sprint_id": stopped_sprint.pk})
        self.assertEqual(res_stop.status_code, 409)
        self.assertIn("Tasks cannot be moved into a Cancelled Sprint.", res_stop.json()["errors"]["sprint_id"][0])

    def test_cancelled_sprint_moves_incomplete_tasks_and_retains_completed(self):
        """When cancelled, incomplete tasks return to product backlog while completed tasks stay."""
        sprint = Sprint.objects.create(
            name="Cancelling Sprint",
            start_date=self.today - timedelta(days=2),
            end_date=self.today + timedelta(days=5),
            status="active",
        )
        task_open = Task.objects.create(title="Incomplete", status="in_progress", sprint=sprint)
        task_done = Task.objects.create(title="Done", status="completed", sprint=sprint)

        sprint, changed = change_sprint_status(sprint_id=sprint.pk, status="stopped", changed_by=self.user)
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "stopped")

        task_open.refresh_from_db()
        task_done.refresh_from_db()
        self.assertIsNone(task_open.sprint)
        self.assertEqual(task_done.sprint, sprint)

    def test_sprint_auto_starts_when_start_date_arrived(self):
        """Sprint auto-starts when start date is reached, ensuring single active sprint."""
        unstarted = Sprint.objects.create(
            name="Ready to Start",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="not_started",
        )
        auto_update_sprint_statuses(reference_date=self.today)
        unstarted.refresh_from_db()
        self.assertEqual(unstarted.status, "active")

    def test_sprints_cannot_have_same_or_overlapping_dates(self):
        """Sprints cannot have the same dates or overlapping dates."""
        from backlog.forms import SprintCreateForm
        Sprint.objects.create(
            name="Existing Sprint Period",
            start_date=self.today + timedelta(days=20),
            end_date=self.today + timedelta(days=27),
            status="not_started",
        )
        # Attempt to create with identical dates
        form_same = SprintCreateForm(
            data={
                "name": "Duplicate Date Sprint",
                "start_date": (self.today + timedelta(days=20)).isoformat(),
                "end_date": (self.today + timedelta(days=27)).isoformat(),
            }
        )
        self.assertFalse(form_same.is_valid())
        self.assertIn("start_date", form_same.errors)

    def test_started_sprint_cannot_go_back_to_not_started(self):
        """Once started, a sprint cannot go back to not_started or planning, can only be cancelled."""
        started_sprint = Sprint.objects.create(
            name="Running Once Started",
            start_date=self.today - timedelta(days=1),
            end_date=self.today + timedelta(days=6),
            status="active",
        )
        with self.assertRaises(ValidationError) as ctx:
            change_sprint_status(sprint_id=started_sprint.pk, status="not_started")
        self.assertIn("A started sprint cannot be changed back", str(ctx.exception))

        # Can only be cancelled
        sprint, changed = change_sprint_status(sprint_id=started_sprint.pk, status="stopped", changed_by=self.user)
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "stopped")

