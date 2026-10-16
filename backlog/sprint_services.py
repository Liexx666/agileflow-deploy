from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import DurationField, ExpressionWrapper, F, Sum
from django.utils import timezone

from .models import (
    Sprint,
    SprintBoardPreference,
    SprintHistory,
    Task,
    TaskHistory,
    TaskWorkSession,
)


def check_sprint_permission(sprint, user):
    """
    Raises ValidationError if the user is not an admin, product owner, scrum master, or member of the sprint.
    """
    if sprint is None:
        return
    if user.is_staff or user.is_superuser:
        return
    if (
        sprint.product_owner == user
        or sprint.scrum_master == user
        or sprint.team_members.filter(id=user.id).exists()
    ):
        return
    raise ValidationError({'sprint_id': 'You must be assigned to this sprint to modify its tasks or settings.'})


@transaction.atomic
def move_task(*, task_id, sprint_id, changed_by, assignee_action=None, new_assignee_id=None):
    """
    Move a task into an active Sprint or return it to the
    Product Backlog.
    If the task has an assignee who is not part of the target sprint team,
    prompt for decision, add to sprint team, or clear assignee / choose from sprint team members.
    """

    task = (
        Task.objects.select_for_update()
        .get(
            pk=task_id,
            is_deleted=False,
        )
    )

    old_sprint = task.sprint
    target_sprint = None

    if sprint_id is not None:
        try:
            target_sprint = (
                Sprint.objects.select_for_update()
                .get(pk=sprint_id, is_deleted=False)
            )
        except Sprint.DoesNotExist as error:
            raise ValidationError(
                {
                    'sprint_id': (
                        'The selected Sprint does not exist.'
                    )
                }
            ) from error

    if task.status == 'completed':
        raise ValidationError(
            {
                'task': (
                    'A completed task cannot be moved.'
                )
            }
        )

    if target_sprint is not None:
        if target_sprint.status in ['stopped', 'cancelled', 'completed']:
            status_display = 'Cancelled' if target_sprint.status in ['stopped', 'cancelled'] else 'Completed'
            raise ValidationError(
                {
                    'sprint_id': (
                        f'Tasks cannot be moved into a {status_display} Sprint.'
                    )
                }
            )
        check_sprint_permission(target_sprint, changed_by)

    if old_sprint:
        if old_sprint.status in ['completed', 'stopped', 'cancelled']:
            status_display = 'Cancelled' if old_sprint.status in ['stopped', 'cancelled'] else 'Completed'
            raise ValidationError(
                {
                    'task': (
                        f'Tasks cannot be moved out of a {status_display} Sprint.'
                    )
                }
            )
        check_sprint_permission(old_sprint, changed_by)

    if old_sprint == target_sprint:
        return task, False, None

    # Check if task assignee is inside the target sprint team
    extra_history_notes = []
    if target_sprint is not None and task.assignee is not None:
        is_member = (
            target_sprint.team_members.filter(id=task.assignee.id).exists()
            or target_sprint.product_owner == task.assignee
            or target_sprint.scrum_master == task.assignee
        )
        if not is_member:
            if not assignee_action:
                sprint_members = [
                    {
                        'id': m.id,
                        'name': m.get_full_name() or m.username,
                        'username': m.username,
                    }
                    for m in target_sprint.team_members.all().order_by('first_name', 'last_name', 'username')
                ]
                return task, False, {
                    'needs_assignee_decision': True,
                    'assignee_id': task.assignee.id,
                    'assignee_name': task.assignee.get_full_name() or task.assignee.username,
                    'sprint_id': target_sprint.id,
                    'sprint_name': target_sprint.name,
                    'sprint_members': sprint_members,
                }
            elif assignee_action == 'add_to_sprint':
                target_sprint.team_members.add(task.assignee)
                assignee_name = task.assignee.get_full_name() or task.assignee.username
                actor = changed_by.get_full_name() or changed_by.username
                SprintHistory.objects.create(
                    sprint=target_sprint,
                    changed_by=changed_by,
                    description=f"{actor} added {assignee_name} to sprint team members",
                )
                extra_history_notes.append(f"added {assignee_name} to sprint team")
            elif assignee_action in ['remove_assignee', 'reassign', 'clear']:
                old_assignee_name = task.assignee.get_full_name() or task.assignee.username
                if new_assignee_id:
                    try:
                        new_assignee = target_sprint.team_members.get(id=new_assignee_id)
                        if new_assignee.is_staff or new_assignee.is_superuser:
                            raise ValidationError({'assignee': 'Sprint tasks cannot be assigned to an administrator.'})
                        task.assignee = new_assignee
                        new_name = new_assignee.get_full_name() or new_assignee.username
                        extra_history_notes.append(f"removed {old_assignee_name} and assigned to {new_name}")
                    except target_sprint.team_members.model.DoesNotExist:
                        raise ValidationError({'assignee': 'The selected assignee is not a member of this sprint.'})
                else:
                    task.assignee = None
                    extra_history_notes.append(f"cleared assignee {old_assignee_name}")

    task.sprint = target_sprint
    
    update_fields = ['sprint', 'updated_at', 'assignee']

    if target_sprint is not None:
        task.status = 'not_started'
        update_fields.append('status')

    task.save(update_fields=list(set(update_fields)))

    old_location = (
        old_sprint.name
        if old_sprint
        else 'Product Backlog'
    )

    new_location = (
        target_sprint.name
        if target_sprint
        else 'Product Backlog'
    )

    actor = (
        changed_by.get_full_name()
        or changed_by.username
    )

    description = (
        f'{actor} moved {task.title} '
        f'from {old_location} to {new_location}'
    )
    if target_sprint is not None:
        description += ' and status was set to "Not Started"'
    if extra_history_notes:
        description += f' ({", ".join(extra_history_notes)})'

    TaskHistory.objects.create(
        task=task,
        changed_by=changed_by,
        description=description,
    )

    return task, True, None


