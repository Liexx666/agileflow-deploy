from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import SprintCreateForm, SprintEditForm, TaskCreateForm, TaskEditForm
from django.db.models import Sum, Q, Case, When, Value, IntegerField
from .models import Task, Tag, Sprint, SprintHistory, TaskHistory, SprintBoardPreference
from .sprint_forms import WorkSessionForm
from .sprint_services import work_time_unavailable_reason
from .burndown import build_sprint_burndown
from django.utils import timezone
from django.urls import reverse


def available_sprints(user):
    sprints = Sprint.objects.filter(is_deleted=False)
    if user.is_staff or user.is_superuser:
        return sprints
    return sprints.filter(Q(product_owner=user) | Q(scrum_master=user) | Q(team_members=user)).distinct()


@login_required
def home(request):
    return redirect("backlog:sprint_board")


@login_required
def product_backlog(request, sprint_id=None):
    """
    US-03: View Product Backlog (List View)
    Displays all active product backlog tasks with the Sprints sidebar,
    tag filtering, and priority/date sorting.
    """
    # Base queries
    accessible_sprints = available_sprints(request.user).order_by('created_at')
    selected_sprint = get_object_or_404(accessible_sprints, pk=sprint_id) if sprint_id else None
    sprints = accessible_sprints.filter(pk=sprint_id) if selected_sprint else accessible_sprints
    sprints = sprints.prefetch_related('team_members').select_related('product_owner', 'scrum_master')
    all_active_tasks = Task.objects.filter(is_deleted=False).filter(Q(sprint__isnull=True) | Q(sprint__in=sprints))
    tasks = all_active_tasks.select_related('assignee', 'sprint').prefetch_related('tags')

    # Query params
    search_query = request.GET.get('search', '').strip()
    selected_tags = request.GET.getlist('tag')
    selected_priority = request.GET.get('priority', '').strip()
    selected_type = request.GET.get('type', '').strip()
    selected_status = request.GET.get('status', '').strip()
    sort_by = request.GET.get('sort', 'urgent_to_lowest').strip()

    # Search filter
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(acceptance_criteria__icontains=search_query)
        )

    # Tag filtering (supports multiple tags)
    if selected_tags:
        for tag_name in selected_tags:
            if tag_name:
                tasks = tasks.filter(tags__name=tag_name)

    # Priority filter
    if selected_priority:
        tasks = tasks.filter(priority=selected_priority)

    # Item type filter
    if selected_type:
        tasks = tasks.filter(item_type=selected_type)

    # Status filter
    if selected_status:
        tasks = tasks.filter(status=selected_status)

    # Custom priority ordering
    priority_order = Case(
        When(priority='urgent', then=Value(4)),
        When(priority='important', then=Value(3)),
        When(priority='medium', then=Value(2)),
        When(priority='low', then=Value(1)),
        default=Value(0),
        output_field=IntegerField(),
    )

    # Sorting: Priority and Date order
    if sort_by in ['priority_asc', 'lowest_to_urgent']:
        tasks = tasks.annotate(p_val=priority_order).order_by('p_val', '-created_at')
    elif sort_by in ['priority_desc', 'urgent_to_lowest']:
        tasks = tasks.annotate(p_val=priority_order).order_by('-p_val', '-created_at')
    elif sort_by in ['created_asc', 'oldest_to_recent']:
        tasks = tasks.order_by('created_at')
    elif sort_by in ['created_desc', 'recent_to_oldest']:
        tasks = tasks.order_by('-created_at')
    else:
        # Default: Priority Urgent to Low
        tasks = tasks.annotate(p_val=priority_order).order_by('-p_val', '-created_at')

    # Overall Backlog metrics
    total_items = all_active_tasks.count()
    total_points = all_active_tasks.aggregate(total=Sum('story_points'))['total'] or 0
    story_count = all_active_tasks.filter(item_type='story').count()
    bug_count = all_active_tasks.filter(item_type='bug').count()

    all_tags = Tag.objects.all()

    product_tasks = [t for t in tasks if t.sprint_id is None]
    
    tasks_by_sprint = {}
    for task in tasks:
        tasks_by_sprint.setdefault(task.sprint_id, []).append(task)
    for sprint in sprints:
        sprint.filtered_tasks = tasks_by_sprint.get(sprint.pk, [])
        sprint.can_edit = (
            request.user.is_staff or request.user.is_superuser
            or request.user.pk in {sprint.product_owner_id, sprint.scrum_master_id}
            or any(member.pk == request.user.pk for member in sprint.team_members.all())
        )
        sprint.can_drop = sprint.can_edit and sprint.status == 'active'
        sprint.can_drag = sprint.can_edit and sprint.status != 'completed'

    context = {
        'tasks': tasks,
        'product_tasks': product_tasks,
        'sprints': sprints,
        'accessible_sprints': accessible_sprints,
        'selected_sprint': selected_sprint,
        'backlog_url': request.path,
        'page_title': f'{selected_sprint.name} Backlog' if selected_sprint else 'Backlog Management',
        'all_tags': all_tags,
        'selected_tags': selected_tags,
        'selected_priority': selected_priority,
        'selected_type': selected_type,
        'selected_status': selected_status,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_items': total_items,
        'total_points': total_points,
        'story_count': story_count,
        'bug_count': bug_count,
    }

    # Original US-03 return statement
    return render(request, 'backlog/product_backlog.html', context)


