from django.core.management.base import BaseCommand
from backlog.sprint_services import auto_update_sprint_statuses


class Command(BaseCommand):
    help = "Automatically start sprints on start date and complete sprints on end date."

    def handle(self, *args, **options):
        updated = auto_update_sprint_statuses()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated {len(updated)} sprint(s)."
            )
        )
