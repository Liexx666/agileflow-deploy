from django.urls import path

from . import sprint_views
from . import views


app_name = "backlog"

urlpatterns = [
    path("", views.home, name="home"),
    path("backlog/", views.product_backlog, name="product_backlog"),
    path("sprints/<int:sprint_id>/backlog/", views.product_backlog, name="sprint_backlog"),
    path("sprint-board/", views.sprint_board, name="sprint_board"),
    path("sprint-board/<int:sprint_id>/", views.sprint_board, name="sprint_board_detail"),
    path("tasks/new/", views.create_task, name="create_task"),
    path("tasks/<int:task_id>/", views.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:task_id>/delete/", views.delete_task, name="delete_task"),
    path("tasks/<int:task_id>/update-status/", views.update_task_status, name="update_task_status"),
    path("sprints/", views.sprint_list, name="sprint_list"),
    path("sprints/new/", views.create_sprint, name="create_sprint"),
    path("sprints/<int:sprint_id>/", views.sprint_detail, name="sprint_detail"),
    path("sprints/<int:sprint_id>/delete/", views.delete_sprint, name="delete_sprint"),
    path("sprints/<int:sprint_id>/edit/", views.edit_sprint, name="edit_sprint"),
    path("sprints/<int:sprint_id>/assign/<str:role>/", views.assign_sprint_role, name="assign_sprint_role"),

    # US-15
    path("tasks/<int:task_id>/move/", sprint_views.move_task_endpoint, name="move_task"),

    # US-16
    path("tasks/<int:task_id>/sprint-status/", sprint_views.sprint_task_status_endpoint, name="sprint_task_status"),

    # US-19: Owner-scoped work session creation and editing.
    path("tasks/<int:task_id>/time/", sprint_views.record_task_time, name="record_task_time"),
    path("tasks/<int:task_id>/time/<int:session_id>/edit/", sprint_views.edit_task_time, name="edit_task_time"),

    # US-17
    path("sprints/<int:sprint_id>/board/data/", sprint_views.sprint_board_data, name="sprint_board_data"),
    path("sprints/<int:sprint_id>/board/view/", sprint_views.sprint_board_view_endpoint, name="sprint_board_view"),

    # US-18
    path("sprints/<int:sprint_id>/status/", sprint_views.sprint_status_endpoint, name="sprint_status"),

    # US-21
    path("sprints/<int:sprint_id>/burndown/", sprint_views.sprint_burndown_data, name="sprint_burndown"),

    # US-23
    path("deleted-tasks/", views.deleted_tasks, name="deleted_tasks"),
    path("tasks/<int:task_id>/recover/", views.recover_task, name="recover_task"),
    path("deleted-sprints/", views.deleted_sprints, name="deleted_sprints"),
    path("sprints/<int:sprint_id>/recover/", views.recover_sprint, name="recover_sprint"),
]
