from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from .burndown import build_sprint_burndown

from .models import (
    Sprint,
    SprintBoardPreference,
    Task,
    TaskWorkSession,
)

from .sprint_forms import (
    MoveTaskForm,
    SprintBoardViewForm,
    SprintStatusForm,
    SprintTaskStatusForm,
    WorkSessionForm,
)

from .sprint_services import (
    auto_update_sprint_statuses,
    change_sprint_status,
    change_sprint_task_status,
    move_task,
    save_board_preference,
    save_work_session,
)


def _form_errors(form):
    return {
        field: [
            error['message']
            for error in errors.get_json_data()
        ]
        for field, errors in form.errors.items()
    }


@login_required
@require_POST
def record_task_time(request, task_id):
    return _save_task_time(request, task_id)


@login_required
@require_POST
def edit_task_time(request, task_id, session_id):
    """US-20: Edit only the logged-in member's own time entry."""
    return _save_task_time(request, task_id, session_id)


def _save_task_time(request, task_id, session_id=None):
    from .views import render_task_detail

    task = get_object_or_404(Task.objects.select_related("sprint"), pk=task_id, is_deleted=False)
    editing_session = None
    if session_id is not None:
        editing_session = get_object_or_404(TaskWorkSession, pk=session_id, task=task, user=request.user)
    is_edit = session_id is not None
    form = WorkSessionForm(request.POST, auto_id="edit_%s" if is_edit else "record_%s")
    status = 400
    if form.is_valid():
        try:
            save_work_session(
                task_id=task.pk, user=request.user, session_id=session_id,
                started_at=form.cleaned_data["started_at"], ended_at=form.cleaned_data["ended_at"],
            )
        except (Task.DoesNotExist, TaskWorkSession.DoesNotExist):
            # A task/entry may disappear between initial lookup and the transaction.
            from django.http import Http404
            raise Http404("The task or work session no longer exists.")
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Work session updated." if is_edit else "Work session recorded.")
            return redirect("backlog:task_detail", task_id=task.pk)
    task.refresh_from_db()
    return render_task_detail(
        request, task, editing_session=editing_session,
        open_time_modal="editTimeModal" if is_edit else "recordTimeModal", status=status,
        **({"edit_time_form": form} if is_edit else {"time_form": form}),
    )


def _validation_errors(error):
    if hasattr(error, 'message_dict'):
        return error.message_dict

    return {
        'non_field_errors': error.messages
    }


def _task_payload(task):
    return {
        'id': task.pk,
        'title': task.title,
        'item_type': task.item_type,
        'story_points': task.story_points,
        'priority': task.priority,
        'stage': task.stage,
        'status': task.status,
        'status_label': task.get_status_display(),
        'sprint_id': task.sprint_id,
        'accumulated_hours': str(task.accumulated_hours),
        'assignee': (
            task.assignee.get_full_name()
            or task.assignee.username
            if task.assignee
            else None
        ),
        'tags': list(
            task.tags.values_list(
                'name',
                flat=True,
            )
        ),
    }


@login_required
@require_POST
def move_task_endpoint(request, task_id):
    """
    US-15: Move a task into an active Sprint or back
    to the Product Backlog.
    """

    form = MoveTaskForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {
                'ok': False,
                'errors': _form_errors(form),
            },
            status=400,
        )

    try:
        task, changed, extra = move_task(
            task_id=task_id,
            sprint_id=form.cleaned_data['sprint_id'],
            assignee_action=form.cleaned_data.get('assignee_action'),
            new_assignee_id=form.cleaned_data.get('new_assignee_id'),
            changed_by=request.user,
        )
        if extra and extra.get('needs_assignee_decision'):
            return JsonResponse(
                {
                    'ok': False,
                    'needs_assignee_decision': True,
                    'assignee_id': extra['assignee_id'],
                    'assignee_name': extra['assignee_name'],
                    'sprint_name': extra['sprint_name'],
                    'sprint_id': form.cleaned_data['sprint_id'],
                    'task_id': task_id,
                    'sprint_members': extra.get('sprint_members', []),
                }
            )
    except Task.DoesNotExist:
        return JsonResponse(
            {
                'ok': False,
                'errors': {
                    'task': [
                        'The selected task does not exist.'
                    ]
                },
            },
            status=404,
        )
    except ValidationError as error:
        return JsonResponse(
            {
                'ok': False,
                'errors': _validation_errors(error),
            },
            status=409,
        )

    task = (
        Task.objects
        .select_related(
            'assignee',
            'sprint',
        )
        .prefetch_related('tags')
        .get(pk=task.pk)
    )

    return JsonResponse(
        {
            'ok': True,
            'changed': changed,
            'task': _task_payload(task),
        }
    )


