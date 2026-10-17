from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import AccountSecurity


class Command(BaseCommand):
    help = "Resets all account passwords to default ('password123') and configures the must_change_password flag."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            type=str,
            default="password123",
            help="New password to set for all accounts (default: password123)",
        )
        parser.add_argument(
            "--require-change",
            action="store_true",
            default=True,
            help="Require users to change password on their next login (default: True)",
        )
        parser.add_argument(
            "--no-require-change",
            dest="require_change",
            action="store_false",
            help="Do not require users to change password on their next login",
        )

    def handle(self, *args, **options):
        password = options["password"]
        require_change = options.get("require_change", True)
        User = get_user_model()
        users = list(User.objects.all())
        for user in users:
            user.set_password(password)
            user.save(update_fields=["password"])
            AccountSecurity.objects.update_or_create(
                user=user,
                defaults={"must_change_password": require_change},
            )
        status_msg = "must change password on next login" if require_change else "login directly without password change"
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully reset password to '{password}' for {len(users)} accounts ({status_msg})."
            )
        )
