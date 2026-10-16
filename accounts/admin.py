from django.contrib import admin
from .models import AccountSecurity, UserThemePreference


@admin.register(AccountSecurity)
class AccountSecurityAdmin(admin.ModelAdmin):
    list_display = ("user", "must_change_password")
    list_filter = ("must_change_password",)
    search_fields = ("user__username", "user__email")


@admin.register(UserThemePreference)
class UserThemePreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "mode")
    list_filter = ("theme", "mode")
    search_fields = ("user__username", "user__email")
