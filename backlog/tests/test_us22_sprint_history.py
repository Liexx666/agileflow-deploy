from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from backlog.models import Sprint, SprintHistory


class US22SprintHistoryTests(TestCase):
    """ US-22: View Sprint History."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="history_admin",
            password="Password123",
            is_staff=True,
            is_superuser=True,
        )

        self.member = User.objects.create_user(
            username="history_member"
        )

        self.second_member = User.objects.create_user(
            username="second_member"
        )

        self.client.force_login(
            self.admin
        )

        today = timezone.localdate()

        self.start_date = today
        self.end_date = today + timedelta(days=7)

    def create_sprint_through_view(self):
        response = self.client.post(
            reverse("backlog:create_sprint"),
            {
                "name": "History Sprint",
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "goal": "Initial goal",
                "team_members": [
                    self.member.pk,
                    self.second_member.pk,
                ],
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        return Sprint.objects.get(
            name="History Sprint"
        )

    def test_sprint_creation_is_logged_with_author_and_initial_status(self):
        sprint = self.create_sprint_through_view()

        entry = SprintHistory.objects.get(
            sprint=sprint
        )

        self.assertEqual(
            entry.changed_by,
            self.admin,
        )

        self.assertIn(
            "created sprint 'History Sprint'",
            entry.description,
        )

        self.assertIn(
            "Not Started",
            entry.description,
        )

    def test_sprint_details_page_contains_dedicated_history_section(self):
        sprint = self.create_sprint_through_view()

        response = self.client.get(
            reverse(
                "backlog:sprint_detail",
                args=[sprint.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'id="sprint-history-heading"',
        )

        self.assertContains(
            response,
            "History",
        )

        self.assertContains(
            response,
            "Author: history_admin",
        )

    def test_history_displays_timestamp_description_and_author(self):
        sprint = self.create_sprint_through_view()

        response = self.client.get(
            reverse(
                "backlog:sprint_detail",
                args=[sprint.pk],
            )
        )

        self.assertContains(
            response,
            "history_admin created sprint",
        )

        self.assertContains(
            response,
            "History Sprint",
        )

        self.assertContains(
            response,
            "Not Started",
        )

        self.assertContains(
            response,
            "history-timestamp",
        )

        self.assertContains(
            response,
            "history-description",
        )

        self.assertContains(
            response,
            "history-author",
        )

    def test_assigning_product_owner_and_scrum_master_is_logged(self):
        sprint = self.create_sprint_through_view()

        self.client.post(
            reverse(
                "backlog:assign_sprint_role",
                args=[
                    sprint.pk,
                    "product_owner",
                ],
            ),
            {
                "user_id": self.member.pk,
            },
        )

        self.client.post(
            reverse(
                "backlog:assign_sprint_role",
                args=[
                    sprint.pk,
                    "scrum_master",
                ],
            ),
            {
                "user_id": self.second_member.pk,
            },
        )

        descriptions = list(
            SprintHistory.objects.filter(
                sprint=sprint
            ).values_list(
                "description",
                flat=True,
            )
        )

        self.assertTrue(
            any(
                "as Product Owner" in text
                for text in descriptions
            )
        )

        self.assertTrue(
            any(
                "as Scrum Master" in text
                for text in descriptions
            )
        )

    def test_editing_name_goal_dates_team_members_and_status_is_logged(self):
        sprint = self.create_sprint_through_view()

        response = self.client.post(
            reverse(
                "backlog:edit_sprint",
                args=[sprint.pk],
            ),
            {
                "name": "Renamed Sprint",
                "start_date": (
                    self.start_date
                    + timedelta(days=1)
                ).isoformat(),
                "end_date": (
                    self.end_date
                    + timedelta(days=1)
                ).isoformat(),
                "goal": "Updated goal",
                "status": "planning",
                "team_members": [
                    self.member.pk
                ],
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        descriptions = "\n".join(
            SprintHistory.objects.filter(
                sprint=sprint
            ).values_list(
                "description",
                flat=True,
            )
        )

        for expected in (
            "edited sprint name",
            "edited start date",
            "edited end date",
            "edited team members",
            "edited goal",
            "edited status",
        ):
            with self.subTest(
                expected=expected
            ):
                self.assertIn(
                    expected,
                    descriptions,
                )

    def test_history_is_most_recent_first(self):
        sprint = self.create_sprint_through_view()

        older = SprintHistory.objects.create(
            sprint=sprint,
            changed_by=self.admin,
            description="Older action",
        )

        newer = SprintHistory.objects.create(
            sprint=sprint,
            changed_by=self.admin,
            description="Newer action",
        )

        history = list(
            SprintHistory.objects.filter(
                sprint=sprint
            )
        )

        self.assertLess(
            history.index(newer),
            history.index(older),
        )

        response = self.client.get(
            reverse(
                "backlog:sprint_detail",
                args=[sprint.pk],
            )
        )

        content = response.content.decode()

        self.assertLess(
            content.index("Newer action"),
            content.index("Older action"),
        )

    def test_history_is_read_only_in_sprint_details_ui(self):
        sprint = self.create_sprint_through_view()

        response = self.client.get(
            reverse(
                "backlog:sprint_detail",
                args=[sprint.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Edit history",
        )

        self.assertNotContains(
            response,
            "Delete history",
        )

        self.assertNotContains(
            response,
            "history-edit",
        )

        self.assertNotContains(
            response,
            "history-delete",
        )