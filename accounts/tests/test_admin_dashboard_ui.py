from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from backlog.models import Task, TaskWorkSession
from django.utils import timezone
from datetime import timedelta


class AdminDashboardUITests(TestCase):
    """
    Automated unit tests for Admin Dashboard UI functionality and profile menu link removal.
    """

    def setUp(self):
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="Superuser",
        )
        self.member_user = self.User.objects.create_user(
            username="member_user",
            email="member@example.com",
            password="MemberPassword123!",
            first_name="Member",
            last_name="Regular",
            is_staff=False,
            is_superuser=False,
        )
        self.dashboard_url = reverse("accounts:admin_dashboard")
        self.backlog_url = reverse("backlog:product_backlog")

    def test_admin_dashboard_profile_dropdown_button_removed(self):
        """
        Verify that the Admin Dashboard button is removed from the profile dropdown menu,
        while Manage Accounts, Reset Password, and Log out remain present for admin.
        """
        self.client.force_login(self.admin_user)
        response = self.client.get(self.backlog_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        # Find the profile dropdown menu
        dropdown_start = content.find('id="profileDropdownMenu"')
        self.assertNotEqual(dropdown_start, -1, "Profile dropdown menu not found")
        dropdown_end = content.find('</ul>', dropdown_start)
        profile_dropdown_html = content[dropdown_start:dropdown_end]

        # The profile dropdown must NOT contain the Admin Dashboard button
        self.assertNotIn("Admin Dashboard", profile_dropdown_html)

        # Other profile items must still be present
        self.assertIn("Manage Accounts", profile_dropdown_html)
        self.assertIn("Reset Password", profile_dropdown_html)
        self.assertIn("Log out", profile_dropdown_html)

    def test_admin_dashboard_access_allowed_for_admin(self):
        """Admin can access the Admin Dashboard UI."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/admin_dashboard.html")

        # Top tab bar includes Sprint Board, Product Backlog, Dashboard
        self.assertContains(response, "Sprint Board")
        self.assertContains(response, "Product Backlog")
        self.assertContains(response, "Dashboard")

    def test_admin_dashboard_access_denied_for_regular_user(self):
        """Non-admin user cannot access Admin Dashboard UI and is redirected."""
        self.client.force_login(self.member_user)
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, self.backlog_url)

    def test_admin_dashboard_context_data(self):
        """Admin Dashboard view provides rich context including all_users, backlog_tasks, and chart_data."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        self.assertIn("members", response.context)
        self.assertIn("all_users", response.context)
        self.assertIn("backlog_tasks", response.context)
        self.assertIn("current_team", response.context)
        self.assertIn("current_view", response.context)
        self.assertIn("chart_data_json", response.context)

        # all_users contains both users
        usernames = [u["username"] for u in response.context["all_users"]]
        self.assertIn("admin_user", usernames)
        self.assertIn("member_user", usernames)

    def test_admin_dashboard_timeline_filtering(self):
        """Filtering with start_date and end_date updates total_days and calculates averages."""
        self.client.force_login(self.admin_user)
        today = timezone.localdate()
        start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")

        response = self.client.get(f"{self.dashboard_url}?start_date={start}&end_date={end}&view=analytics&team=Team%201")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["start_date"], start)
        self.assertEqual(response.context["end_date"], end)
        self.assertEqual(response.context["total_days"], 7)
        self.assertEqual(response.context["current_view"], "analytics")
        self.assertEqual(response.context["current_team"], "Team 1")

    def test_admin_dashboard_sort_order(self):
        """Sort query parameter 'asc' and 'desc' adjusts sort order."""
        self.client.force_login(self.admin_user)

        resp_asc = self.client.get(f"{self.dashboard_url}?sort=asc")
        self.assertEqual(resp_asc.status_code, 200)
        self.assertEqual(resp_asc.context["current_sort"], "asc")

        resp_desc = self.client.get(f"{self.dashboard_url}?sort=desc")
        self.assertEqual(resp_desc.status_code, 200)
        self.assertEqual(resp_desc.context["current_sort"], "desc")

    def test_admin_dashboard_template_interactive_components(self):
        """Verify presence of key interactive features in template."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        content = response.content.decode()

        # Sidebar and Panels
        self.assertIn('id="teamsListContainer"', content)
        self.assertIn('id="sidebarActionBtn"', content)
        self.assertIn('id="viewTeamMembers"', content)
        self.assertIn('id="viewAdminDashboard"', content)
        self.assertIn('id="viewUserSummary"', content)

        # Modals
        self.assertIn('id="modalCreateTeam"', content)
        self.assertIn('id="modalAddTeamMember"', content)
        self.assertIn('id="modalAssignTask"', content)
        self.assertIn('id="modalConfirmRemoveMember"', content)

        # Declarative modal triggers
        self.assertIn('id="btnAddMemberTrigger" data-bs-toggle="modal" data-bs-target="#modalAddTeamMember"', content)
        self.assertIn('id="sidebarActionBtn" data-bs-toggle="modal" data-bs-target="#modalCreateTeam"', content)

        # Lifecycle and modal helpers
        self.assertIn('initAdminDashboard', content)
        self.assertIn('showModalById', content)
        self.assertIn('hideModalById', content)

        # Timeline and Quick Presets
        self.assertIn('timeline-quick-btn', content)
        self.assertIn('summary-quick-btn', content)
        self.assertIn('id="summaryBarChartVisual"', content)
        self.assertIn('id="summaryMemberTasksList"', content)

        # Summary Period Banner and Daily Breakdown Table
        self.assertIn('id="summaryPeriodBanner"', content)
        self.assertIn('id="summaryPeriodDatesText"', content)
        self.assertIn('id="summaryPeriodAvgText"', content)
        self.assertIn('id="summaryPeriodTotalText"', content)
        self.assertIn('id="summaryDailyBreakdownTable"', content)
        self.assertIn('id="summaryBreakdownTableBody"', content)
        self.assertIn('id="summaryBreakdownTableFoot"', content)
        self.assertIn('dash-pillar-fill zero-hours', content)

        # Fixed Y-Axis and Internal Scrollable Box (Page does not extend)
        self.assertIn('id="summaryChartViewport"', content)
        self.assertIn('id="summaryChartYAxis"', content)
        self.assertIn('id="summaryChartScrollBox"', content)
        self.assertIn('id="summaryYAxisTicks"', content)
        self.assertIn('id="summaryChartGridlines"', content)
        self.assertIn('summary-table-scrollbox', content)

    def test_admin_dashboard_chart_data_shows_entirety_of_period_including_zero_work_days(self):
        """
        Verify that chart_data_map contains every single date in the timeline period [Oct 7 to Oct 11],
        even if no work was logged on some or all of those dates.
        """
        import json
        self.client.force_login(self.admin_user)
        start = "2026-10-07"
        end = "2026-10-11"

        response = self.client.get(f"{self.dashboard_url}?start_date={start}&end_date={end}&view=analytics")
        self.assertEqual(response.status_code, 200)

        chart_data_json = response.context.get("chart_data_json")
        self.assertIsNotNone(chart_data_json)
        chart_data = json.loads(chart_data_json)

        # Ensure user key exists in chart_data
        self.assertIn("member_user", chart_data)
        member_days = chart_data["member_user"]

        # Exactly 5 days from Oct 7 to Oct 11 inclusive
        expected_iso_dates = [
            "2026-10-07",
            "2026-10-08",
            "2026-10-09",
            "2026-10-10",
            "2026-10-11",
        ]
        actual_iso_dates = [d["isoDate"] for d in member_days]
        self.assertEqual(actual_iso_dates, expected_iso_dates)

        # Each day has required structure
        for d in member_days:
            self.assertIn("date", d)
            self.assertIn("isoDate", d)
            self.assertIn("hours", d)
            self.assertIn("startTime", d)
            self.assertIn("hasWork", d)
            self.assertIn("heightPct", d)

    def test_admin_reassign_backlog_task_success(self):
        """Admin can reassign a backlog task to any non-admin member."""
        import json
        from backlog.models import TaskHistory
        self.client.force_login(self.admin_user)
        task = Task.objects.create(title="Backlog Task Alpha", sprint=None)
        reassign_url = reverse("accounts:admin_reassign_task")

        response = self.client.post(
            reassign_url,
            data=json.dumps({
                "task_id": task.id,
                "assignee_id": self.member_user.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        task.refresh_from_db()
        self.assertEqual(task.assignee, self.member_user)
        self.assertTrue(TaskHistory.objects.filter(task=task).exists())

    def test_admin_reassign_backlog_task_to_admin_forbidden(self):
        """Backlog tasks cannot be reassigned to an admin."""
        import json
        self.client.force_login(self.admin_user)
        task = Task.objects.create(title="Backlog Task Beta", sprint=None)
        reassign_url = reverse("accounts:admin_reassign_task")

        response = self.client.post(
            reassign_url,
            data=json.dumps({
                "task_id": task.id,
                "assignee_id": self.admin_user.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("administrator", data["error"].lower())

    def test_admin_reassign_sprint_task_to_sprint_member_success(self):
        """Sprint tasks can be reassigned to other non-admin members of the sprint."""
        import json
        from backlog.models import Sprint
        self.client.force_login(self.admin_user)
        member2 = self.User.objects.create_user(
            username="member_two",
            email="member2@example.com",
            password="MemberPassword123!",
        )
        sprint = Sprint.objects.create(name="Sprint Test", status="not_started")
        sprint.team_members.add(self.member_user, member2)

        task = Task.objects.create(
            title="Sprint Task Gamma",
            sprint=sprint,
            assignee=self.member_user,
        )
        reassign_url = reverse("accounts:admin_reassign_task")

        response = self.client.post(
            reassign_url,
            data=json.dumps({
                "task_id": task.id,
                "assignee_id": member2.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        task.refresh_from_db()
        self.assertEqual(task.assignee, member2)

    def test_admin_reassign_sprint_task_to_non_sprint_member_forbidden(self):
        """Sprint tasks cannot be reassigned to users outside the sprint."""
        import json
        from backlog.models import Sprint
        self.client.force_login(self.admin_user)
        non_sprint_user = self.User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="MemberPassword123!",
        )
        sprint = Sprint.objects.create(name="Sprint Restricted", status="not_started")
        sprint.team_members.add(self.member_user)

        task = Task.objects.create(
            title="Sprint Task Delta",
            sprint=sprint,
            assignee=self.member_user,
        )
        reassign_url = reverse("accounts:admin_reassign_task")

        response = self.client.post(
            reassign_url,
            data=json.dumps({
                "task_id": task.id,
                "assignee_id": non_sprint_user.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("member of this sprint", data["error"])

    def test_non_admin_cannot_access_reassign_task(self):
        """Non-admin user cannot access the admin task reassignment endpoint."""
        import json
        self.client.force_login(self.member_user)
        task = Task.objects.create(title="Backlog Task Epsilon")
        reassign_url = reverse("accounts:admin_reassign_task")

        response = self.client.post(
            reassign_url,
            data=json.dumps({
                "task_id": task.id,
                "assignee_id": self.member_user.id,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_no_task_assignment_controls_in_add_member_or_roster(self):
        """Adding team members cannot assign tasks, dashboard cannot assign tasks, and calendar visibility styles are present."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        content = response.content.decode()

        # Add member modal must NOT contain initial task assignment
        self.assertNotIn('id="selectPresetTask"', content)
        self.assertNotIn('Assign Initial Task', content)

        # Dashboard user summary must NOT contain Assign Task button
        self.assertNotIn('id="btnSummaryAssignTask"', content)

        # modalAssignTask must be disabled/hidden with d-none
        self.assertIn('id="modalAssignTask"', content)
        self.assertIn('class="modal fade d-none"', content)

        # Database task helper must be defined in script
        self.assertIn('getMemberDatabaseTasks', content)

        # Calendar and clock period input visibility styles must be present
        self.assertIn('dash-timeline-input', content)
        self.assertIn('color-scheme: dark !important;', content)
        self.assertIn('color-scheme: light !important;', content)
        self.assertIn('webkit-calendar-picker-indicator', content)

    def test_admin_dashboard_tasks_assigned_from_database(self):
        """Tasks assigned are determined dynamically from database backlog tasks."""
        self.client.force_login(self.admin_user)
        task = Task.objects.create(
            title="Database Driven Task",
            assignee=self.member_user,
            status="in_progress",
        )
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Context contains backlog_tasks from database
        self.assertIn("backlog_tasks", response.context)
        tasks_in_context = response.context["backlog_tasks"]
        db_task_entry = next((t for t in tasks_in_context if t["id"] == task.id), None)
        self.assertIsNotNone(db_task_entry)
        self.assertEqual(db_task_entry["title"], "Database Driven Task")
        self.assertEqual(db_task_entry["assignee_id"], self.member_user.id)
        self.assertEqual(db_task_entry["assignee_username"], self.member_user.username)

    def test_admin_dashboard_stats_api_access_control(self):
        """Stats API endpoint allows staff/superuser and denies regular users."""
        stats_api_url = reverse("accounts:admin_dashboard_stats_api")
        self.client.force_login(self.member_user)
        response = self.client.get(stats_api_url)
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin_user)
        response = self.client.get(stats_api_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("members", data)
        self.assertIn("chart_data", data)
        self.assertIn("start_date", data)
        self.assertIn("end_date", data)
        self.assertIn("total_days", data)

    def test_logged_time_stored_in_database_reflects_concurrently_on_stats_and_chart(self):
        """
        Verify that time logging is stored in TaskWorkSession in the database and
        retrieved concurrently by the API and dashboard, updating average time and bar chart.
        """
        from datetime import datetime
        stats_api_url = reverse("accounts:admin_dashboard_stats_api")
        today = timezone.localdate()
        today_iso = today.strftime("%Y-%m-%d")

        task = Task.objects.create(title="Task Alpha", assignee=self.member_user)

        self.client.force_login(self.admin_user)
        # 1. Before logging any time, total_seconds for member is 0
        resp_before = self.client.get(f"{stats_api_url}?start_date={today_iso}&end_date={today_iso}")
        self.assertEqual(resp_before.status_code, 200)
        data_before = resp_before.json()
        member_stat_before = next(m for m in data_before["members"] if m["username"] == self.member_user.username)
        self.assertEqual(member_stat_before["total_seconds"], 0)
        self.assertEqual(member_stat_before["avg_seconds"], 0)

        # Bar chart today entry is 0.0 hrs
        today_chart_before = next(d for d in data_before["chart_data"][self.member_user.username] if d["isoDate"] == today_iso)
        self.assertEqual(today_chart_before["hours"], 0.0)
        self.assertFalse(today_chart_before["hasWork"])

        # 2. Member logs a 2.5 hour work session today in the database
        now = timezone.localtime()
        start_session = now.replace(hour=9, minute=0, second=0, microsecond=0)
        end_session = start_session + timedelta(hours=2, minutes=30)
        session1 = TaskWorkSession.objects.create(
            task=task,
            user=self.member_user,
            started_at=start_session,
            ended_at=end_session,
        )

        # 3. Stats API is called (e.g. concurrent poll or view refresh)
        resp_after1 = self.client.get(f"{stats_api_url}?start_date={today_iso}&end_date={today_iso}")
        self.assertEqual(resp_after1.status_code, 200)
        data_after1 = resp_after1.json()
        member_stat_after1 = next(m for m in data_after1["members"] if m["username"] == self.member_user.username)
        self.assertEqual(member_stat_after1["total_seconds"], 9000)  # 2.5h * 3600
        self.assertEqual(member_stat_after1["avg_seconds"], 9000)
        self.assertIn("2 hours 30 minutes", member_stat_after1["avg_time_formatted"])

        # Bar chart today entry now reflects 2.5 hrs from database
        today_chart_after1 = next(d for d in data_after1["chart_data"][self.member_user.username] if d["isoDate"] == today_iso)
        self.assertEqual(today_chart_after1["hours"], 2.5)
        self.assertTrue(today_chart_after1["hasWork"])

        # 4. Another session of 1.5 hours is logged today on the same or another task
        start_session2 = start_session + timedelta(hours=3)
        end_session2 = start_session2 + timedelta(hours=1, minutes=30)
        TaskWorkSession.objects.create(
            task=task,
            user=self.member_user,
            started_at=start_session2,
            ended_at=end_session2,
        )

        # 5. Subsequent concurrent fetch shows cumulative 4.0 hours
        resp_after2 = self.client.get(f"{stats_api_url}?start_date={today_iso}&end_date={today_iso}")
        self.assertEqual(resp_after2.status_code, 200)
        data_after2 = resp_after2.json()
        member_stat_after2 = next(m for m in data_after2["members"] if m["username"] == self.member_user.username)
        self.assertEqual(member_stat_after2["total_seconds"], 14400)  # 4.0h * 3600
        self.assertEqual(member_stat_after2["avg_seconds"], 14400)
        self.assertIn("4 hours", member_stat_after2["avg_time_formatted"])

        today_chart_after2 = next(d for d in data_after2["chart_data"][self.member_user.username] if d["isoDate"] == today_iso)
        self.assertEqual(today_chart_after2["hours"], 4.0)
        self.assertTrue(today_chart_after2["hasWork"])

    def test_admin_dashboard_template_contains_realtime_polling_and_no_mock_fallbacks(self):
        """Dashboard template includes real-time concurrent polling script and no hardcoded fallback datasets."""
        self.client.force_login(self.admin_user)
        response = self.client.get(self.dashboard_url)
        content = response.content.decode()

        self.assertIn("fetchLatestDashboardStats", content)
        self.assertIn("setInterval", content)
        self.assertIn("visibilitychange", content)
        self.assertNotIn("fallbackWorkLogs", content)
        self.assertNotIn("fallbackStats", content)
        self.assertNotIn("47769", content)  # mock preset seconds for Chloe



