"""US-21: Persist daily progress and build the Sprint's percentage burndown."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import Sprint, SprintBurndownSnapshot


def sprint_workload(sprint):
    totals = sprint.tasks.filter(is_deleted=False).aggregate(
        total=Sum("story_points"),
        remaining=Sum("story_points", filter=~Q(status="completed")),
    )
    return totals["total"] or 0, totals["remaining"] or 0


def percentage_left(total, remaining):
    return round(remaining / total * 100, 2) if total else 0


@transaction.atomic
def record_sprint_burndown(sprint_id):
    # Serialize updates for this Sprint and aggregate committed task data.
    sprint = Sprint.objects.select_for_update().filter(pk=sprint_id).first()
    if sprint is None:
        return
    total, remaining = sprint_workload(sprint)
    measured_at = timezone.now()
    SprintBurndownSnapshot.objects.update_or_create(
        sprint=sprint,
        date=timezone.localdate(measured_at),
        defaults={
            "total_story_points": total,
            "remaining_story_points": remaining,
            "measured_at": measured_at,
        },
    )


def build_sprint_burndown(sprint):
    """Return daily chart values. Unknown history and future progress stay null."""
    total, remaining = sprint_workload(sprint)
    current_percentage = percentage_left(total, remaining)
    data = {
        "sprint_id": sprint.pk,
        "total_story_points": total,
        "remaining_story_points": remaining,
        "remaining_percentage": current_percentage,
        "available": False,
        "labels": [],
        "ideal": [],
        "actual": [],
        "note": "",
    }
    start, end = sprint.start_date, sprint.end_date
    if not start or not end or end < start:
        data["note"] = "Set a valid Sprint start and end date to display the burndown chart."
        return data

    today = timezone.localdate()
    snapshots = list(sprint.burndown_snapshots.filter(date__lte=today).order_by("date"))
    days = (end - start).days + 1
    initial = 100 if total else 0
    # The separate opening point represents all planned work before day one.
    labels, ideal, actual = [f"{start.isoformat()} (start)"], [initial], [initial]
    cursor, last_snapshot = 0, None
    for index in range(days):
        day = start + timedelta(days=index)
        while cursor < len(snapshots) and snapshots[cursor].date <= day:
            last_snapshot = snapshots[cursor]
            cursor += 1
        value = None
        if day <= today and last_snapshot is not None:
            value = percentage_left(last_snapshot.total_story_points, last_snapshot.remaining_story_points)
        # Use current database values for the latest visible point.
        if day == min(today, end) and today >= start:
            value = current_percentage
        labels.append(day.isoformat())
        ideal.append(round(initial * (days - index - 1) / days, 2))
        actual.append(value)

    notes = ["Daily values show the latest recorded progress for each date."]
    if snapshots and snapshots[0].date > start:
        notes.append(f"History starts on {snapshots[0].date.isoformat()}; earlier daily values were not recorded.")
    elif not snapshots and today >= start:
        notes.append("Earlier daily values were not recorded.")
    if today > end:
        notes.append("The final date shows the latest known Sprint progress.")
    if not total:
        notes.append("This Sprint has no story points; remaining work is 0%.")
    data.update(available=True, labels=labels, ideal=ideal, actual=actual, note=" ".join(notes))
    return data
