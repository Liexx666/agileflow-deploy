from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


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


import re


def validate_password_complexity(password):
    """
    Validates password security requirements:
    - 8 to 20 characters in length.
    - Must include at least one letter and at least one number.
    """
    if len(password) < 8 or len(password) > 20:
        raise forms.ValidationError("Password must be between 8 and 20 characters in length.")
    if not re.search(r"[a-zA-Z]", password):
        raise forms.ValidationError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise forms.ValidationError("Password must contain at least one number.")


class InitialPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_new_password1(self):
        password = self.cleaned_data['new_password1']
        validate_password_complexity(password)
        if self.user.check_password(password):
            raise forms.ValidationError('Choose a new password different from your current password.')
        return password


class AdminRegisterAccountForm(forms.Form):
    ROLE_CHOICES = [
        ("member", "Team member"),
        ("admin", "Administrator"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    first_name = forms.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "First name is required."},
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "Last name is required."},
    )
    email = forms.EmailField(
        required=True,
        error_messages={"required": "Email address is required."},
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "Username is required."},
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        error_messages={"required": "Please select an account role."},
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        initial="active",
    )
    
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self):
        User = get_user_model()
        role = self.cleaned_data["role"]
        status = self.cleaned_data.get("status", "active")

        is_staff = role == "admin"
        is_superuser = role == "admin"
        is_active = status == "active"

        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password="password123",
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=is_active,
        )

        return user


class ResetPasswordForm(forms.Form):
    email = forms.EmailField(
        required=True,
        error_messages={"required": "Email address is required."},
    )
    new_password = forms.CharField(
        strip=False,
        min_length=8,
        required=True,
        error_messages={"required": "New password is required."},
    )
    confirm_password = forms.CharField(
        strip=False,
        min_length=8,
        required=True,
        error_messages={"required": "Please confirm the new password."},
    )

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        self.user = None

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        User = get_user_model()

        if self.current_user and self.current_user.is_authenticated:
            if not self.current_user.email or email.lower() != self.current_user.email.lower():
                raise forms.ValidationError("You can only reset your own account password. Please enter your registered email address.")
            self.user = self.current_user
            return email

        try:
            self.user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError("No account found with this email address.")
        except User.MultipleObjectsReturned:
            raise forms.ValidationError("Multiple accounts found with this email address. Please contact an administrator.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                try:
                    validate_password_complexity(new_password)
                except forms.ValidationError as e:
                    self.add_error("new_password", e)
                else:
                    if hasattr(self, "user") and self.user:
                        try:
                            validate_password(new_password, user=self.user)
                        except ValidationError as e:
                            self.add_error("new_password", e)

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        return self.user
