import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models


def normalize_active_sprints(apps, schema_editor):
    """
    Keep the newest active Sprint and return duplicate
    active Sprints to Planning.
    """

    Sprint = apps.get_model(
        'backlog',
        'Sprint',
    )

    active_sprints = list(
        Sprint.objects
        .filter(status='active')
        .order_by(
            '-created_at',
            '-pk',
        )
    )

    if len(active_sprints) > 1:
        duplicate_ids = [
            sprint.pk
            for sprint in active_sprints[1:]
        ]

        Sprint.objects.filter(
            pk__in=duplicate_ids
        ).update(
            status='planning'
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            'backlog',
            '0004_alter_taskhistory_description',
        ),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        migrations.CreateModel(
            name='SprintBoardPreference',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'view_mode',
                    models.CharField(
                        choices=[
                            ('kanban', 'Kanban'),
                            ('list', 'List'),
                        ],
                        default='kanban',
                        max_length=10,
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                    ),
                ),
            ],
        ),

        migrations.RunPython(
            normalize_active_sprints,
            reverse_code=migrations.RunPython.noop,
        ),

        migrations.AddConstraint(
            model_name='sprint',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('status', 'active')
                ),
                fields=('status',),
                name='backlog_single_active_sprint',
            ),
        ),

        migrations.AddField(
            model_name='sprintboardpreference',
            name='sprint',
            field=models.ForeignKey(
                on_delete=(
                    django.db.models.deletion.CASCADE
                ),
                related_name='board_preferences',
                to='backlog.sprint',
            ),
        ),

        migrations.AddField(
            model_name='sprintboardpreference',
            name='user',
            field=models.ForeignKey(
                on_delete=(
                    django.db.models.deletion.CASCADE
                ),
                related_name='sprint_board_preferences',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        migrations.AddConstraint(
            model_name='sprintboardpreference',
            constraint=models.UniqueConstraint(
                fields=(
                    'user',
                    'sprint',
                ),
                name='backlog_unique_user_sprint_view',
            ),
        ),
    ]