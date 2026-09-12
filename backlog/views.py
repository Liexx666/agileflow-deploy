from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import TaskCreateForm, TaskEditForm
from django.db.models import Sum, Q, Case, When, Value, IntegerField
from .models import Task, Tag, Sprint, TaskHistory


@login_required
def product_backlog(request):
    """
    US-03: View Product Backlog (List View)
    Displays all active product backlog tasks with the Sprints sidebar,
    tag filtering, and priority/date sorting.
    """
    # Base queries
    tasks = Task.objects.filter(is_deleted=False).prefetch_related('tags', 'assignee', 'sprint')
    sprints = Sprint.objects.all().order_by('created_at')

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
    all_active_tasks = Task.objects.filter(is_deleted=False)
    total_items = all_active_tasks.count()
    total_points = all_active_tasks.aggregate(total=Sum('story_points'))['total'] or 0
    story_count = all_active_tasks.filter(item_type='story').count()
    bug_count = all_active_tasks.filter(item_type='bug').count()

    all_tags = Tag.objects.all()

    context = {
        'tasks': tasks,
        'sprints': sprints,
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

            return redirect("backlog:product_backlog")
    else:
        form = TaskCreateForm()

    return render(
        request,
        "backlog/create_task.html",
        {"form": form},
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

    history = task.history.all()

    return render(
        request,
        "backlog/task_detail.html",
        {
            "task": task,
            "history": history,
        },
    )


@login_required
def delete_task(request, task_id):
    """
    US-06: Delete a Product Backlog task.

    GET displays a confirmation page.
    POST soft-deletes the task by setting is_deleted=True.
    """
    task = get_object_or_404(Task, pk=task_id, is_deleted=False)

    if task.status == 'completed':
        messages.error(request, f'"{task.title}" cannot be deleted because it is already completed.')
        return redirect("backlog:task_detail", task_id=task.id)

    if request.method == "POST":
        task.is_deleted = True
        task.save(update_fields=["is_deleted", "updated_at"])

        TaskHistory.objects.create(
            task=task,
            changed_by=request.user,
            description=f"{request.user.get_full_name() or request.user.username} deleted {task.title}",
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

    if request.method == "POST":
        form = TaskEditForm(
            request.POST,
            request.FILES,
            instance=task
        )

        if form.is_valid():
            changed_fields = form.changed_data
            task = form.save()

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

