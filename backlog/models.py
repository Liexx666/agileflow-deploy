from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from django.utils import timezone

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color_class = models.CharField(max_length=30, default="badge-dark-tag")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Sprint(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('active', 'Active'),
        ('stopped', 'Stopped'),
        ('completed', 'Completed'),
        ('planning', 'Planning'),
    ]

    name = models.CharField(max_length=100)
    goal = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    is_deleted = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    product_owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_owner_sprints'
    )
    scrum_master = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scrum_master_sprints'
    )
    team_members = models.ManyToManyField(
        User,
        blank=True,
        related_name='sprint_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['status'],
                condition=Q(status='active'),
                name='backlog_single_active_sprint',
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def status_badge_class(self):
        if self.status == 'completed':
            return 'badge-sprint-completed'
        elif self.status == 'stopped':
            return 'badge-sprint-stopped'
        elif self.status in ['active', 'in_progress']:
            return 'badge-sprint-active'
        return 'badge-sprint-planning'


class SprintBurndownSnapshot(models.Model):
    """The latest measured workload for one Sprint on one local calendar day."""

    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE, related_name="burndown_snapshots")
    date = models.DateField(default=timezone.localdate)
    total_story_points = models.PositiveIntegerField()
    remaining_story_points = models.PositiveIntegerField()
    measured_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["sprint", "date"], name="unique_sprint_burndown_day"),
            models.CheckConstraint(
                condition=Q(remaining_story_points__lte=models.F("total_story_points")),
                name="burndown_remaining_lte_total",
            ),
        ]


class SprintHistory(models.Model):
    """
    Records changes and audit log entries made to a Sprint.
    Satisfies AC: Sprint creation is recorded in sprint history.
    """
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.CASCADE,
        related_name='history'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sprint_changes'
    )
    description = models.CharField(
        max_length=255,
        help_text="Human-readable summary, e.g. 'Admin created sprint Sprint 1'"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Sprint histories'

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} — {self.description}"


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
    accumulated_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Accumulated hours logged on this task"
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
    is_time_entry_change = models.BooleanField(
        default=False,
        help_text="Time-entry changes are only shown to the member who made them.",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} — {self.description}"


class TaskWorkSession(models.Model):
    """One member's work interval; duration is derived from its timestamps."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="work_sessions")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="work_sessions")
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at", "-pk"]
        indexes = [models.Index(fields=["user", "started_at"], name="work_session_user_start")]
        constraints = [
            models.CheckConstraint(
                condition=Q(ended_at__gt=models.F("started_at")),
                name="work_session_positive_duration",
            ),
        ]

    @property
    def duration(self):
        return self.ended_at - self.started_at

    @property
    def duration_label(self):
        hours, minutes = divmod(int(self.duration.total_seconds()) // 60, 60)
        return f"{hours}h {minutes:02d}m"

    def __str__(self):
        return f"{self.user} — {self.task} ({self.duration_label})"


class SprintBoardPreference(models.Model):
    """Stores each user's preferred layout for an individual Sprint board."""

    VIEW_KANBAN = "kanban"
    VIEW_LIST = "list"

    VIEW_CHOICES = [
        (VIEW_KANBAN, "Kanban"),
        (VIEW_LIST, "List"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sprint_board_preferences",
    )
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.CASCADE,
        related_name="board_preferences",
    )
    view_mode = models.CharField(
        max_length=10,
        choices=VIEW_CHOICES,
        default=VIEW_KANBAN,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "sprint"],
                name="backlog_unique_user_sprint_view",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.sprint} - {self.view_mode}"
