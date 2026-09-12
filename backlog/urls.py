from django.urls import path

from . import views


app_name = "backlog"

urlpatterns = [
    path("", views.product_backlog, name="product_backlog"),
    path("tasks/new/", views.create_task, name="create_task"),
    path("tasks/<int:task_id>/", views.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/edit/", views.edit_task, name="edit_task"),
    path("tasks/<int:task_id>/delete/", views.delete_task, name="delete_task"),
]