import json
import os
import sys

if __name__ == "__main__" and __package__ is None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agileflow_project.settings")
    import django

    django.setup()
    from accounts.forms import (
        AdminRegisterAccountForm,
        EmailLoginForm,
        ResetPasswordForm,
        InitialPasswordChangeForm,
    )
    from accounts.models import AccountSecurity, UserThemePreference
else:
    try:
        from .forms import (
            AdminRegisterAccountForm,
            EmailLoginForm,
            ResetPasswordForm,
            InitialPasswordChangeForm,
        )
        from .models import AccountSecurity, UserThemePreference
    except ImportError:
        from accounts.forms import (
            AdminRegisterAccountForm,
            EmailLoginForm,
            ResetPasswordForm,
            InitialPasswordChangeForm,
        )
        from accounts.models import AccountSecurity, UserThemePreference

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


def login_view(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if request.user.is_authenticated:
        return redirect(next_url or "backlog:product_backlog")

    if request.method == "POST":
        form = EmailLoginForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            security, _ = AccountSecurity.objects.get_or_create(user=form.user)
            login(request, form.user)
            if security.must_change_password:
                return redirect("accounts:change_password")
            return redirect(next_url or "backlog:product_backlog")
    else:
        form = EmailLoginForm(request=request)

    return render(request, "accounts/login.html", {"form": form})


@login_required
def change_password_ui(request):
    security, _ = AccountSecurity.objects.get_or_create(user=request.user)
    form = InitialPasswordChangeForm(user=request.user, data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            security.must_change_password = False
            security.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed. Welcome to your Sprint Board.")
        return redirect("backlog:home")
    return render(request, "accounts/change_password.html", {"form": form, "required_change": security.must_change_password})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def reset_password_ui(request):
    """
    US-11: Password reset for logged-in users.
    Validates user email matches current account, enforces 8-20 character
    alphanumeric complexity, updates password securely, and redirects to login.
    """
    if request.method == "POST":
        form = ResetPasswordForm(request.POST, current_user=request.user)
        if form.is_valid():
            form.save()
            logout(request)
            messages.success(
                request,
                "Your password has been successfully reset. Please log in with your new password.",
            )
            return redirect("accounts:login")
    else:
        form = ResetPasswordForm(current_user=request.user)

    return render(request, "accounts/reset_password.html", {"form": form})


@login_required
def user_accounts_ui(request):
    """
    US-27: View user accounts for administration.
    Only accessible by staff/admin users.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to view user accounts.",
        )
        return redirect("backlog:product_backlog")

    from django.db.models import Count, Q
    from backlog.models import Task

    User = get_user_model()
    users = User.objects.annotate(
        assigned_tasks_count=Count(
            "assigned_tasks",
            filter=Q(assigned_tasks__is_deleted=False),
        ),
        active_tasks_count=Count(
            "assigned_tasks",
            filter=Q(assigned_tasks__is_deleted=False) & ~Q(assigned_tasks__status="completed") & (Q(assigned_tasks__sprint__isnull=True) | ~Q(assigned_tasks__sprint__status__in=["completed", "cancelled", "stopped"])),
        ),
        completed_tasks_count=Count(
            "assigned_tasks",
            filter=Q(assigned_tasks__is_deleted=False) & (Q(assigned_tasks__status="completed") | Q(assigned_tasks__sprint__status__in=["completed", "cancelled", "stopped"])),
        ),
    ).order_by(
        "first_name",
        "last_name",
        "username",
    )

    all_eligible_users = list(
        User.objects.filter(is_active=True, is_staff=False, is_superuser=False)
        .order_by("first_name", "last_name", "username")
        .values("id", "username", "first_name", "last_name")
    )
    for u in all_eligible_users:
        full_name = f"{u['first_name']} {u['last_name']}".strip()
        u["full_name"] = full_name or u["username"]

    all_tasks_qs = (
        Task.objects.filter(is_deleted=False, assignee__isnull=False)
        .select_related("sprint")
        .prefetch_related("sprint__team_members")
        .order_by("status", "title")
    )

    user_active_tasks = {}
    for task in all_tasks_qs:
        assignee_id = str(task.assignee_id)
        if assignee_id not in user_active_tasks:
            user_active_tasks[assignee_id] = []

        is_sprint = bool(task.sprint)
        sprint_name = task.sprint.name if task.sprint else ""
        sprint_status = task.sprint.status if task.sprint else ""

        is_locked_or_completed = bool(
            task.status == "completed" or
            (task.sprint and task.sprint.status in ["completed", "cancelled", "stopped"])
        )
        requires_reassign = not is_locked_or_completed

        if is_sprint:
            eligible_members = [
                {
                    "id": m.id,
                    "username": m.username,
                    "full_name": m.get_full_name() or m.username,
                }
                for m in task.sprint.team_members.all()
                if not (m.is_staff or m.is_superuser) and m.is_active and m.id != task.assignee_id
            ]
        else:
            eligible_members = [
                {
                    "id": m["id"],
                    "username": m["username"],
                    "full_name": m["full_name"],
                }
                for m in all_eligible_users
                if m["id"] != task.assignee_id
            ]

        user_active_tasks[assignee_id].append({
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "status_display": task.get_status_display(),
            "is_sprint": is_sprint,
            "sprint_name": sprint_name,
            "sprint_status": sprint_status,
            "is_completed": is_locked_or_completed,
            "requires_reassign": requires_reassign,
            "eligible_members": eligible_members,
        })

    return render(
        request,
        "accounts/user_accounts.html",
        {
            "account_users": users,
            "user_active_tasks": user_active_tasks,
            "user_active_tasks_json": json.dumps(user_active_tasks),
        },
    )


@login_required
@require_POST
def admin_reset_user_password(request, user_id):
    """
    Allows administrators/staff to reset a user's password to default ('password123').
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to reset user passwords.",
        )
        return redirect("backlog:product_backlog")

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)
    with transaction.atomic():
        target_user.set_password("password123")
        target_user.save(update_fields=["password"])
        AccountSecurity.objects.update_or_create(user=target_user, defaults={"must_change_password": True})

    display_name = target_user.get_full_name() or target_user.username
    messages.success(
        request,
        f"Password for {display_name} (@{target_user.username}) has been successfully reset to default (password123).",
    )
    return redirect("accounts:user_accounts")


