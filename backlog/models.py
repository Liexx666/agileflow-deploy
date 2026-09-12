from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color_class = models.CharField(max_length=30, default="badge-dark-tag")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Sprint(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=100)
    goal = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def status_badge_class(self):
        if self.status == 'completed':
            return 'badge-sprint-completed'
        elif self.status == 'active':
            return 'badge-sprint-active'
        return 'badge-sprint-planning'


class Task(models.Model):
    ITEM_TYPE_CHOICES = [
        ('story', 'Story'),
        ('bug', 'Bug'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('important', 'Important'),
        ('urgent', 'Urgent'),
    ]

    STAGE_CHOICES = [
        ('planning', 'Planning'),
        ('development', 'Development'),
        ('testing', 'Testing'),
        ('integration', 'Integration'),
    ]

    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    acceptance_criteria = models.TextField(blank=True, default='')
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default='story'
    )
    story_points = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Whole number between 0 and 10"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default='planning'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    attachment = models.FileField(
    upload_to="task_attachments/%Y/%m/",
    null=True,
    blank=True,
)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.title}"


class TaskHistory(models.Model):
    """
    Records every meaningful change made to a Task — who did it and when.
    Satisfies AC: system records task changes, the user, and the timestamp.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='history'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_changes'
    )
    description = models.CharField(
        max_length=255,
        help_text="Human-readable summary, e.g. 'Angela created Task 1'"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} — {self.description}"
