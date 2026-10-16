from django.shortcuts import redirect

from .models import AccountSecurity


class RequirePasswordChangeMiddleware:
    """Block every application view until the initial password is changed."""

    allowed_views = {"accounts:change_password", "accounts:logout"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.password_change_required = False
        if request.user.is_authenticated:
            security, _ = AccountSecurity.objects.get_or_create(user=request.user)
            request.password_change_required = security.must_change_password
            if security.must_change_password and request.resolver_match and request.resolver_match.view_name not in self.allowed_views:
                return redirect("accounts:change_password")

