from django.contrib.auth import login,logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import EmailLoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("backlog:product_backlog")

    if request.method == "POST":
        form = EmailLoginForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            login(request, form.user)
            return redirect("backlog:product_backlog")
    else:
        form = EmailLoginForm(request=request)

    return render(request, "accounts/login.html", {"form": form})

@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")