@transaction.atomic
def change_sprint_task_status(
    *,
    task_id,
    status,
    changed_by,
):
    """
    Change the workflow status of a task belonging to an
    active Sprint.
    """

    task = (
        Task.objects.select_for_update()
        .get(
            pk=task_id,
            is_deleted=False,
        )
    )

    if task.sprint is None:
        raise ValidationError(
            {
                'task': (
                    'Only tasks assigned to a Sprint have '
                    'a Sprint task status.'
                )
            }
        )

    if task.sprint.status in ['completed', 'stopped', 'cancelled']:
        status_display = 'cancelled' if task.sprint.status in ['stopped', 'cancelled'] else 'completed'
        raise ValidationError(
            {
                'task': (
                    f'Task status cannot be changed in a {status_display} Sprint.'
                )
            }
        )

    if task.sprint.status != 'active':
        raise ValidationError(
            {
                'task': (
                    'Task status can only be changed in '
                    'an active Sprint.'
                )
            }
        )

    if task.status == 'completed' and status != 'completed':
        raise ValidationError(
            {
                'task': (
                    'A completed task cannot change its status.'
                )
            }
        )

    check_sprint_permission(task.sprint, changed_by)

    valid_statuses = {
        choice[0]
        for choice in Task.STATUS_CHOICES
    }

    if status not in valid_statuses:
        raise ValidationError(
            {
                'status': 'Select a valid task status.'
            }
        )

    if task.status == status:
        return task, False

    old_status = task.get_status_display()

    task.status = status

    task.save(
        update_fields=[
            'status',
            'updated_at',
        ]
    )

    new_status = task.get_status_display()

    actor = (
        changed_by.get_full_name()
        or changed_by.username
    )

    TaskHistory.objects.create(
        task=task,
        changed_by=changed_by,
        description=(
            f'{actor} changed {task.title} status '
            f'from {old_status} to {new_status}'
        ),
    )

    return task, True


@transaction.atomic
def save_board_preference(
    *,
    user,
    sprint_id,
    view_mode,
):
    """
    Store the selected Kanban/List layout for one user and Sprint.
    """

    try:
        sprint = Sprint.objects.get(pk=sprint_id)
    except Sprint.DoesNotExist as error:
        raise ValidationError(
            {
                'sprint': (
                    'The selected Sprint does not exist.'
                )
            }
        ) from error

    valid_modes = {
        choice[0]
        for choice in SprintBoardPreference.VIEW_CHOICES
    }

    if view_mode not in valid_modes:
        raise ValidationError(
            {
                'view_mode': (
                    'Select either Kanban or List view.'
                )
            }
        )

    preference, _ = (
        SprintBoardPreference.objects.update_or_create(
            user=user,
            sprint=sprint,
            defaults={
                'view_mode': view_mode,
            },
        )
    )

    return preference


