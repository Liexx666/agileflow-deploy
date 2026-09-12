from django.contrib import admin
from .models import Tag, Sprint, Task


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_class')
    search_fields = ('name',)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'goal')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'priority', 'story_points', 'stage', 'status', 'assignee', 'sprint', 'is_deleted')
    list_filter = ('item_type', 'priority', 'stage', 'status', 'is_deleted', 'tags')
    search_fields = ('title', 'description', 'acceptance_criteria')
