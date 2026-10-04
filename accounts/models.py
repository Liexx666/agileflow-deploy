from django.conf import settings
from django.db import models


class AccountSecurity(models.Model):
    """Persist the password-change requirement across logins and browsers."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_security")
    must_change_password = models.BooleanField(default=True)

