"""Keep Sprint burndown history in sync with workload changes."""

from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .burndown import record_sprint_burndown
from .models import Sprint, Task


WORKLOAD_FIELDS = {"sprint_id", "status", "story_points", "is_deleted"}


def schedule_snapshots(sprint_ids, using):
    for sprint_id in sorted(sprint_ids - {None}):
        # Rolled-back changes must not leave a progress record.
        transaction.on_commit(partial(record_sprint_burndown, sprint_id), using=using)


@receiver(pre_save, sender=Task)
def remember_task_workload(sender, instance, update_fields, raw, using, **kwargs):
    instance._previous_workload = None
    if raw or (update_fields is not None and not (WORKLOAD_FIELDS | {"sprint"}) & set(update_fields)):
        return
    if instance.pk:
        instance._previous_workload = sender.objects.using(using).filter(pk=instance.pk).values(*WORKLOAD_FIELDS).first()


@receiver(post_save, sender=Task)
def record_task_workload(sender, instance, created, update_fields, raw, using, **kwargs):
    if raw or (update_fields is not None and not (WORKLOAD_FIELDS | {"sprint"}) & set(update_fields)):
        return
    previous = getattr(instance, "_previous_workload", None)
    if created or previous is None or any(previous[field] != getattr(instance, field) for field in WORKLOAD_FIELDS):
        schedule_snapshots({instance.sprint_id, previous["sprint_id"] if previous else None}, using)


@receiver(post_delete, sender=Task)
def record_removed_task(sender, instance, using, **kwargs):
    schedule_snapshots({instance.sprint_id}, using)


@receiver(post_save, sender=Sprint)
def record_sprint_workload(sender, instance, created, update_fields, raw, using, **kwargs):
    if not raw and (created or update_fields is None or {"start_date", "end_date", "status"} & set(update_fields)):
        schedule_snapshots({instance.pk}, using)
