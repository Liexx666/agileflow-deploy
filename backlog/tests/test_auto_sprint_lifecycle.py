from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountSecurity
from backlog.forms import SprintCreateForm, SprintEditForm
from backlog.models import Sprint, SprintHistory
from backlog.sprint_services import (
    auto_update_sprint_statuses,
    change_sprint_status,
    check_sprint_date_overlap,
)


class AutoSprintLifecycleTests(TestCase):
    """
    Test suite covering:
    1. Auto start sprint on start date
    2. Early manual sprint start before start date
    3. Overlapping sprint dates validation (create & edit)
    4. Once started, status cannot be changed back to not started or planning
    5. Manual cancellation changes end date to current date
    6. Manual completion changes end date to current date
    7. Auto end/complete sprint on end date
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="lifecycle_admin",
            password="TestPassword123!",
            is_staff=True,
            is_superuser=True,
        )
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    # -------------------------------------------------------------------------
    # 1. AUTO START SPRINT ON START DATE
    # -------------------------------------------------------------------------

    def test_sprint_auto_starts_when_start_date_arrives(self):
        """When current date reaches start_date, unstarted sprint automatically becomes active."""
        future_end = self.today + timedelta(days=7)
        sprint = Sprint.objects.create(
            name="Auto Start Sprint",
            start_date=self.today,
            end_date=future_end,
            status="not_started",
        )

        updated = auto_update_sprint_statuses(reference_date=self.today)
        sprint.refresh_from_db()

        self.assertIn(sprint, updated)
        self.assertEqual(sprint.status, "active")
        self.assertTrue(
            SprintHistory.objects.filter(
                sprint=sprint,
                description__icontains="automatically started",
            ).exists()
        )

    def test_future_sprint_does_not_auto_start_before_start_date(self):
        """A sprint with start_date in the future remains not_started."""
        tomorrow = self.today + timedelta(days=1)
        next_week = self.today + timedelta(days=8)
        sprint = Sprint.objects.create(
            name="Future Sprint",
            start_date=tomorrow,
            end_date=next_week,
            status="not_started",
        )

        auto_update_sprint_statuses(reference_date=self.today)
        sprint.refresh_from_db()

        self.assertEqual(sprint.status, "not_started")

    def test_auto_start_respects_single_active_sprint_rule(self):
        """If another sprint is already active, pending sprint waits until active finishes."""
        active_sprint = Sprint.objects.create(
            name="Current Active",
            start_date=self.today - timedelta(days=5),
            end_date=self.today + timedelta(days=2),
            status="active",
        )
        pending_sprint = Sprint.objects.create(
            name="Pending Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="not_started",
        )

        auto_update_sprint_statuses(reference_date=self.today)
        pending_sprint.refresh_from_db()
        active_sprint.refresh_from_db()

        # Active sprint remains active; pending sprint is not started to avoid active collision
        self.assertEqual(active_sprint.status, "active")
        self.assertEqual(pending_sprint.status, "not_started")

    # -------------------------------------------------------------------------
    # 2. EARLY MANUAL SPRINT START BEFORE START DATE
    # -------------------------------------------------------------------------

    def test_sprint_can_be_manually_started_early_before_start_date(self):
        """User can manually start a sprint early before its start date arrives."""
        future_start = self.today + timedelta(days=3)
        future_end = self.today + timedelta(days=10)
        sprint = Sprint.objects.create(
            name="Early Start Sprint",
            start_date=future_start,
            end_date=future_end,
            status="planning",
        )

        sprint, changed = change_sprint_status(sprint_id=sprint.pk, status="active")
        self.assertTrue(changed)
        self.assertEqual(sprint.status, "active")

    # -------------------------------------------------------------------------
    # 3. NON-OVERLAPPING SPRINT DATES VALIDATION
    # -------------------------------------------------------------------------

    def test_sprint_create_form_rejects_overlapping_dates(self):
        """SprintCreateForm rejects date ranges that overlap with existing sprints."""
        existing = Sprint.objects.create(
            name="Existing Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        # Overlap: inside existing range
        form = SprintCreateForm(
            data={
                "name": "Overlapping Sprint",
                "start_date": (self.today + timedelta(days=2)).isoformat(),
                "end_date": (self.today + timedelta(days=5)).isoformat(),
                "goal": "Test overlap",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)
        self.assertTrue(any("overlap" in err.lower() for err in form.errors["start_date"]))

    def test_sprint_create_form_allows_adjacent_non_overlapping_dates(self):
        """SprintCreateForm allows sprints that start right after an existing sprint ends."""
        Sprint.objects.create(
            name="Sprint 1",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        # Starts the day after Sprint 1 ends
        form = SprintCreateForm(
            data={
                "name": "Sprint 2 Adjacent",
                "start_date": (self.today + timedelta(days=8)).isoformat(),
                "end_date": (self.today + timedelta(days=15)).isoformat(),
                "goal": "Adjacent period",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_sprint_edit_form_rejects_overlapping_dates_with_other_sprint(self):
        """SprintEditForm rejects changing dates to overlap with another sprint."""
        sprint1 = Sprint.objects.create(
            name="Sprint 1",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )
        sprint2 = Sprint.objects.create(
            name="Sprint 2",
            start_date=self.today + timedelta(days=8),
            end_date=self.today + timedelta(days=15),
            status="not_started",
        )

        # Attempt to edit Sprint 2 to overlap with Sprint 1
        form = SprintEditForm(
            instance=sprint2,
            data={
                "name": "Sprint 2 Conflict",
                "start_date": (self.today + timedelta(days=5)).isoformat(),
                "end_date": (self.today + timedelta(days=12)).isoformat(),
                "status": "not_started",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("start_date", form.errors)
        self.assertTrue(any("overlap" in err.lower() for err in form.errors["start_date"]))

    def test_sprint_edit_form_allows_saving_without_date_change(self):
        """Editing an existing sprint without altering its dates does not trigger overlap error."""
        sprint = Sprint.objects.create(
            name="Self Check Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        form = SprintEditForm(
            instance=sprint,
            data={
                "name": "Renamed Self Check Sprint",
                "start_date": self.today.isoformat(),
                "end_date": (self.today + timedelta(days=7)).isoformat(),
                "status": "active",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_deleted_sprint_does_not_cause_overlap_error(self):
        """A soft-deleted sprint does not block new sprints on the same dates."""
        Sprint.objects.create(
            name="Deleted Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="not_started",
            is_deleted=True,
        )

        form = SprintCreateForm(
            data={
                "name": "New Sprint After Deleted",
                "start_date": self.today.isoformat(),
                "end_date": (self.today + timedelta(days=7)).isoformat(),
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    # -------------------------------------------------------------------------
    # 4. ONCE STARTED, STATUS CANNOT BE CHANGED TO NOT STARTED OR PLANNING
    # -------------------------------------------------------------------------

    def test_started_sprint_cannot_be_set_to_not_started_or_planning_via_service(self):
        """Service rejects transitioning an active or stopped sprint to not_started or planning."""
        active_sprint = Sprint.objects.create(
            name="Active Lock Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        for illegal_status in ["not_started", "planning"]:
            with self.assertRaises(ValidationError) as ctx:
                change_sprint_status(sprint_id=active_sprint.pk, status=illegal_status)
            self.assertIn("A started sprint cannot be changed back", str(ctx.exception))

    def test_sprint_edit_form_choices_exclude_not_started_and_planning_when_started(self):
        """SprintEditForm excludes 'not_started' and 'planning' choices once a sprint is started."""
        active_sprint = Sprint.objects.create(
            name="Active Choices Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        form = SprintEditForm(instance=active_sprint)
        choice_codes = [c[0] for c in form.fields["status"].choices]
        self.assertNotIn("not_started", choice_codes)
        self.assertNotIn("planning", choice_codes)
        self.assertIn("active", choice_codes)
        self.assertIn("stopped", choice_codes)  # Cancelled
        self.assertIn("completed", choice_codes)

    def test_sprint_edit_form_validation_rejects_setting_started_sprint_to_planning(self):
        """SprintEditForm clean validation rejects reverting an active sprint to planning."""
        active_sprint = Sprint.objects.create(
            name="Active Revert Sprint",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="active",
        )

        form = SprintEditForm(
            instance=active_sprint,
            data={
                "name": "Active Revert Sprint",
                "start_date": self.today.isoformat(),
                "end_date": (self.today + timedelta(days=7)).isoformat(),
                "status": "planning",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)
        self.assertIn("A started sprint cannot be changed back to not started or planning.", form.errors["status"])

    # -------------------------------------------------------------------------
    # 5. MANUAL CANCELLATION SETS END DATE TO CURRENT DATE
    # -------------------------------------------------------------------------

    def test_manual_cancellation_sets_end_date_to_current_date(self):
        """Setting a sprint to cancelled manually changes its end_date to current date."""
        original_end = self.today + timedelta(days=14)
        active_sprint = Sprint.objects.create(
            name="Cancel Sprint",
            start_date=self.today,
            end_date=original_end,
            status="active",
        )

        sprint, changed = change_sprint_status(sprint_id=active_sprint.pk, status="cancelled")
        sprint.refresh_from_db()

        self.assertEqual(sprint.status, "stopped")
        self.assertEqual(sprint.end_date, self.today)

    def test_manual_cancellation_via_edit_form_sets_end_date_to_current_date(self):
        """SprintEditForm sets end_date to current date when status is changed to Cancelled."""
        original_end = self.today + timedelta(days=14)
        active_sprint = Sprint.objects.create(
            name="Form Cancel Sprint",
            start_date=self.today,
            end_date=original_end,
            status="active",
        )

        form = SprintEditForm(
            instance=active_sprint,
            data={
                "name": "Form Cancel Sprint",
                "start_date": self.today.isoformat(),
                "end_date": original_end.isoformat(),
                "status": "cancelled",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.status, "stopped")
        self.assertEqual(saved.end_date, self.today)

    # -------------------------------------------------------------------------
    # 6. MANUAL COMPLETION SETS END DATE TO CURRENT DATE
    # -------------------------------------------------------------------------

    def test_manual_completion_sets_end_date_to_current_date(self):
        """Setting a sprint to completed manually changes its end_date to current date."""
        original_end = self.today + timedelta(days=10)
        active_sprint = Sprint.objects.create(
            name="Complete Sprint",
            start_date=self.today,
            end_date=original_end,
            status="active",
        )

        sprint, changed = change_sprint_status(sprint_id=active_sprint.pk, status="completed")
        sprint.refresh_from_db()

        self.assertEqual(sprint.status, "completed")
        self.assertEqual(sprint.end_date, self.today)

    # -------------------------------------------------------------------------
    # 7. AUTO END / COMPLETE SPRINT ON END DATE
    # -------------------------------------------------------------------------

    def test_sprint_auto_completes_when_end_date_arrives(self):
        """When current date reaches or passes end_date, active sprint automatically completes."""
        active_sprint = Sprint.objects.create(
            name="Auto Complete Sprint",
            start_date=self.today - timedelta(days=7),
            end_date=self.today,
            status="active",
        )

        updated = auto_update_sprint_statuses(reference_date=self.today)
        active_sprint.refresh_from_db()

        self.assertIn(active_sprint, updated)
        self.assertEqual(active_sprint.status, "completed")
        self.assertTrue(
            SprintHistory.objects.filter(
                sprint=active_sprint,
                description__icontains="automatically completed",
            ).exists()
        )

    def test_auto_complete_then_auto_start_next_sprint(self):
        """
        When active sprint's end_date arrives, it completes, allowing the next sprint
        whose start_date has arrived to automatically activate.
        """
        sprint_ending = Sprint.objects.create(
            name="Sprint 1 Ending Today",
            start_date=self.today - timedelta(days=7),
            end_date=self.today,
            status="active",
        )
        sprint_starting = Sprint.objects.create(
            name="Sprint 2 Starting Today",
            start_date=self.today,
            end_date=self.today + timedelta(days=7),
            status="not_started",
        )

        auto_update_sprint_statuses(reference_date=self.today)
        sprint_ending.refresh_from_db()
        sprint_starting.refresh_from_db()

        self.assertEqual(sprint_ending.status, "completed")
        self.assertEqual(sprint_starting.status, "active")