@login_required
@require_POST
def admin_remove_user_account(request, user_id):
    """
    Allows administrators/staff to remove a user account.
    If the account has active (non-completed) assigned tasks, they must be reassigned
    before removal can proceed.
    - Product backlog tasks: can be reassigned to any active user except admins.
    - Sprint backlog tasks: can be reassigned to members working on that sprint (except admins).
    - Completed tasks: do not need to be reassigned and remain locked.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to remove user accounts.",
        )
        return redirect("backlog:product_backlog")

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        messages.error(
            request,
            "You cannot remove your own account.",
        )
        return redirect("accounts:user_accounts")

    from backlog.models import Sprint, Task, TaskHistory

    # Find active tasks assigned to target_user that require reassignment
    raw_active_tasks = (
        Task.objects.filter(
            assignee=target_user,
            is_deleted=False,
        )
        .exclude(status="completed")
        .select_related("sprint")
    )

    active_tasks = [
        t for t in raw_active_tasks
        if not (t.sprint and t.sprint.status in ["completed", "cancelled", "stopped"])
    ]

    display_name = target_user.get_full_name() or target_user.username

    reassignments = {}
    if active_tasks:
        for t in active_tasks:
            field_name = f"reassign_task_{t.id}"
            new_assignee_id = request.POST.get(field_name)

            if not new_assignee_id:
                messages.error(
                    request,
                    f"Cannot remove {display_name}: This account has {len(active_tasks)} assigned task(s). Please reassign or unassign all tasks before removing the account.",
                )
                return redirect("accounts:user_accounts")

            try:
                new_assignee = User.objects.get(pk=new_assignee_id)
            except (User.DoesNotExist, ValueError):
                messages.error(
                    request,
                    f"Invalid reassignment selected for task '{t.title}'.",
                )
                return redirect("accounts:user_accounts")

            if new_assignee.pk == target_user.pk:
                messages.error(
                    request,
                    f"Cannot reassign task '{t.title}' to the user being removed.",
                )
                return redirect("accounts:user_accounts")

            if new_assignee.is_staff or new_assignee.is_superuser:
                messages.error(
                    request,
                    f"Tasks cannot be reassigned to administrators ('{t.title}').",
                )
                return redirect("accounts:user_accounts")

            if t.sprint:
                if not t.sprint.team_members.filter(pk=new_assignee.pk).exists():
                    messages.error(
                        request,
                        f"Task '{t.title}' is in sprint '{t.sprint.name}' and can only be reassigned to members of that sprint.",
                    )
                    return redirect("accounts:user_accounts")

            reassignments[t.id] = new_assignee

    with transaction.atomic():
        # Reassign active tasks and log TaskHistory
        for t in active_tasks:
            new_assignee = reassignments[t.id]
            old_name = target_user.get_full_name() or target_user.username
            new_name = new_assignee.get_full_name() or new_assignee.username
            t.assignee = new_assignee
            t.save(update_fields=["assignee", "updated_at"])
            TaskHistory.objects.create(
                task=t,
                changed_by=request.user,
                description=f"{request.user.username} reassigned task from {old_name} to {new_name} during account removal",
            )

        # Clear sprint team memberships
        target_user.sprint_teams.clear()

        # Clear any sprint role assignments
        Sprint.objects.filter(product_owner=target_user).update(product_owner=None)
        Sprint.objects.filter(scrum_master=target_user).update(scrum_master=None)

        # Remove any work sessions associated with this user to prevent ProtectedError
        target_user.work_sessions.all().delete()

        username = target_user.username
        target_user.delete()

    if active_tasks:
        messages.success(
            request,
            f"Account for {display_name} (@{username}) has been successfully removed and {len(active_tasks)} assigned task(s) were reassigned.",
        )
    else:
        messages.success(
            request,
            f"Account for {display_name} (@{username}) has been successfully removed.",
        )
    return redirect("accounts:user_accounts")


@login_required
def register_account_ui(request):
    """
    US-33: Registering new accounts for admin role.
    Only accessible by staff/admin users.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to register new accounts.",
        )
        return redirect("backlog:product_backlog")

    if request.method == "POST":
        form = AdminRegisterAccountForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(
                request,
                f"Account for @{new_user.username} has been successfully registered.",
            )
            return redirect("accounts:user_accounts")
    else:
        form = AdminRegisterAccountForm()

    return render(request, "accounts/register_account.html", {"form": form})


