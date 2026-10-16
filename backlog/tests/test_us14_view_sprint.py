from datetime import date, timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from backlog.models import Sprint, Task, Tag


class ViewSprintTests(TestCase):
    """
    Automated tests for User Story US-14: View Sprint.
    Tests all acceptance criteria for sprint details view, task list, metrics, and permissions.
    """

    def setUp(self):
        self.client = Client()

        # Admin user (not a direct sprint member)
        self.admin = User.objects.create_superuser(
            username="admin_viewer",
            email="admin_viewer@example.com",
            password="Password123!",
        )

        # Sprint roles
        self.po_user = User.objects.create_user(
            username="po_viewer",
            first_name="Alice",
            last_name="PO",
            email="alice@example.com",
        )
        self.sm_user = User.objects.create_user(
            username="sm_viewer",
            first_name="Bob",
            last_name="SM",
            email="bob@example.com",
        )
        self.member1 = User.objects.create_user(
            username="dev_viewer1",
            first_name="Charlie",
            last_name="Dev",
            email="charlie@example.com",
        )

        # Unauthorized user (not member and not admin)
        self.unauthorized_user = User.objects.create_user(
            username="unauthorized_viewer",
            email="unauth_viewer@example.com",
            password="Password123!",
            is_staff=False,
            is_superuser=False,
        )
        from accounts.models import AccountSecurity
        AccountSecurity.objects.filter(
            user__in=[self.admin, self.po_user, self.sm_user, self.member1, self.unauthorized_user]
        ).update(must_change_password=False)

        # Tags
        self.tag_backend = Tag.objects.create(name="Backend")
        self.tag_auth = Tag.objects.create(name="Auth")

        # Sprint setup
        self.today = date.today()
        self.end_date = self.today + timedelta(days=14)
        self.sprint = Sprint.objects.create(
            name="Sprint 2 - User Management",
            goal="Implement sprint viewing and task management.",
            status="active",
            start_date=self.today,
            end_date=self.end_date,
            product_owner=self.po_user,
            scrum_master=self.sm_user,
        )
        self.sprint.team_members.add(self.member1)

        # Sprint Tasks
        self.task1 = Task.objects.create(
            title="Create sprint dashboard",
            item_type="story",
            priority="urgent",
            story_points=5,
            accumulated_hours=6.5,
            status="in_progress",
            assignee=self.member1,
            sprint=self.sprint,
        )
        self.task1.tags.add(self.tag_backend, self.tag_auth)

        self.task2 = Task.objects.create(
            title="Fix sprint filter bug",
            item_type="bug",
            priority="medium",
            story_points=3,
            accumulated_hours=2.0,
            status="completed",
            assignee=self.po_user,
            sprint=self.sprint,
        )
        self.task2.tags.add(self.tag_backend)

        self.task3_deleted = Task.objects.create(
            title="Deleted old sprint task",
            item_type="story",
            priority="low",
            story_points=1,
            accumulated_hours=0.0,
            status="not_started",
            is_deleted=True,
            sprint=self.sprint,
        )

        self.url = reverse("backlog:sprint_detail", kwargs={"sprint_id": self.sprint.id})

    # AC: Anonymous user redirected to login
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    # AC: Unauthorized user denied access
    def test_unauthorized_user_denied_access(self):
        self.client.force_login(self.unauthorized_user)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("backlog:product_backlog"))
        self.assertContains(
            response,
            "Access denied: You do not have permission to view this sprint.",
        )

    # AC: Admin can view sprint information without being a sprint member
    def test_admin_can_view_sprint_without_being_a_member(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backlog/sprint_detail.html")
        self.assertEqual(response.context["sprint"], self.sprint)

    # AC: Sprint members (PO, SM, Team Member) can view sprint
    def test_sprint_members_can_view_sprint(self):
        for user in [self.po_user, self.sm_user, self.member1]:
            self.client.force_login(user)
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "backlog/sprint_detail.html")

    # AC: Sprint details are displayed (name, goal, start/end date, PO, SM)
    def test_sprint_details_are_displayed(self):
        self.client.force_login(self.member1)
        response = self.client.get(self.url)

        self.assertContains(response, "Sprint 2 - User Management")
        self.assertContains(response, "Implement sprint viewing and task management.")
        self.assertContains(response, "Alice PO")
        self.assertContains(response, "Bob SM")
        self.assertContains(response, f"{self.today.day} {self.today.strftime('%b %Y')}")

    # AC: Sprint status is displayed
    def test_sprint_status_is_displayed(self):
        self.client.force_login(self.member1)
        response = self.client.get(self.url)

        self.assertContains(response, "Active")
        self.assertEqual(response.context["sprint"].status, "active")

    # AC: Sprint team members are displayed
    def test_sprint_team_members_are_displayed(self):
        self.client.force_login(self.member1)
        response = self.client.get(self.url)

        self.assertIn(self.member1, response.context["team_members"])
        self.assertContains(response, "Charlie Dev")

    # AC: Sprint tasks are displayed with task name, type, tags, priority, story points, assignee, and accumulated hours
    def test_sprint_tasks_and_information_displayed(self):
        self.client.force_login(self.member1)
        response = self.client.get(self.url)

        tasks = list(response.context["tasks"])
        self.assertIn(self.task1, tasks)
        self.assertIn(self.task2, tasks)
        # Soft-deleted tasks must NOT be included
        self.assertNotIn(self.task3_deleted, tasks)

        # Check task fields in rendered HTML
        self.assertContains(response, "Create sprint dashboard")
        self.assertContains(response, "Fix sprint filter bug")
        self.assertContains(response, "Story")
        self.assertContains(response, "Bug")
        self.assertContains(response, "Backend")
        self.assertContains(response, "Auth")
        self.assertContains(response, "Urgent")
        self.assertContains(response, "Medium")
        self.assertContains(response, "5")  # Story points
        self.assertContains(response, "6.5")  # Accumulated hours
        self.assertContains(response, "2.0")  # Accumulated hours

    # AC: Metrics / Summary metrics are calculated correctly in context
    def test_sprint_task_metrics_calculated(self):
        self.client.force_login(self.member1)
        response = self.client.get(self.url)

        self.assertEqual(response.context["total_tasks"], 2)
        self.assertEqual(response.context["total_story_points"], 8)
        self.assertEqual(response.context["total_accumulated_hours"], 8.5)
        self.assertEqual(response.context["completed_tasks"], 1)
        self.assertEqual(response.context["in_progress_tasks"], 1)
        self.assertEqual(response.context["not_started_tasks"], 0)

    # AC: Available sprints shown in product backlog dropdown for authorized users
    def test_accessible_sprints_in_product_backlog(self):
        # Sprint member sees sprint in accessible_sprints dropdown
        self.client.force_login(self.member1)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertIn(self.sprint, response.context["accessible_sprints"])
        self.assertContains(response, self.sprint.name)

        # Admin sees all sprints in accessible_sprints
        self.client.force_login(self.admin)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertIn(self.sprint, response.context["accessible_sprints"])
        self.assertContains(response, self.sprint.name)

        # Unauthorized user does not see this sprint in accessible_sprints
        self.client.force_login(self.unauthorized_user)
        response = self.client.get(reverse("backlog:product_backlog"))
        self.assertNotIn(self.sprint, response.context["accessible_sprints"])
