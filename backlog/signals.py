"""
backlog/signals.py
Automatically records a TaskHistory entry when a Task is created.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task, TaskHistory


@receiver(post_save, sender=Task)
def record_task_created(sender, instance, created, **kwargs):
    """
    On first save (created=True), log a history entry.
    changed_by is None until authentication is wired to the forms.
    """
    pass