def _calculate_dashboard_metrics(start_date, end_date):
    """
    Calculate real total time, daily averages, and calendar breakdown strictly from TaskWorkSession records in the database.
    """
    from datetime import datetime, time as dt_time, timedelta
    from django.utils import timezone
    from django.db.models import Sum
    from backlog.models import Task, TaskWorkSession

    total_days = max(1, (end_date - start_date).days + 1)
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, dt_time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, dt_time.max), tz)

    User = get_user_model()
    users = User.objects.filter(
        is_staff=False,
        is_superuser=False,
    ).order_by("first_name", "last_name", "username")

    sessions = TaskWorkSession.objects.filter(
        started_at__lte=end_dt,
        ended_at__gte=start_dt
    ).select_related("user", "task")

    user_sessions_map = {u.pk: [] for u in users}
    for s in sessions:
        if s.user_id in user_sessions_map:
            user_sessions_map[s.user_id].append(s)

    members_data = []
    chart_data_map = {}

    for u in users:
        u_sessions = user_sessions_map.get(u.pk, [])
        total_seconds = 0
        daily_breakdown = {}

        for s in u_sessions:
            s_start = max(s.started_at, start_dt)
            s_end = min(s.ended_at, end_dt)
            sec = max(0, int((s_end - s_start).total_seconds()))
            total_seconds += sec

            s_local_start = timezone.localtime(s.started_at)
            s_date = s_local_start.date()
            dur_hrs = round(sec / 3600.0, 2)
            st_time = s_local_start.strftime("%I:%M %p")

            if s_date not in daily_breakdown:
                daily_breakdown[s_date] = {
                    "date": s_date.strftime("%b %d"),
                    "hours": dur_hrs,
                    "startTime": st_time,
                }
            else:
                daily_breakdown[s_date]["hours"] = round(daily_breakdown[s_date]["hours"] + dur_hrs, 2)



        avg_seconds = total_seconds // total_days
        avg_hours = avg_seconds // 3600
        avg_mins = (avg_seconds % 3600) // 60
        avg_secs = avg_seconds % 60
        hours_label = f"{avg_hours} hour{'s' if avg_hours != 1 else ''}"
        mins_label = f"{avg_mins} minute{'s' if avg_mins != 1 else ''}"
        secs_label = f"{avg_secs} second{'s' if avg_secs != 1 else ''}"
        avg_time_formatted = f"Average time spent: {hours_label} {mins_label} {secs_label}"

        display_name = u.get_full_name() or u.username
        initials = (u.first_name[:1] + u.last_name[:1]).upper() if u.first_name and u.last_name else u.username[:2].upper()

        members_data.append({
            "id": u.pk,
            "username": u.username,
            "display_name": display_name,
            "initials": initials,
            "total_seconds": total_seconds,
            "avg_seconds": avg_seconds,
            "avg_time_formatted": avg_time_formatted,
        })

        # Ensure EVERY date in the entire timeline period [start_date, end_date] is present
        all_period_days = []
        cur_day = start_date
        while cur_day <= end_date:
            if cur_day in daily_breakdown:
                entry = daily_breakdown[cur_day]
                all_period_days.append({
                    "date": cur_day.strftime("%b %d"),
                    "isoDate": cur_day.strftime("%Y-%m-%d"),
                    "hours": round(float(entry["hours"]), 2),
                    "startTime": entry.get("startTime", "09:00 AM"),
                    "hasWork": True,
                })
            else:
                all_period_days.append({
                    "date": cur_day.strftime("%b %d"),
                    "isoDate": cur_day.strftime("%Y-%m-%d"),
                    "hours": 0.0,
                    "startTime": "No work logged",
                    "hasWork": False,
                })
            cur_day += timedelta(days=1)

        max_h = max((d["hours"] for d in all_period_days), default=1.0) or 1.0
        for d in all_period_days:
            if d["hours"] > 0:
                d["heightPct"] = min(100, max(15, int((d["hours"] / max_h) * 100)))
            else:
                d["heightPct"] = 0

        chart_data_map[u.username] = all_period_days
        chart_data_map[display_name] = all_period_days
        full_alias = f"{u.first_name} {u.last_name}".strip()
        if full_alias:
            chart_data_map[full_alias] = all_period_days

    return members_data, chart_data_map, total_days


