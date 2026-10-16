from django.conf import settings
from django.db import models


class AccountSecurity(models.Model):
    """Persist the password-change requirement across logins and browsers."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_security")
    must_change_password = models.BooleanField(default=False)


class UserThemePreference(models.Model):
    """Persist personal theme and light/dark mode preferences per user."""

    THEME_ZARA = "zara_larsson"
    THEME_ICE = "ice"
    THEME_CITY = "city"
    THEME_FOREST = "forest"
    THEME_GAME = "game"

    THEME_CHOICES = [
        (THEME_ZARA, "Zara Larsson"),
        (THEME_ICE, "Ice"),
        (THEME_CITY, "City"),
        (THEME_FOREST, "Forest"),
        (THEME_GAME, "Game"),
    ]

    MODE_LIGHT = "light"
    MODE_DARK = "dark"

    MODE_CHOICES = [
        (MODE_LIGHT, "Light"),
        (MODE_DARK, "Dark"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="theme_preference",
    )
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default=THEME_ZARA,
    )
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_LIGHT,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_theme_display()} ({self.get_mode_display()})"

    @classmethod
    def get_for_user(cls, user):
        """Retrieve or create the theme preference for a user, or return default if unauthenticated."""
        if not user or not user.is_authenticated:
            return None
        pref, _ = cls.objects.get_or_create(
            user=user,
            defaults={"theme": cls.THEME_ZARA, "mode": cls.MODE_LIGHT},
        )
        return pref



