from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import AccountSecurity
from backlog.models import Task, Tag, Sprint


class ProductBacklogTests(TestCase):
    """
    Automated tests for viewing and interacting with the Product Backlog.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="backlog_reader")
        AccountSecurity.objects.filter(user=self.user).update(must_change_password=False)
        self.client.force_login(self.user)

        self.tag_ui = Tag.objects.create(name="UI")
        self.tag_ux = Tag.objects.create(name="UX")
        self.tag_fe = Tag.objects.create(name="Front-end")

        self.sprint1 = Sprint.objects.create(
            name="Sprint 1",
            status="completed",
        )

        self.sprint2 = Sprint.objects.create(
            name="Sprint 2",
            status="active",
        )

        self.task1 = Task.objects.create(
            title="Task 1",
            item_type="story",
            priority="low",
            story_points=3,
        )

        self.task1.tags.add(
            self.tag_ui,
            self.tag_ux,
        )

        self.task2 = Task.objects.create(
            title="Task 2",
            item_type="story",
            priority="urgent",
            story_points=10,
        )

        self.task2.tags.add(self.tag_fe)

    def test_backlog_view_status_code(self):
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "backlog/product_backlog.html",
        )

    def test_backlog_tasks_in_context(self):
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(
            response.context["total_items"],
            2,
        )

        self.assertEqual(
            response.context["total_points"],
            13,
        )

    def test_tag_filtering(self):
        url = (
            reverse("backlog:product_backlog")
            + "?tag=Front-end"
        )

        response = self.client.get(url)
        tasks = response.context["tasks"]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Task 2")

    def test_priority_sorting_urgent_first(self):
        url = (
            reverse("backlog:product_backlog")
            + "?sort=priority_desc"
        )

        response = self.client.get(url)
        tasks = list(response.context["tasks"])

        self.assertEqual(tasks[0].title, "Task 2")
        self.assertEqual(tasks[1].title, "Task 1")

    def test_priority_sorting_lowest_first(self):
        url = (
            reverse("backlog:product_backlog")
            + "?sort=priority_asc"
        )

        response = self.client.get(url)
        tasks = list(response.context["tasks"])

        self.assertEqual(tasks[0].title, "Task 1")
        self.assertEqual(tasks[1].title, "Task 2")

    def test_backlog_header_title_without_selected_sprint(self):
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_title"], "Sprint Board")
        self.assertContains(response, '<h1 class="backlog-title">Sprint Board</h1>')

    def test_backlog_header_title_with_selected_sprint(self):
        self.sprint2.team_members.add(self.user)
        url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_title"], f"{self.sprint2.name} Backlog Management")
        self.assertContains(response, f'<h1 class="backlog-title">{self.sprint2.name} Backlog Management</h1>')

    def test_column_order_product_backlog_on_left_sprint_backlog_on_right(self):
        """In sprint backlog management view, product backlog is on left and sprint backlog on right."""
        self.sprint2.team_members.add(self.user)
        url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        prod_index = content.find('id="product-backlog-dropzone"')
        sprint_index = content.find('Sprint Backlog</h2>')

        self.assertNotEqual(prod_index, -1)
        self.assertNotEqual(sprint_index, -1)
        self.assertLess(prod_index, sprint_index, "Product Backlog column should come before Sprint Backlog column")

    def test_sprint_board_without_selected_sprint_has_no_product_backlog_column(self):
        """Sprint board general view contains only sprint backlog information and has no product backlog column."""
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="product-backlog-dropzone"')
        self.assertContains(response, 'Sprint Backlog</h2>')

    def test_sprint_backlog_management_removes_three_dots_and_create_actions(self):
        """In the sprint backlog management view (selected sprint), 3 dots and create/deleted actions are removed."""
        self.sprint2.team_members.add(self.user)
        url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sprint Options")
        self.assertNotContains(response, "bi-three-dots-vertical")
        self.assertNotContains(response, "Create new task")
        self.assertNotContains(response, "Create new sprint")
        self.assertNotContains(response, "Deleted Tasks")
        self.assertNotContains(response, "Deleted Sprints")

    def test_general_backlog_has_create_task_and_three_dots(self):
        """On sprint board (/backlog/), users see sprint options but no create task (task creation is in product backlog)."""
        self.sprint2.team_members.add(self.user)
        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Create new task")
        self.assertContains(response, "Sprint Options")
        self.assertContains(response, "bi-three-dots-vertical")

    def test_sprint_backlog_management_has_back_button_to_sprint_board(self):
        """In sprint backlog management view, a back button returns to the sprint board where all sprints are."""
        self.sprint2.team_members.add(self.user)
        url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        sprint_board_url = reverse("backlog:product_backlog")
        self.assertContains(response, 'id="backToSprintBoardBtn"')
        self.assertContains(response, f'href="{sprint_board_url}"')
        self.assertContains(response, "Back")

        # In the sprint board view (where all sprints are already displayed), the back button is not present
        general_response = self.client.get(sprint_board_url)
        self.assertNotContains(general_response, 'id="backToSprintBoardBtn"')

    def test_sprint_board_header_manage_sprint_and_dblclick_and_sprint_info(self):
        """On sprint board, each sprint header has Manage sprint button, dblclick on name navigates to edit, and 3-dots has Sprint Information."""
        self.sprint2.team_members.add(self.user)
        sprint_board_url = reverse("backlog:product_backlog")
        response = self.client.get(sprint_board_url)

        self.assertEqual(response.status_code, 200)
        # Manage sprint button exists and links to sprint backlog
        sprint_backlog_url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        self.assertContains(response, "Manage sprint")
        self.assertContains(response, sprint_backlog_url)

        # Sprint name has ondblclick pointing to edit sprint
        edit_sprint_url = reverse("backlog:edit_sprint", args=[self.sprint2.id])
        self.assertContains(response, edit_sprint_url)
        self.assertContains(response, "ondblclick=")

        # 3 dots menu has Sprint Information and View Board, not Edit Sprint
        sprint_detail_url = reverse("backlog:sprint_detail", args=[self.sprint2.id])
        self.assertContains(response, "Sprint Information")
        self.assertContains(response, sprint_detail_url)
        self.assertNotContains(response, "Edit Sprint")
        view_board_url = reverse("backlog:sprint_board_detail", args=[self.sprint2.id])
        self.assertContains(response, "View Board")
        self.assertContains(response, view_board_url)
        self.assertNotContains(response, "View Kanban Board")

    def test_edit_sprint_page_has_manage_sprint_button(self):
        """On top of edit sprint form, a Manage Sprint button takes the user to the sprint backlog management view."""
        self.sprint2.team_members.add(self.user)
        response = self.client.get(reverse("backlog:edit_sprint", args=[self.sprint2.id]))

        self.assertEqual(response.status_code, 200)
        sprint_backlog_url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])
        self.assertContains(response, "Manage Sprint")
        self.assertContains(response, sprint_backlog_url)
        self.assertContains(response, 'id="manageSprintTopBtn"')

    def test_update_task_status_from_sprint_backlog_view_redirects_back_to_sprint_backlog(self):
        """Updating task status from sprint backlog management view stays on that sprint's backlog view."""
        self.sprint2.team_members.add(self.user)
        self.task2.sprint = self.sprint2
        self.task2.save()
        sprint_backlog_url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])

        # Verify HTML form contains hidden next input with sprint backlog url
        get_response = self.client.get(sprint_backlog_url)
        self.assertContains(get_response, f'<input type="hidden" name="next" value="{sprint_backlog_url}">')

        # POST with next parameter
        post_response = self.client.post(
            reverse("backlog:update_task_status", args=[self.task2.id]),
            {"status": "in_progress", "next": sprint_backlog_url},
        )
        self.assertRedirects(post_response, sprint_backlog_url)
        self.task2.refresh_from_db()
        self.assertEqual(self.task2.status, "in_progress")

    def test_update_task_status_with_referer_redirects_back_to_sprint_backlog(self):
        """Updating task status without next param but with referer redirects back to sprint backlog."""
        self.sprint2.team_members.add(self.user)
        self.task2.sprint = self.sprint2
        self.task2.save()
        sprint_backlog_url = reverse("backlog:sprint_backlog", args=[self.sprint2.id])

        post_response = self.client.post(
            reverse("backlog:update_task_status", args=[self.task2.id]),
            {"status": "completed"},
            HTTP_REFERER=f"http://testserver{sprint_backlog_url}",
        )
        self.assertRedirects(post_response, sprint_backlog_url)
        self.task2.refresh_from_db()
        self.assertEqual(self.task2.status, "completed")

    def test_admin_sees_deleted_links_and_create_sprint_on_general_backlog(self):
        """On sprint board (/backlog/), admin sees Deleted Sprints and Create sprint, but task actions are in product backlog."""
        admin_user = User.objects.create_user(
            username="backlog_admin",
            is_staff=True,
            is_superuser=True,
        )
        AccountSecurity.objects.filter(user=admin_user).update(must_change_password=False)
        self.client.force_login(admin_user)

        url = reverse("backlog:product_backlog")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Deleted Tasks")
        self.assertContains(response, "Deleted Sprints")
        self.assertNotContains(response, reverse("backlog:deleted_tasks"))
        self.assertContains(response, reverse("backlog:deleted_sprints"))
        self.assertNotContains(response, "Create new task")
        self.assertContains(response, "Create new sprint")

    def test_sprint_stopped_status_displays_as_cancelled(self):
        stopped_sprint = Sprint.objects.create(
            name="Alpha Sprint",
            status="stopped",
        )
        stopped_sprint.team_members.add(self.user)
        self.assertEqual(stopped_sprint.get_status_display(), "Cancelled")

        url = reverse("backlog:product_backlog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelled")
        self.assertNotContains(response, ">Stopped<")

    def test_drag_drop_eligibility_by_sprint_status(self):
        not_started_sprint = Sprint.objects.create(name="Not Started Sprint", status="not_started")
        not_started_sprint.team_members.add(self.user)

        planning_sprint = Sprint.objects.create(name="Planning Sprint", status="planning")
        planning_sprint.team_members.add(self.user)

        stopped_sprint = Sprint.objects.create(name="Cancelled Sprint", status="stopped")
        stopped_sprint.team_members.add(self.user)

        completed_sprint = self.sprint1
        completed_sprint.team_members.add(self.user)

        active_sprint = self.sprint2
        active_sprint.team_members.add(self.user)

        url = reverse("backlog:product_backlog")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        sprints_dict = {s.id: s for s in response.context["sprints"]}
        self.assertTrue(sprints_dict[not_started_sprint.id].can_drop)
        self.assertTrue(sprints_dict[planning_sprint.id].can_drop)
        self.assertTrue(sprints_dict[active_sprint.id].can_drop)
        self.assertFalse(sprints_dict[stopped_sprint.id].can_drop)
        self.assertFalse(sprints_dict[completed_sprint.id].can_drop)

    def test_move_task_into_not_started_sprint_allowed(self):
        not_started_sprint = Sprint.objects.create(name="Not Started Target", status="not_started")
        not_started_sprint.team_members.add(self.user)

        url = reverse("backlog:move_task", args=[self.task1.id])
        response = self.client.post(url, {"sprint_id": not_started_sprint.id})
        self.assertEqual(response.status_code, 200)

        self.task1.refresh_from_db()
        self.assertEqual(self.task1.sprint, not_started_sprint)

    def test_move_task_into_cancelled_sprint_rejected(self):
        cancelled_sprint = Sprint.objects.create(name="Cancelled Target", status="stopped")
        cancelled_sprint.team_members.add(self.user)

        url = reverse("backlog:move_task", args=[self.task1.id])
        response = self.client.post(url, {"sprint_id": cancelled_sprint.id})
        self.assertEqual(response.status_code, 409)

        self.task1.refresh_from_db()
        self.assertIsNone(self.task1.sprint)