@transaction.atomic
def change_sprint_status(*, sprint_id, status, changed_by=None):
    """
    Update Sprint status while enforcing the single-active-Sprint rule.
    """

    try:
        sprint = (
            Sprint.objects.select_for_update()
            .get(pk=sprint_id)
        )
    except Sprint.DoesNotExist as error:
        raise ValidationError(
            {
                'sprint': (
                    'The selected Sprint does not exist.'
                )
            }
        ) from error

    valid_statuses = {
        choice[0]
        for choice in Sprint.STATUS_CHOICES
    }

    if status not in valid_statuses:
        raise ValidationError(
            {
                'status': 'Select a valid Sprint status.'
            }
        )

    if status == 'cancelled':
        status = 'stopped'

    current_status = 'stopped' if sprint.status == 'cancelled' else sprint.status
    if current_status == status:
        return sprint, False

    if status == 'stopped' and current_status != 'active':
        raise ValidationError(
            {
                'status': 'Only active sprints can be cancelled.'
            }
        )

    # AC: A completed or cancelled sprint cannot be changed anymore
    if current_status in ['completed', 'stopped']:
        status_display = 'cancelled' if current_status == 'stopped' else 'completed'
        raise ValidationError(
            {
                'status': f'A {status_display} Sprint cannot be changed anymore.'
            }
        )

    # AC: Once a sprint is started, it cannot be changed back to not started or planning
    if current_status in ['active', 'stopped', 'completed'] and status in ['not_started', 'planning']:
        raise ValidationError(
            {
                'status': 'A started sprint cannot be changed back to not started or planning.'
            }
        )

    if status == 'active':
        another_active_sprint = (
            Sprint.objects.select_for_update()
            .exclude(pk=sprint.pk)
            .filter(status='active')
            .exists()
        )

        if another_active_sprint:
            raise ValidationError(
                {
                    'status': (
                        'Another Sprint is already active. '
                        'Complete it first.'
                    )
                }
            )

    sprint.status = status
    if changed_by is not None:
        sprint._changed_by = changed_by
    update_fields = ['status']

    # AC: If by manual the sprint is set to cancelled or completed, change end date to current date
    if status in ['stopped', 'completed']:
        today = timezone.localdate()
        sprint.end_date = today
        update_fields.append('end_date')
        if sprint.start_date and sprint.start_date > today:
            sprint.start_date = today
            update_fields.append('start_date')

    try:
        sprint.save(
            update_fields=update_fields
        )
    except IntegrityError as error:
        raise ValidationError(
            {
                'status': (
                    'Another Sprint is already active. '
                    'Complete it first.'
                )
            }
        ) from error

    return sprint, True


def work_time_unavailable_reason(task, user, *, editing=False):
    """Shared by the UI and service; hiding a button alone is not authorization."""
    if task.is_deleted or not task.sprint_id:
        return "Time can only be recorded for a Sprint task."
    if task.sprint.status != "active":
        return "Time can only be recorded in an active Sprint."
    if task.status == "completed":
        return "Completed tasks cannot receive new or edited time entries."
    if not task.sprint.team_members.filter(pk=user.pk).exists():
        return "Only a Sprint team member can record or edit time."
    if not editing and task.assignee_id != user.pk:
        return "Only a Sprint member assigned to this task can record time."
    return ""


def _work_session_total(task):
    interval = ExpressionWrapper(F("ended_at") - F("started_at"), output_field=DurationField())
    return task.work_sessions.aggregate(total=Sum(interval))["total"] or timedelta()


def _duration_hours(duration):
    return (Decimal(str(duration.total_seconds())) / Decimal("3600")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP,
    )


@transaction.atomic
def save_work_session(*, task_id, user, started_at, ended_at, session_id=None):
    """Validate and save a work interval together with the task's accumulated total."""
    # Serialize this user's writes across ALL tasks, including when no entry exists yet.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    task = Task.objects.select_for_update().get(pk=task_id, is_deleted=False)
    if task.sprint_id:
        # Re-read/lock the Sprint so a concurrent status change cannot bypass validation.
        task.sprint = Sprint.objects.select_for_update().get(pk=task.sprint_id)
    is_edit = session_id is not None
    reason = work_time_unavailable_reason(task, user, editing=is_edit)
    if reason:
        if task.sprint_id and not is_edit and task.assignee_id != user.pk:
            raise PermissionDenied(reason)
        if task.sprint_id and not task.sprint.team_members.filter(pk=user.pk).exists():
            raise PermissionDenied(reason)
        raise ValidationError(reason)
    if ended_at <= started_at:
        raise ValidationError("End date and time must be after start date and time.")

    entry = TaskWorkSession(task=task, user=user)
    previous_duration = timedelta()
    previous_interval = None
    if is_edit:
        # Scope edits to both the requested task and the authenticated owner.
        entry = TaskWorkSession.objects.select_for_update().get(
            pk=session_id, task=task, user=user,
        )
        previous_duration = entry.duration
        if entry.started_at == started_at and entry.ended_at == ended_at:
            return entry  # No actual change: do not create a misleading history entry.
        previous_interval = _work_session_interval_label(entry)

    overlaps = TaskWorkSession.objects.filter(
        user=user, started_at__lt=ended_at, ended_at__gt=started_at,
    )
    if entry.pk:
        overlaps = overlaps.exclude(pk=entry.pk)
    if overlaps.exists():
        raise ValidationError("This interval overlaps another of your work sessions (including on other tasks).")

    previous_total = _work_session_total(task)
    # Preserve legacy aggregate hours, whose individual timestamps are unavailable.
    legacy_hours = task.accumulated_hours - _duration_hours(previous_total)
    new_duration = ended_at - started_at
    total_hours = legacy_hours + _duration_hours(previous_total - previous_duration + new_duration)
    if total_hours > Decimal("9999.99"):
        raise ValidationError("Total task time cannot exceed 9999.99 hours.")

    entry.started_at = started_at
    entry.ended_at = ended_at
    entry.save()
    task.accumulated_hours = total_hours
    task.save(update_fields=["accumulated_hours", "updated_at"])
    if is_edit:
        # Commit the timestamps, accumulated total and audit history together (US-20).
        TaskHistory.objects.create(
            task=task,
            changed_by=user,
            is_time_entry_change=True,
            description=(
                f"Edited work session #{entry.pk}: {previous_interval} to "
                f"{_work_session_interval_label(entry)} "
                f"({timezone.get_current_timezone_name()})."
            ),
        )
    return entry