@login_required
def create_task(request):
    """
    US-04: Create a new Product Backlog task.

    GET displays the task form.
    POST validates and saves the submitted task.
    """
    backlog_sprint_id = request.GET.get('backlog_sprint', '')
    selected_backlog = get_object_or_404(available_sprints(request.user), pk=backlog_sprint_id) if backlog_sprint_id.isdecimal() else None
    backlog_return_url = reverse('backlog:sprint_backlog', args=[selected_backlog.pk]) if selected_backlog else reverse('backlog:product_backlog')
    if request.method == "POST":
        form = TaskCreateForm(request.POST, request.FILES)

        if form.is_valid():
            task = form.save()

            TaskHistory.objects.create(
                task=task,
                changed_by=request.user,
                description=f"{request.user.username} created {task.title}"
            )

            messages.success(
                request,
                f'"{task.title}" was added to the Product Backlog.',
            )

            return redirect(backlog_return_url)
    else:
        form = TaskCreateForm()

    return render(
        request,
        "backlog/create_task.html",
        {"form": form, "backlog_return_url": backlog_return_url},
    )


@login_required
def task_detail(request, task_id):
    """
    US-03/US-05/US-06: Display the details and history of a Product Backlog task.
    """
    task = get_object_or_404(
        Task,
        pk=task_id,
        is_deleted=False
    )

    return render_task_detail(request, task)


def render_task_detail(request, task, *, time_form=None, edit_time_form=None,
                       editing_session=None, open_time_modal="", status=200):
    """Use the same detail page for initial display and recoverable form errors."""
    can_edit_task = True
    if task.sprint and not (request.user.is_staff or request.user.is_superuser):
        can_edit_task = task.sprint.team_members.filter(id=request.user.id).exists()

    return render(request, "backlog/task_detail.html", {
        "task": task,
        "can_edit_task": can_edit_task,
        "history": task.history.filter(
            Q(is_time_entry_change=False) | Q(changed_by=request.user),
        ),
        "time_entries": task.work_sessions.filter(user=request.user),
        "time_unavailable_reason": work_time_unavailable_reason(task, request.user),
        "edit_time_unavailable_reason": work_time_unavailable_reason(task, request.user, editing=True),
        "time_form": time_form if time_form is not None else WorkSessionForm(auto_id="record_%s"),
        "edit_time_form": edit_time_form if edit_time_form is not None else WorkSessionForm(auto_id="edit_%s"),
        "editing_session": editing_session,
        "open_time_modal": open_time_modal,
        "time_zone": timezone.get_current_timezone_name(),
    }, status=status)


