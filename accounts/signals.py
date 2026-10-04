from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccountSecurity


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_account_security(sender, instance, created, raw, using, **kwargs):
    if created and not raw:
        AccountSecurity.objects.using(using).get_or_create(user=instance)

