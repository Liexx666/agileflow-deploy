# Generated for Sprint Creation and View Sprint feature

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("backlog", "0004_alter_taskhistory_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="sprint",
            name="product_owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="product_owner_sprints",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sprint",
            name="scrum_master",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="scrum_master_sprints",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sprint",
            name="team_members",
            field=models.ManyToManyField(
                blank=True,
                related_name="sprint_teams",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sprint",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="sprint",
            name="status",
            field=models.CharField(
                choices=[
                    ("not_started", "Not Started"),
                    ("active", "Active"),
                    ("completed", "Completed"),
                    ("planning", "Planning"),
                ],
                default="not_started",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="SprintHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        help_text="Human-readable summary, e.g. 'Admin created sprint Sprint 1'",
                        max_length=255,
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sprint_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "sprint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="backlog.sprint",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "verbose_name_plural": "Sprint histories",
            },
        ),
        migrations.AddField(
            model_name="task",
            name="accumulated_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Accumulated hours logged on this task",
                max_digits=6,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
