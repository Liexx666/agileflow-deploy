from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password/change/", views.change_password_ui, name="change_password"),

    # US-11
    path(
        "password/reset/",
        views.reset_password_ui,
        name="reset_password",
    ),

    # US-27 & Admin User Management
    path(
        "accounts/",
        views.user_accounts_ui,
        name="user_accounts",
    ),
    path(
        "accounts/<int:user_id>/reset-password/",
        views.admin_reset_user_password,
        name="admin_reset_user_password",
    ),
    path(
        "accounts/<int:user_id>/remove/",
        views.admin_remove_user_account,
        name="admin_remove_user_account",
    ),

    # US-33
    path(
        "accounts/new/",
        views.register_account_ui,
        name="register_account",
    ),

    # US-24, US-25, US-26
    path(
        "admin-dashboard/",
        views.admin_dashboard_ui,
        name="admin_dashboard",
    ),
    path(
        "admin-dashboard/reassign-task/",
        views.admin_reassign_task,
        name="admin_reassign_task",
    ),
    path(
        "admin-dashboard/stats-api/",
        views.admin_dashboard_stats_api,
        name="admin_dashboard_stats_api",
    ),

    # Theme Preferences
    path(
        "theme/update/",
        views.update_theme_preference,
        name="update_theme_preference",
    ),
]