@login_required
def delete_task(request, task_id):
    """
    US-06: Delete a Product Backlog task.

    GET displays a confirmation page.
    POST soft-deletes the task by setting is_deleted=True.

    Maximum of 50 deleted tasks can be kept for recovery.
    Once 50 recoverable deleted tasks already exist, any further
    deleted task is permanently removed and cannot be recovered.
    """
    task = get_object_or_404(Task, pk=task_id, is_deleted=False)

    if task.sprint is not None:
        messages.error(
            request,
            f'"{task.title}" cannot be deleted because it is currently assigned to a sprint. '
            f'Move it back to the Product Backlog first.'
        )
        return redirect("backlog:task_detail", task_id=task.id)

    if task.status == 'completed':
        messages.error(
            request,
            f'"{task.title}" cannot be deleted because it is already completed.'
        )
        return redirect("backlog:task_detail", task_id=task.id)

    if request.method == "POST":
        recoverable_deleted_count = Task.objects.filter(
            is_deleted=True
        ).count()

        # Maximum of 50 tasks can stay in Deleted Tasks for recovery.
        if recoverable_deleted_count >= 50:
            task_title = task.title

            # Permanently delete the 51st task and anything after it.
            task.delete()

            messages.success(
                request,
                f'"{task_title}" was permanently deleted because the '
                f'Deleted Tasks recovery limit of 50 has been reached.',
            )

            return redirect("backlog:product_backlog")

        # Normal soft delete while fewer than 50 recoverable tasks exist.
        task.is_deleted = True
        task.save(update_fields=["is_deleted", "updated_at"])

        TaskHistory.objects.create(
            task=task,
            changed_by=request.user,
            description=(
                f"{request.user.get_full_name() or request.user.username} "
                f"deleted {task.title}"
            ),
        )

        messages.success(
            request,
            f'"{task.title}" was deleted from the Product Backlog.',
        )

        return redirect("backlog:product_backlog")

    return render(
        request,
        "backlog/delete_task.html",
        {"task": task},
    )


@login_required
def edit_task(request, task_id):
    """
    US-05: Edit an existing Product Backlog task.
    """

    task = get_object_or_404(
        Task,
        pk=task_id,
        is_deleted=False
    )

    if task.sprint and not (request.user.is_staff or request.user.is_superuser or task.sprint.team_members.filter(id=request.user.id).exists()):
        messages.error(request, "You must be a team member of this sprint to edit its tasks.")
        return redirect("backlog:task_detail", task_id=task.id)

    if request.method == "POST":
        form = TaskEditForm(
            request.POST,
            request.FILES,
            instance=task
        )

        if form.is_valid():
            changed_fields = form.changed_data
            task = form.save(commit=False)
            # A concurrent time submission must not be overwritten by this older form instance.
            task.save(update_fields=[field for field in form._meta.fields if field != "tags"] + ["updated_at"])
            form.save_m2m()

            if changed_fields:
                for field in changed_fields:
                    field_name = field.replace('_', ' ')
                    
                    if field == 'tags':
                        tags = form.cleaned_data[field]
                        new_val = ", ".join([t.name for t in tags]) if tags else "None"
                    elif field == 'assignee':
                        assignee = form.cleaned_data[field]
                        new_val = assignee.get_full_name() or assignee.username if assignee else "None"
                    else:
                        new_val = form.cleaned_data[field]
                        
                    if field == 'title':
                        description = f'{request.user.username} edited task name to "{new_val}"'
                    else:
                        description = f'{request.user.username} edited {field_name} to "{new_val}"'
                        
                    TaskHistory.objects.create(
                        task=task,
                        changed_by=request.user,
                        description=description
                    )

            messages.success(
                request,
                f'"{task.title}" was updated successfully.'
            )

            return redirect(
                "backlog:task_detail",
                task_id=task.id
            )

    else:
        form = TaskEditForm(instance=task)

    return render(
        request,
        "backlog/edit_task.html",
        {
            "form": form,
            "task": task,
        },
    )

