from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import AccountSecurity


class Command(BaseCommand):
    help = "Resets all account passwords to default ('password123') and clears the must_change_password flag."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default="password123",
            help="New password to set for all accounts (default: password123)",
        )

    def handle(self, *args, **options):
        password = options["password"]
        User = get_user_model()
        users = list(User.objects.all())
        for user in users:
            user.set_password(password)
            user.save(update_fields=["password"])
            AccountSecurity.objects.update_or_create(
                user=user,
                defaults={"must_change_password": False},
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully reset password to '{password}' for {len(users)} accounts."
            )
        )
