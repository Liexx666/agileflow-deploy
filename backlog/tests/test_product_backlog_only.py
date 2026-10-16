"""
Unit tests for the standalone Product Backlog view (US-03 / Sprint 1 parity).

Verifies that:
- The view requires authentication.
- Only tasks without a sprint (product backlog items) are displayed.
- Tasks assigned to sprints are not displayed.
- Sprints, sprint backlog columns, deleted sprints links, and create sprint buttons are removed.
- 'Create new task' button is present.
- 'Deleted Tasks' link is visible to admins and hidden from regular users.
- Tag filtering and priority sorting work.
- Metrics correctly count only pure product backlog items.
- The top navbar includes the 'Product Backlog' tab link.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountSecurity
from backlog.models import Sprint, Tag, Task


class ProductBacklogOnlyViewTests(TestCase):
    """Test suite for the standalone Product Backlog view."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_pb",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="member_pb",
            password="Password123!",
        )
        AccountSecurity.objects.filter(
            user__in=[self.admin, self.user]
        ).update(must_change_password=False)

        self.sprint = Sprint.objects.create(
            name="Sprint Active Test",
            goal="Test sprint isolation",
            status="active",
        )

        self.tag_ui = Tag.objects.create(name="UI")
        self.tag_backend = Tag.objects.create(name="Backend")

        # Unassigned product backlog tasks
        self.task_product_1 = Task.objects.create(
            title="Design Home Landing Page",
            item_type="story",
            priority="urgent",
            story_points=5,
            sprint=None,
        )
        self.task_product_1.tags.add(self.tag_ui)

        self.task_product_2 = Task.objects.create(
            title="Fix Database Connection Leak",
            item_type="bug",
            priority="low",
            story_points=3,
            sprint=None,
        )
        self.task_product_2.tags.add(self.tag_backend)

        # Task in a sprint (should NOT be visible in standalone product backlog)
        self.task_in_sprint = Task.objects.create(
            title="Implement Sprint Specific Feature",
            item_type="story",
            priority="important",
            story_points=8,
            sprint=self.sprint,
        )

        # Soft-deleted task (should NOT be visible)
        self.task_deleted = Task.objects.create(
            title="Old Soft Deleted Backlog Task",
            item_type="story",
            priority="medium",
            story_points=2,
            is_deleted=True,
            sprint=None,
        )

        self.url = reverse("backlog:product_backlog_only")

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated requests must be redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_displays_only_unassigned_product_tasks(self):
        """Standalone view shows only unassigned product tasks, not sprint tasks."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Product tasks should be present
        self.assertContains(response, self.task_product_1.title)
        self.assertContains(response, self.task_product_2.title)

        # Sprint task and deleted task must NOT be in the response
        self.assertNotContains(response, self.task_in_sprint.title)
        self.assertNotContains(response, self.task_deleted.title)

    def test_no_sprint_related_elements(self):
        """Sprint backlog column, Deleted Sprints, and Create sprint must NOT be present."""
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # No sprint names or sprint actions
        self.assertNotContains(response, self.sprint.name)
        self.assertNotContains(response, "Deleted Sprints")
        self.assertNotContains(response, "Create new sprint")
        self.assertNotContains(response, reverse("backlog:deleted_sprints"))
        self.assertNotContains(response, reverse("backlog:create_sprint"))

    def test_create_task_button_is_present(self):
        """The 'Create new task' action button must be present."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create new task")
        self.assertContains(response, reverse("backlog:create_task"))

    def test_deleted_tasks_link_admin_only(self):
        """Deleted Tasks link should appear for admin but not regular users."""
        # Admin should see Deleted Tasks link
        self.client.force_login(self.admin)
        admin_response = self.client.get(self.url)
        self.assertContains(admin_response, "Deleted Tasks")
        self.assertContains(admin_response, reverse("backlog:deleted_tasks"))

        # Regular user should NOT see Deleted Tasks link
        self.client.force_login(self.user)
        user_response = self.client.get(self.url)
        self.assertNotContains(user_response, reverse("backlog:deleted_tasks"))

    def test_tag_filtering(self):
        """Tag filtering limits results to matching product tasks."""
        self.client.force_login(self.user)
        response = self.client.get(f"{self.url}?tag=UI")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.task_product_1.title)
        self.assertNotContains(response, self.task_product_2.title)

    def test_priority_sorting(self):
        """Tasks are sorted by priority when requested."""
        self.client.force_login(self.user)
        # Lowest to urgent sort
        response = self.client.get(f"{self.url}?sort=priority_asc")
        self.assertEqual(response.status_code, 200)
        tasks = list(response.context["tasks"])
        self.assertEqual(tasks[0], self.task_product_2)
        self.assertEqual(tasks[1], self.task_product_1)

    def test_metrics_reflect_only_product_backlog_items(self):
        """Metrics should count only unassigned, non-deleted product items."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_items"], 2)
        self.assertEqual(response.context["total_points"], 8)
        self.assertEqual(response.context["story_count"], 1)
        self.assertEqual(response.context["bug_count"], 1)

    def test_tab_strip_includes_product_backlog_tab(self):
        """The tab bar has Sprint Board first, Product Backlog second, and Kanban Board tab removed."""
        self.client.force_login(self.user)
        def get_tab_strip(html):
            start = html.find('class="d-flex border-bottom mb-4')
            self.assertNotEqual(start, -1, "Tab strip container not found in view")
            end = html.find('</div>', start)
            return html[start:end]

        # Check kanban board view tab strip
        response_board = self.client.get(reverse("backlog:sprint_board"))
        tab_board = get_tab_strip(response_board.content.decode())
        self.assertIn("Sprint Board", tab_board)
        self.assertIn("Product Backlog", tab_board)
        self.assertNotIn("Kanban Board", tab_board)
        self.assertTrue(tab_board.index("Sprint Board") < tab_board.index("Product Backlog"))
        self.assertContains(response_board, "Back to Sprint Board")

        # Check sprint board tab bar - Kanban Board is not in tab bar
        response_backlog = self.client.get(reverse("backlog:product_backlog"))
        tab_backlog = get_tab_strip(response_backlog.content.decode())
        self.assertIn("Sprint Board", tab_backlog)
        self.assertIn("Product Backlog", tab_backlog)
        self.assertNotIn("Kanban Board", tab_backlog)
        self.assertTrue(tab_backlog.index("Sprint Board") < tab_backlog.index("Product Backlog"))

        # Check product backlog standalone view itself
        response_pb = self.client.get(self.url)
        tab_pb = get_tab_strip(response_pb.content.decode())
        self.assertIn("Sprint Board", tab_pb)
        self.assertIn("Product Backlog", tab_pb)
        self.assertNotIn("Kanban Board", tab_pb)
        self.assertTrue(tab_pb.index("Sprint Board") < tab_pb.index("Product Backlog"))
        # Non-admin user does not see Dashboard in tab bar
        self.assertNotIn("Dashboard", tab_board)
        self.assertNotIn("Dashboard", tab_backlog)
        self.assertNotIn("Dashboard", tab_pb)

    def test_admin_dashboard_tab_visibility_and_access(self):
        """Dashboard tab is visible across views for admins only, and restricted for regular members."""
        def get_tab_strip(html):
            start = html.find('class="d-flex border-bottom mb-4')
            self.assertNotEqual(start, -1, "Tab strip container not found in view")
            end = html.find('</div>', start)
            return html[start:end]

        # 1. Admin user has Dashboard tab across Product Backlog, Sprint Board, and Kanban Board
        self.client.force_login(self.admin)
        admin_dash_url = reverse("accounts:admin_dashboard")

        # Product Backlog view
        resp_pb = self.client.get(self.url)
        tab_pb = get_tab_strip(resp_pb.content.decode())
        self.assertIn("Dashboard", tab_pb)
        self.assertIn(admin_dash_url, tab_pb)

        # Sprint Board view
        resp_sb = self.client.get(reverse("backlog:product_backlog"))
        tab_sb = get_tab_strip(resp_sb.content.decode())
        self.assertIn("Dashboard", tab_sb)
        self.assertIn(admin_dash_url, tab_sb)

        # Kanban Board view
        resp_kb = self.client.get(reverse("backlog:sprint_board"))
        tab_kb = get_tab_strip(resp_kb.content.decode())
        self.assertIn("Dashboard", tab_kb)
        self.assertIn(admin_dash_url, tab_kb)

        # Admin dashboard view itself includes tab strip
        resp_dash = self.client.get(admin_dash_url)
        self.assertEqual(resp_dash.status_code, 200)
        tab_dash = get_tab_strip(resp_dash.content.decode())
        self.assertIn("Sprint Board", tab_dash)
        self.assertIn("Product Backlog", tab_dash)
        self.assertIn("Dashboard", tab_dash)

        # 2. Non-admin member never sees Dashboard tab and cannot access admin dashboard
        self.client.force_login(self.user)
        resp_pb_member = self.client.get(self.url)
        tab_pb_member = get_tab_strip(resp_pb_member.content.decode())
        self.assertNotIn("Dashboard", tab_pb_member)
        self.assertNotIn(admin_dash_url, tab_pb_member)

        resp_sb_member = self.client.get(reverse("backlog:product_backlog"))
        tab_sb_member = get_tab_strip(resp_sb_member.content.decode())
        self.assertNotIn("Dashboard", tab_sb_member)
        self.assertNotIn(admin_dash_url, tab_sb_member)

        # Direct access to admin dashboard is denied for non-admin
        resp_dash_member = self.client.get(admin_dash_url, follow=True)
        self.assertRedirects(resp_dash_member, reverse("backlog:product_backlog"))
        self.assertContains(resp_dash_member, "Access denied")

    def test_default_landing_view_is_sprint_board(self):
        """Authenticated users visiting the home URL or logging in land on the Sprint Board."""
        self.client.force_login(self.user)
        response_home = self.client.get(reverse("backlog:home"))
        self.assertRedirects(response_home, reverse("backlog:product_backlog"))