def _work_session_interval_label(entry):
    start = timezone.localtime(entry.started_at).strftime("%Y-%m-%d %H:%M")
    end = timezone.localtime(entry.ended_at).strftime("%Y-%m-%d %H:%M")
    return f"{start} - {end} ({entry.duration_label})"


def check_sprint_date_overlap(start_date, end_date, exclude_sprint_id=None):
    """
    Check if a given date range overlaps with any existing non-deleted sprint.
    Two date ranges [S1, E1] and [S2, E2] overlap if S1 <= E2 and E1 >= S2.
    Returns the first conflicting Sprint instance or None.
    """
    if not start_date or not end_date:
        return None

    qs = Sprint.objects.filter(
        is_deleted=False,
        start_date__isnull=False,
        end_date__isnull=False,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_sprint_id:
        qs = qs.exclude(pk=exclude_sprint_id)

    return qs.first()


def auto_update_sprint_statuses(reference_date=None):
    """
    Automatically updates sprint statuses based on dates:
    1. Active sprints whose end date has arrived (today >= end_date) are completed.
    2. Not started / planning sprints whose start date has arrived (today >= start_date)
       are automatically started (or completed if today >= end_date as well),
       respecting the single-active-sprint constraint.
    """
    today = reference_date or timezone.localdate()
    updated_sprints = []

    # Step 1: Auto-complete active sprints whose end date has arrived
    active_to_complete = list(
        Sprint.objects.filter(
            is_deleted=False,
            status='active',
            end_date__isnull=False,
            end_date__lte=today,
        )
    )
    for sprint in active_to_complete:
        sprint.status = 'completed'
        sprint.save(update_fields=['status'])
        SprintHistory.objects.create(
            sprint=sprint,
            changed_by=None,
            description=f"Sprint automatically completed on end date {sprint.end_date}.",
        )
        updated_sprints.append(sprint)

    # Step 2: Auto-start unstarted sprints whose start date has arrived
    has_active = Sprint.objects.filter(is_deleted=False, status='active').exists()

    candidates = list(
        Sprint.objects.filter(
            is_deleted=False,
            status__in=['not_started', 'planning'],
            start_date__isnull=False,
            start_date__lte=today,
        ).order_by('start_date', 'id')
    )

    for sprint in candidates:
        if sprint.end_date and sprint.end_date <= today:
            sprint.status = 'completed'
            sprint.save(update_fields=['status'])
            SprintHistory.objects.create(
                sprint=sprint,
                changed_by=None,
                description=f"Sprint automatically completed on end date {sprint.end_date}.",
            )
            updated_sprints.append(sprint)
        elif not has_active:
            sprint.status = 'active'
            sprint.save(update_fields=['status'])
            SprintHistory.objects.create(
                sprint=sprint,
                changed_by=None,
                description=f"Sprint automatically started on start date {sprint.start_date}.",
            )
            updated_sprints.append(sprint)
            has_active = True

    # Step 3: Ensure no incomplete tasks remain in stopped or completed sprints
    inactive_sprints = Sprint.objects.filter(is_deleted=False, status__in=['stopped', 'cancelled', 'completed'])
    for s in inactive_sprints:
        if s.tasks.exclude(status='completed').exists():
            s.return_incomplete_tasks_to_product_backlog(reason="completed" if s.status == 'completed' else "cancelled")

    return updated_sprints