@login_required
def admin_dashboard_stats_api(request):
    """
    API endpoint returning real-time concurrent dashboard statistics from the database.
    Allows concurrent reflection of newly logged work sessions on the bar chart and average times.
    """
    from datetime import datetime, timedelta
    from django.utils import timezone

    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Access denied."}, status=403)

    start_str = request.GET.get("start_date", "").strip()
    end_str = request.GET.get("end_date", "").strip()

    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    default_end = today

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else default_end
    except ValueError:
        end_date = default_end

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    members_data, chart_data_map, total_days = _calculate_dashboard_metrics(start_date, end_date)

    sort_order = request.GET.get("sort", "desc").strip().lower()
    if sort_order == "asc":
        members_data.sort(key=lambda x: x["avg_seconds"])
    else:
        members_data.sort(key=lambda x: x["avg_seconds"], reverse=True)

    return JsonResponse({
        "ok": True,
        "members": members_data,
        "chart_data": chart_data_map,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "total_days": total_days,
    })


@login_required
def admin_dashboard_ui(request):
    """
    US-24: View Admin Dashboard.
    US-25: View Team Member Time Summary.
    US-26: Sort Dashboard Team Members.
    Calculates real total time and daily average time per user across the selected timeline from the database.
    """
    import json
    from datetime import datetime, timedelta
    from django.utils import timezone
    from backlog.models import Task

    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to view the Admin Dashboard.",
        )
        return redirect("backlog:product_backlog")

    start_str = request.GET.get("start_date", "").strip()
    end_str = request.GET.get("end_date", "").strip()

    today = timezone.localdate()
    default_start = today - timedelta(days=29)
    default_end = today

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else default_start
    except ValueError:
        start_date = default_start

    try:
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else default_end
    except ValueError:
        end_date = default_end

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    members_data, chart_data_map, total_days = _calculate_dashboard_metrics(start_date, end_date)

    User = get_user_model()
    users = User.objects.all().order_by("first_name", "last_name", "username")

    sort_order = request.GET.get("sort", "desc").strip().lower()
    if sort_order == "asc":
        members_data.sort(key=lambda x: x["avg_seconds"])
    else:
        members_data.sort(key=lambda x: x["avg_seconds"], reverse=True)
        sort_order = "desc"

    all_users = [
        {
            "id": u.pk,
            "username": u.username,
            "full_name": u.get_full_name() or u.username,
            "email": u.email or f"{u.username.lower()}@student.monash.edu",
            "is_admin": bool(u.is_staff or u.is_superuser),
        }
        for u in users
    ]

    raw_tasks = (
        Task.objects.filter(is_deleted=False)
        .select_related("sprint", "assignee")
        .prefetch_related("sprint__team_members")
        .order_by("-updated_at")
    )
    backlog_tasks = []
    for t in raw_tasks:
        sprint_info = None
        if t.sprint:
            sprint_members = [
                {
                    "id": m.pk,
                    "username": m.username,
                    "full_name": m.get_full_name() or m.username,
                    "is_admin": bool(m.is_staff or m.is_superuser),
                }
                for m in t.sprint.team_members.all()
                if not (m.is_staff or m.is_superuser)
            ]
            sprint_info = {
                "id": t.sprint.id,
                "name": t.sprint.name,
                "status": t.sprint.status,
                "team_members": sprint_members,
            }
        backlog_tasks.append({
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "assignee_id": t.assignee.id if t.assignee else None,
            "assignee_username": t.assignee.username if t.assignee else "",
            "assignee_name": (t.assignee.get_full_name() or t.assignee.username) if t.assignee else "",
            "sprint": sprint_info,
        })

    current_team = request.GET.get("team", "All Members").strip()
    current_view = request.GET.get("view", "analytics").strip()
    selected_member = request.GET.get("member", "").strip()

    context = {
        "members": members_data,
        "members_json": json.dumps(members_data),
        "chart_data_json": json.dumps(chart_data_map),
        "all_users": all_users,
        "all_users_json": json.dumps(all_users),
        "backlog_tasks": backlog_tasks,
        "backlog_tasks_json": json.dumps(backlog_tasks, default=str),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "total_days": total_days,
        "current_sort": sort_order,
        "current_team": current_team,
        "current_view": current_view,
        "selected_member": selected_member,
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
@require_POST
def admin_reassign_task(request):
    """
    Reassign a task when a member is removed from a team.
    - If the task is in a sprint, it can only be assigned to a member in that sprint (excluding admins).
    - If the task is in the backlog, it can be assigned to anyone else except an admin.
    """
    from backlog.models import Task, TaskHistory

    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({"ok": False, "error": "Access denied."}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except Exception:
        data = request.POST

    task_id = data.get("task_id")
    assignee_id = data.get("assignee_id")
    assignee_username = data.get("assignee_username")

    if not task_id:
        return JsonResponse({"ok": False, "error": "Task ID is required."}, status=400)

    task = get_object_or_404(Task, pk=task_id)

    if task.status == "completed":
        return JsonResponse({"ok": False, "error": "A completed task cannot be reassigned."}, status=400)
    if task.sprint and task.sprint.status in ["completed", "stopped", "cancelled"]:
        status_disp = "cancelled" if task.sprint.status in ["stopped", "cancelled"] else "completed"
        return JsonResponse({"ok": False, "error": f"Tasks in a {status_disp} sprint cannot be reassigned."}, status=400)

    User = get_user_model()
    new_assignee = None
    if assignee_id:
        new_assignee = get_object_or_404(User, pk=assignee_id)
    elif assignee_username:
        new_assignee = get_object_or_404(User, username=assignee_username)
    else:
        return JsonResponse({"ok": False, "error": "Please select a valid assignee."}, status=400)

    # 1. Backlog tasks vs Sprint tasks rules:
    # If the task is in a sprint, I should assign the task to one of the members in the sprint
    if task.sprint:
        if new_assignee.is_staff or new_assignee.is_superuser:
            return JsonResponse({"ok": False, "error": "Sprint tasks cannot be assigned to an administrator."}, status=400)
        if not task.sprint.team_members.filter(pk=new_assignee.pk).exists():
            return JsonResponse({
                "ok": False,
                "error": f"Task '{task.title}' is in sprint '{task.sprint.name}'. It must be assigned to a member of this sprint."
            }, status=400)
    else:
        # If the task is only in the backlog, I can assign it to anyone else but the admin
        if new_assignee.is_staff or new_assignee.is_superuser:
            return JsonResponse({"ok": False, "error": "Backlog tasks cannot be assigned to an administrator."}, status=400)

    task.assignee = new_assignee
    task.save(update_fields=["assignee", "updated_at"])

    admin_name = request.user.get_full_name() or request.user.username
    assignee_display = new_assignee.get_full_name() or new_assignee.username
    TaskHistory.objects.create(
        task=task,
        changed_by=request.user,
        description=f'{admin_name} reassigned task to "{assignee_display}"',
    )

    return JsonResponse({
        "ok": True,
        "task_id": task.id,
        "task_title": task.title,
        "assignee_id": new_assignee.id,
        "assignee_username": new_assignee.username,
        "assignee_name": assignee_display,
    })


@login_required
@require_POST
def update_theme_preference(request):
    """
    Persist personal theme and light/dark mode preferences per user.
    Accepts JSON payload or form data: { "theme": "...", "mode": "..." }
    """
    theme = None
    mode = None

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
            theme = data.get("theme")
            mode = data.get("mode")
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)
    else:
        theme = request.POST.get("theme")
        mode = request.POST.get("mode")

    pref = UserThemePreference.get_for_user(request.user)

    valid_themes = [choice[0] for choice in UserThemePreference.THEME_CHOICES]
    valid_modes = [choice[0] for choice in UserThemePreference.MODE_CHOICES]

    if theme is not None:
        if theme in valid_themes:
            pref.theme = theme
        else:
            return JsonResponse({"status": "error", "message": f"Invalid theme '{theme}'"}, status=400)

    if mode is not None:
        if mode in valid_modes:
            pref.mode = mode
        else:
            return JsonResponse({"status": "error", "message": f"Invalid mode '{mode}'"}, status=400)

    pref.save()

    return JsonResponse({
        "status": "success",
        "theme": pref.theme,
        "mode": pref.mode,
        "theme_name": pref.get_theme_display(),
        "mode_name": pref.get_mode_display(),
    })


if __name__ == "__main__":
    print("accounts/views.py executed successfully.")


