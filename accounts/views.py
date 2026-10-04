from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db import transaction

from .forms import AdminRegisterAccountForm, EmailLoginForm, ResetPasswordForm, InitialPasswordChangeForm
from .models import AccountSecurity


def login_view(request):
    if request.user.is_authenticated:
        return redirect("backlog:home")

    if request.method == "POST":
        form = EmailLoginForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            security, _ = AccountSecurity.objects.get_or_create(user=form.user)
            login(request, form.user)
            if security.must_change_password:
                return redirect("accounts:change_password")
            return redirect("backlog:home")
    else:
        form = EmailLoginForm(request=request)

    return render(request, "accounts/login.html", {"form": form})


@login_required
def change_password_ui(request):
    security, _ = AccountSecurity.objects.get_or_create(user=request.user)
    form = InitialPasswordChangeForm(user=request.user, data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            security.must_change_password = False
            security.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed. Welcome to your Sprint Board.")
        return redirect("backlog:home")
    return render(request, "accounts/change_password.html", {"form": form, "required_change": security.must_change_password})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def reset_password_ui(request):
    """
    US-11: Password reset for logged-in users.
    Validates user email matches current account, enforces 8-20 character
    alphanumeric complexity, updates password securely, and redirects to login.
    """
    if request.method == "POST":
        form = ResetPasswordForm(request.POST, current_user=request.user)
        if form.is_valid():
            form.save()
            logout(request)
            messages.success(
                request,
                "Your password has been successfully reset. Please log in with your new password.",
            )
            return redirect("accounts:login")
    else:
        form = ResetPasswordForm(current_user=request.user)

    return render(request, "accounts/reset_password.html", {"form": form})


@login_required
def user_accounts_ui(request):
    """
    US-27: View user accounts for administration.
    Only accessible by staff/admin users.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to view user accounts.",
        )
        return redirect("backlog:product_backlog")

    User = get_user_model()
    users = User.objects.all().order_by(
        "first_name",
        "last_name",
        "username",
    )

    return render(
        request,
        "accounts/user_accounts.html",
        {"account_users": users},
    )


@login_required
@require_POST
def admin_reset_user_password(request, user_id):
    """
    Allows administrators/staff to reset a user's password to default ('password123').
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to reset user passwords.",
        )
        return redirect("backlog:product_backlog")

    User = get_user_model()
    target_user = get_object_or_404(User, pk=user_id)
    with transaction.atomic():
        target_user.set_password("password123")
        target_user.save(update_fields=["password"])
        AccountSecurity.objects.update_or_create(user=target_user, defaults={"must_change_password": True})

    display_name = target_user.get_full_name() or target_user.username
    messages.success(
        request,
        f"Password for {display_name} (@{target_user.username}) has been successfully reset to default (password123).",
    )
    return redirect("accounts:user_accounts")


@login_required
def register_account_ui(request):
    """
    US-33: Registering new accounts for admin role.
    Only accessible by staff/admin users.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Access denied: You do not have permission to register new accounts.",
        )
        return redirect("backlog:product_backlog")

    if request.method == "POST":
        form = AdminRegisterAccountForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(
                request,
                f"Account for @{new_user.username} has been successfully registered.",
            )
            return redirect("accounts:user_accounts")
    else:
        form = AdminRegisterAccountForm()

    return render(request, "accounts/register_account.html", {"form": form})
