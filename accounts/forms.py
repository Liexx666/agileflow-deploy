from django import forms
from django.contrib.auth import authenticate, get_user_model


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "current-password",
            }
        ),
    )
    
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if not email or not password:
            return cleaned_data

        User = get_user_model()

        try:
            account = User.objects.get(email__iexact=email)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Perform password hashing even when no unique account matches.
            User().set_password(password)
        else:
            self.user = authenticate(
                request=self.request,
                username=account.get_username(),
                password=password,
            )

        if self.user is None:
            raise forms.ValidationError("Invalid email or password.")

        return cleaned_data