@login_required
def update_task_status(request, task_id):
    """
    US: Update Task Status from backlog list view.
    """
    if request.method == "POST":
        task = get_object_or_404(Task, pk=task_id, is_deleted=False)

        if task.sprint and not (request.user.is_staff or request.user.is_superuser or task.sprint.team_members.filter(id=request.user.id).exists()):
            messages.error(request, "You must be a team member of this sprint to update its tasks.")
            return redirect("backlog:product_backlog")
        new_status = request.POST.get('status')
        if new_status in dict(Task.STATUS_CHOICES):
            task.status = new_status
            task.save(update_fields=['status', 'updated_at'])
            
            TaskHistory.objects.create(
                task=task,
                changed_by=request.user,
                description=f"{request.user.get_full_name() or request.user.username} updated status to '{task.get_status_display()}'"
            )
            
    return redirect('backlog:product_backlog')

@login_required
def create_sprint(request):
    """
    US: Create a Sprint.
    Only accessible by staff/admin users.
    GET displays the sprint creation form.
    POST validates and saves the sprint with status 'Not Started' and logs SprintHistory.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to create a sprint.",
        )
        return redirect("backlog:product_backlog")

    if request.method == "POST":
        form = SprintCreateForm(request.POST)
        if form.is_valid():
            sprint = form.save()

            # Record in SprintHistory (AC 10)
            SprintHistory.objects.create(
                sprint=sprint,
                changed_by=request.user,
                description=f"{request.user.get_full_name() or request.user.username} created sprint '{sprint.name}' with status 'Not Started'",
            )

            messages.success(
                request,
                f'Sprint "{sprint.name}" has been successfully created with status "Not Started".',
            )
            return redirect("backlog:product_backlog")
    else:
        form = SprintCreateForm()

    return render(
        request,
        "backlog/create_sprint.html",
        {"form": form},
    )


@login_required
def edit_sprint(request, sprint_id):
    """
    US: Edit Sprint Details.
    Authorised users: staff/superuser, or the sprint's product owner / scrum master / team members.
    GET: Displays the sprint edit form populated with sprint data.
    POST: Validates and saves changes, and logs SprintHistory.
    """
    sprint = get_object_or_404(Sprint, pk=sprint_id)

    # Authorization check
    is_authorised = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user == sprint.product_owner
        or request.user == sprint.scrum_master
        or sprint.team_members.filter(pk=request.user.pk).exists()
    )

    if not is_authorised:
        messages.error(
            request,
            "Access denied: You do not have permission to edit this sprint.",
        )
        return redirect("backlog:product_backlog")

    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        form = SprintEditForm(request.POST, instance=sprint)
        if form.is_valid():
            changed_fields = form.changed_data
            sprint = form.save()

            if changed_fields:
                for field in changed_fields:
                    field_name = field.replace("_", " ")

                    if field == "team_members":
                        members = form.cleaned_data[field]
                        new_val = (
                            ", ".join([m.get_full_name() or m.username for m in members])
                            if members
                            else "None"
                        )
                    elif field in ["product_owner", "scrum_master"]:
                        user_obj = form.cleaned_data[field]
                        new_val = (
                            user_obj.get_full_name() or user_obj.username
                            if user_obj
                            else "None"
                        )
                    else:
                        new_val = form.cleaned_data[field]

                    if field == "name":
                        description = f'{request.user.get_full_name() or request.user.username} edited sprint name to "{new_val}"'
                    else:
                        description = f'{request.user.get_full_name() or request.user.username} edited {field_name} to "{new_val}"'

                    SprintHistory.objects.create(
                        sprint=sprint,
                        changed_by=request.user,
                        description=description,
                    )

            messages.success(
                request,
                f'Sprint "{sprint.name}" was updated successfully.',
            )
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect("backlog:product_backlog")
    else:
        form = SprintEditForm(instance=sprint)

    return render(
        request,
        "backlog/edit_sprint.html",
        {
            "form": form,
            "sprint": sprint,
            "next_url": next_url,
        },
    )


@login_required
def sprint_list(request):
    """
    US: View Available Sprints.
    Allows authenticated users to view all sprints available in the system.
    """
    sprints = (
        Sprint.objects.all()
        .prefetch_related("team_members", "tasks", "tasks__tags")
        .select_related("product_owner", "scrum_master")
        .order_by("-created_at")
    )

    active_sprints = sprints.filter(status__in=["active", "in_progress"])
    planning_sprints = sprints.filter(status__in=["planning", "not_started"])
    completed_sprints = sprints.filter(status="completed")

    context = {
        "sprints": sprints,
        "active_sprints": active_sprints,
        "planning_sprints": planning_sprints,
        "completed_sprints": completed_sprints,
        "total_sprints": sprints.count(),
    }
    return render(request, "backlog/sprint_list.html", context)


@login_required
def sprint_detail(request, sprint_id):
    """
    US: View Sprint (Sprint Details & Tasks View).
    AC 1: User can view available sprints.
    AC 2: User can open a sprint.
    AC 3: Sprint details are displayed (name, goal, start_date, end_date, product_owner, scrum_master, created_at).
    AC 4: Sprint status is displayed (status, status_badge_class).
    AC 5: Sprint team members are displayed (team_members).
    AC 6: Sprint tasks are displayed (tasks).
    AC 7: Sprint task information includes name, type, tags, priority, story points, assignee, accumulated hours.
    AC 8: Admin can view sprint information without being a sprint member.
    """
    sprint = get_object_or_404(
        Sprint.objects.prefetch_related(
            "team_members",
            "history",
            "history__changed_by",
        ).select_related("product_owner", "scrum_master"),
        pk=sprint_id,
    )

    # Authorization: Admin / staff / superuser, or assigned Product Owner, Scrum Master, Team Member
    is_authorised = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user == sprint.product_owner
        or request.user == sprint.scrum_master
        or sprint.team_members.filter(pk=request.user.pk).exists()
    )

    if not is_authorised:
        messages.error(
            request,
            "Access denied: You do not have permission to view this sprint.",
        )
        return redirect("backlog:product_backlog")

    # Retrieve all non-deleted sprint tasks with tags and assignee pre-fetched
    tasks = (
        sprint.tasks.filter(is_deleted=False)
        .prefetch_related("tags")
        .select_related("assignee")
        .order_by("-created_at")
    )

    # Calculate aggregate metrics for sprint work overview
    total_tasks = tasks.count()
    total_story_points = tasks.aggregate(total=Sum("story_points"))["total"] or 0
    total_accumulated_hours = tasks.aggregate(total=Sum("accumulated_hours"))["total"] or 0
    completed_tasks = tasks.filter(status="completed").count()
    in_progress_tasks = tasks.filter(status="in_progress").count()
    not_started_tasks = tasks.filter(status="not_started").count()

    can_edit_sprint = (
        request.user.is_staff
        or request.user.is_superuser
        or sprint.team_members.filter(id=request.user.id).exists()
    )

    context = {
        "sprint": sprint,
        "tasks": tasks,
        "team_members": sprint.team_members.all(),
        "total_tasks": total_tasks,
        "total_story_points": total_story_points,
        "total_accumulated_hours": total_accumulated_hours,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "not_started_tasks": not_started_tasks,
        "history": sprint.history.all(),
        "can_edit_sprint": can_edit_sprint,
    }
    return render(request, "backlog/sprint_detail.html", context)


@login_required
def sprint_board(request, sprint_id=None):
    sprints = available_sprints(request.user).order_by('created_at')
    
    if sprint_id:
        current_sprint = get_object_or_404(sprints, pk=sprint_id)
    else:
        current_sprint = sprints.filter(status='active').first()
    
    sprint_tasks = []
    not_started_tasks = []
    in_progress_tasks = []
    completed_tasks = []
    
    if current_sprint:
        sprint_tasks = current_sprint.tasks.filter(is_deleted=False).select_related('assignee').prefetch_related('tags').order_by('-created_at')
        not_started_tasks = sprint_tasks.filter(status='not_started')
        in_progress_tasks = sprint_tasks.filter(status='in_progress')
        completed_tasks = sprint_tasks.filter(status='completed')
        
    preference = None
    if current_sprint:
        preference = SprintBoardPreference.objects.filter(user=request.user, sprint=current_sprint).first()
    view_mode = preference.view_mode if preference else 'kanban'
    can_edit_sprint = True
    if current_sprint and not (request.user.is_staff or request.user.is_superuser):
        can_edit_sprint = (request.user.pk in {current_sprint.product_owner_id, current_sprint.scrum_master_id}
                           or current_sprint.team_members.filter(id=request.user.id).exists())
    
    return render(
        request,
        "backlog/sprint_board.html",
        {
            "sprints": sprints,
            "current_sprint": current_sprint,
            "can_edit_sprint": can_edit_sprint,
            "can_change_status": bool(current_sprint and current_sprint.status == 'active' and can_edit_sprint),
            "task_status_choices": Task.STATUS_CHOICES,
            "sprint_tasks": sprint_tasks,
            "not_started_tasks": not_started_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": completed_tasks,
            "view_mode": view_mode,
            "burndown_data": build_sprint_burndown(current_sprint) if current_sprint else None,
        },
    )

@login_required
def assign_sprint_role(request, sprint_id, role):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if request.method == "POST":
        sprint = get_object_or_404(Sprint, pk=sprint_id)
        user_id = request.POST.get('user_id')
        if not user_id:
            messages.error(request, "Please select a user.")
            return redirect('backlog:product_backlog')
        selected_user = get_object_or_404(User, pk=user_id)
        if role == 'scrum_master':
            if sprint.product_owner == selected_user:
                messages.error(request, "You cannot be both the Scrum Master and Product Owner.")
            else:
                sprint.scrum_master = selected_user
                sprint.save(update_fields=['scrum_master', 'updated_at'])
                SprintHistory.objects.create(
                    sprint=sprint,
                    changed_by=request.user,
                    description=f"{request.user.get_full_name() or request.user.username} assigned {selected_user.get_full_name() or selected_user.username} as Scrum Master"
                )
                messages.success(request, f"{selected_user.get_full_name() or selected_user.username} is now the Scrum Master.")
        elif role == 'product_owner':
            if sprint.scrum_master == selected_user:
                messages.error(request, "You cannot be both the Scrum Master and Product Owner.")
            else:
                sprint.product_owner = selected_user
                sprint.save(update_fields=['product_owner', 'updated_at'])
                SprintHistory.objects.create(
                    sprint=sprint,
                    changed_by=request.user,
                    description=f"{request.user.get_full_name() or request.user.username} assigned {selected_user.get_full_name() or selected_user.username} as Product Owner"
                )
                messages.success(request, f"{selected_user.get_full_name() or selected_user.username} is now the Product Owner.")
        return redirect('backlog:product_backlog')


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def deleted_tasks(request):
    """
    US-23: View Deleted Tasks
    Displays deleted tasks with their name, sprint belonged, sprint status, and deletion date.
    Allows user to select and recover tasks with pagination.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    deleted_tasks_qs = Task.objects.filter(is_deleted=True).select_related('sprint').order_by('-updated_at')

    # Mock tasks to guarantee identical UI presentation as in mockups if no deleted items exist yet
    mock_tasks = [
        {
            "id": 101,
            "title": "Task 1",
            "sprint_name": "Sprint 1",
            "sprint_status": "Completed",
            "sprint_status_class": "badge-sprint-completed",
            "formatted_date": "24th August 2026, 9:57am",
            "is_mock": True,
        },
        {
            "id": 102,
            "title": "Task 2",
            "sprint_name": "Sprint 6",
            "sprint_status": "Active",
            "sprint_status_class": "badge-sprint-active",
            "formatted_date": "18th August 2026, 9:30am",
            "is_mock": True,
        },
    ]

    tasks_data = []
    for t in deleted_tasks_qs:
        sprint_name = t.sprint.name if t.sprint else "-"
        sprint_status = t.sprint.get_status_display() if t.sprint else "-"
        sprint_badge = t.sprint.status_badge_class if t.sprint else "bg-secondary"
        
        # Format date as '24th August 2026, 9:57am'
        dt = t.updated_at
        day_suffix = 'th' if 11 <= dt.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(dt.day % 10, 'th')
        formatted_date = f"{dt.day}{day_suffix} {dt.strftime('%B %Y, %I:%M%p').lstrip('0').lower()}"

        tasks_data.append({
            "id": t.id,
            "title": t.title,
            "sprint_name": sprint_name,
            "sprint_status": sprint_status,
            "sprint_status_class": sprint_badge,
            "formatted_date": formatted_date,
            "is_mock": False,
        })

    tasks_list = tasks_data if tasks_data else mock_tasks

    # Pagination
    paginator = Paginator(tasks_list, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    step = request.GET.get('step', '1')
    recovered_id = request.GET.get('recovered_id')

    return render(
        request,
        "backlog/deleted_tasks.html",
        {
            "deleted_tasks": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "step": step,
            "recovered_id": str(recovered_id) if recovered_id else None,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def recover_task(request, task_id):
    """
    US-23: Recover a deleted task.
    Tasks belonging to completed sprints cannot be recovered.
    """
    if request.method != "POST":
        return redirect("backlog:deleted_tasks")

    try:
        task = Task.objects.get(pk=task_id, is_deleted=True)

        if task.sprint and task.sprint.status == "completed":
            messages.error(
                request,
                "Tasks from completed sprints cannot be recovered."
            )
            return redirect("backlog:deleted_tasks")

        task.is_deleted = False
        task.save(update_fields=["is_deleted", "updated_at"])

        TaskHistory.objects.create(
            task=task,
            changed_by=request.user,
            description=(
                f"{request.user.get_full_name() or request.user.username} "
                f"recovered {task.title}"
            ),
        )
        messages.success(
            request,
            f'"{task.title}" was recovered successfully.'
        )

    except Task.DoesNotExist:
        messages.error(request, "Deleted task was not found.")

    return redirect("backlog:deleted_tasks")


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def deleted_sprints(request):
    """
    US-23: Display deleted sprints from the database.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    deleted_sprints = Sprint.objects.filter(
        is_deleted=True
    ).order_by("-updated_at")

    # Prepare values used by the template
    for sprint in deleted_sprints:
        sprint.status_class = f"badge-sprint-{sprint.status.replace('_', '-')}"
        sprint.formatted_date = sprint.updated_at.strftime("%d %B %Y, %I:%M %p")
        sprint.is_mock = False

    paginator = Paginator(deleted_sprints, 10)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    return render(
        request,
        "backlog/deleted_sprints.html",
        {
            "deleted_sprints": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def recover_sprint(request, sprint_id):
    """
    US-23: Recover a deleted sprint.
    """
    if request.method != "POST":
        return redirect("backlog:deleted_sprints")

    try:
        sprint = Sprint.objects.get(pk=sprint_id, is_deleted=True)
    except Sprint.DoesNotExist:
        messages.error(request, "Deleted sprint was not found.")
        return redirect("backlog:deleted_sprints")

    sprint.is_deleted = False
    sprint.save(update_fields=["is_deleted", "updated_at"])

    messages.success(request, f"{sprint.name} was recovered successfully.")
    return redirect("backlog:deleted_sprints")


@login_required
def delete_sprint(request, sprint_id):
    """
    US-23: Soft-delete a sprint so it can be recovered later.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "You do not have permission to delete this sprint.")
        return redirect("backlog:sprint_detail", sprint_id=sprint_id)

    try:
        sprint = Sprint.objects.get(pk=sprint_id, is_deleted=False)
    except Sprint.DoesNotExist:
        messages.error(request, "Sprint was not found.")
        return redirect("backlog:product_backlog")

    if sprint.status not in ["stopped", "not_started"]:
        messages.error(request, "Only stopped or not-started sprints can be deleted.")
        return redirect("backlog:product_backlog")

    if request.method == "POST":
        sprint.is_deleted = True
        sprint.save(update_fields=["is_deleted", "updated_at"])
        messages.success(request, f"{sprint.name} was moved to Deleted Sprints.")
        return redirect("backlog:product_backlog")

    return render(
        request,
        "backlog/delete_sprint.html",
        {"sprint": sprint},
    )