@login_required
@require_POST
def sprint_task_status_endpoint(request, task_id):
    """
    US-16: Change a task's status inside an active Sprint.
    """

    form = SprintTaskStatusForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {
                'ok': False,
                'errors': _form_errors(form),
            },
            status=400,
        )

    try:
        task, changed = change_sprint_task_status(
            task_id=task_id,
            status=form.cleaned_data['status'],
            changed_by=request.user,
        )
    except Task.DoesNotExist:
        return JsonResponse(
            {
                'ok': False,
                'errors': {
                    'task': [
                        'The selected task does not exist.'
                    ]
                },
            },
            status=404,
        )
    except ValidationError as error:
        return JsonResponse(
            {
                'ok': False,
                'errors': _validation_errors(error),
            },
            status=409,
        )

    task = (
        Task.objects
        .select_related(
            'assignee',
            'sprint',
        )
        .prefetch_related('tags')
        .get(pk=task.pk)
    )

    burndown = (
        build_sprint_burndown(task.sprint)
        if task.sprint
        else None
    )

    return JsonResponse(
        {
            'ok': True,
            'changed': changed,
            'task': _task_payload(task),
            'burndown': burndown,
        }
    )


@login_required
@require_GET
def sprint_board_data(request, sprint_id):
    """
    US-15, US-16 and US-17:
    Supply the data required to display a Sprint board.
    """

    auto_update_sprint_statuses()
    sprint = get_object_or_404(
        Sprint,
        pk=sprint_id,
    )

    preference = (
        SprintBoardPreference.objects.filter(
            user=request.user,
            sprint=sprint,
        )
        .first()
    )

    view_mode = (
        preference.view_mode
        if preference
        else SprintBoardPreference.VIEW_KANBAN
    )

    tasks = (
        sprint.tasks
        .filter(is_deleted=False)
        .select_related(
            'assignee',
            'sprint',
        )
        .prefetch_related('tags')
        .order_by(
            'status',
            '-priority',
            'title',
        )
    )

    task_payloads = [
        _task_payload(task)
        for task in tasks
    ]

    grouped_tasks = {
        status: [
            task
            for task in task_payloads
            if task['status'] == status
        ]
        for status, _ in Task.STATUS_CHOICES
    }

    return JsonResponse(
        {
            'ok': True,
            'sprint': {
                'id': sprint.pk,
                'name': sprint.name,
                'goal': sprint.goal,
                'status': sprint.status,
                'status_label': (
                    sprint.get_status_display()
                ),
                'start_date': (
                    sprint.start_date.isoformat()
                    if sprint.start_date
                    else None
                ),
                'end_date': (
                    sprint.end_date.isoformat()
                    if sprint.end_date
                    else None
                ),
            },
            'view_mode': view_mode,
            'tasks': task_payloads,
            'tasks_by_status': grouped_tasks,
        }
    )


@login_required
@require_GET
def sprint_burndown_data(request, sprint_id):
    sprint = get_object_or_404(Sprint, pk=sprint_id)
    return JsonResponse({"ok": True, "burndown": build_sprint_burndown(sprint)})


@login_required
@require_POST
def sprint_board_view_endpoint(request, sprint_id):
    """
    US-17: Save the user's Kanban/List preference.
    """

    form = SprintBoardViewForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {
                'ok': False,
                'errors': _form_errors(form),
            },
            status=400,
        )

    try:
        preference = save_board_preference(
            user=request.user,
            sprint_id=sprint_id,
            view_mode=form.cleaned_data['view_mode'],
        )
    except ValidationError as error:
        return JsonResponse(
            {
                'ok': False,
                'errors': _validation_errors(error),
            },
            status=404,
        )

    return JsonResponse(
        {
            'ok': True,
            'view_mode': preference.view_mode,
        }
    )


@login_required
@require_POST
def sprint_status_endpoint(request, sprint_id):
    """
    US-18: Update Sprint status while allowing only one
    active Sprint.
    """

    form = SprintStatusForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {
                'ok': False,
                'errors': _form_errors(form),
            },
            status=400,
        )

    try:
        sprint, changed = change_sprint_status(
            sprint_id=sprint_id,
            status=form.cleaned_data['status'],
            changed_by=request.user,
        )
    except ValidationError as error:
        return JsonResponse(
            {
                'ok': False,
                'errors': _validation_errors(error),
            },
            status=409,
        )

    return JsonResponse(
        {
            'ok': True,
            'changed': changed,
            'sprint': {
                'id': sprint.pk,
                'status': sprint.status,
                'status_label': (
                    sprint.get_status_display()
                ),
                'end_date': (
                    sprint.end_date.isoformat() if sprint.end_date else None
                ),
            },
        }
    )
