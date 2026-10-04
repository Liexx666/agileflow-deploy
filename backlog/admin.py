from django.contrib import admin

from .models import (
    Sprint,
    SprintBoardPreference,
    SprintHistory,
    Tag,
    Task,
    TaskHistory,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'color_class',
    )
    search_fields = (
        'name',
    )


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'status',
        'start_date',
        'end_date',
        'product_owner',
        'scrum_master',
        'created_at',
    )
    list_filter = (
        'status',
    )
    search_fields = (
        'name',
        'goal',
    )
    filter_horizontal = ('team_members',)


@admin.register(SprintHistory)
class SprintHistoryAdmin(admin.ModelAdmin):
    list_display = ('sprint', 'changed_by', 'description', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('sprint__name', 'description', 'changed_by__username')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ('accumulated_hours',)
    list_display = (
        'title',
        'item_type',
        'priority',
        'story_points',
        'accumulated_hours',
        'stage',
        'status',
        'assignee',
        'sprint',
        'is_deleted',
    )
    list_filter = (
        'item_type',
        'priority',
        'stage',
        'status',
        'is_deleted',
        'tags',
    )
    search_fields = (
        'title',
        'description',
        'acceptance_criteria',
    )


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'changed_by', 'description', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('task__title', 'description', 'changed_by__username')


@admin.register(SprintBoardPreference)
class SprintBoardPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'sprint',
        'view_mode',
        'updated_at',
    )
    list_filter = (
        'view_mode',
        'sprint',
    )
    search_fields = (
        'user__username',
        'sprint__name',
    )

