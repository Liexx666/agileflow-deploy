from django.apps import AppConfig


class BacklogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backlog'

    def ready(self):
        import backlog.signals  # noqa: F401 — registers post_save signal
