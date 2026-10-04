from django import forms
from django.contrib.auth import get_user_model

from .models import Sprint, Task


class SprintCreateForm(forms.ModelForm):
    """
    Validates all information required when creating a new sprint.
    Satisfies US & Acceptance Criteria for Sprint Creation.
    """

    class Meta:
        model = Sprint
        fields = [
            "name",
            "start_date",
            "end_date",
            "team_members",
            "goal",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter a sprint name (e.g. Sprint 1)",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "team_members": forms.CheckboxSelectMultiple(),
            "goal": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Sprint goal or objectives (optional)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].required = True
        self.fields["start_date"].required = True
        self.fields["end_date"].required = True

        # Query all registered users for role selection (exclude admins)
        User = get_user_model()
        user_queryset = User.objects.filter(is_superuser=False).order_by("first_name", "last_name", "username")
        self.fields["team_members"].queryset = user_queryset

        self.fields["team_members"].label_from_instance = (
            lambda obj: obj.get_full_name() or obj.username
        )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Sprint name is required.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validate start date and end date
        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "End date cannot be earlier than start date."
                )

        return cleaned_data

    def save(self, commit=True):
        sprint = super().save(commit=False)
        # AC: Newly created sprint has status Not Started
        sprint.status = "not_started"
        if commit:
            sprint.save()
            self.save_m2m()
        return sprint


class SprintEditForm(forms.ModelForm):
    """
    Form used to edit an existing Sprint.
    Satisfies US & Acceptance Criteria for Editing Sprint Details.
    """

    class Meta:
        model = Sprint
        fields = [
            "name",
            "start_date",
            "end_date",
            "team_members",
            "goal",
            "status",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter sprint name",
                }
            ),
            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "team_members": forms.CheckboxSelectMultiple(),
            "goal": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Sprint goal or objectives",
                }
            ),
            "status": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].required = True
        self.fields["start_date"].required = True
        self.fields["end_date"].required = True

        User = get_user_model()
        user_queryset = User.objects.filter(is_superuser=False).order_by("first_name", "last_name", "username")
        self.fields["team_members"].queryset = user_queryset

        self.fields["team_members"].label_from_instance = (
            lambda obj: obj.get_full_name() or obj.username
        )

        if self.instance and self.instance.status not in ['active', 'stopped']:
            choices = [c for c in Sprint.STATUS_CHOICES if c[0] != 'stopped']
            self.fields["status"].choices = choices

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Sprint name is required.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validate start date and end date
        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "End date cannot be earlier than start date."
                )

        return cleaned_data


class TaskCreateForm(forms.ModelForm):
    """Validates all information required when creating a backlog task."""

    class Meta:
        model = Task
        fields = [
            "title",
            "item_type",
            "story_points",
            "tags",
            "priority",
            "assignee",
            "description",
            "status",
            "stage",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter a clear task name",
                }
            ),
            "item_type": forms.RadioSelect,
            "story_points": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 10,
                    "step": 1,
                }
            ),
            "tags": forms.CheckboxSelectMultiple,
            "priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "assignee": forms.Select(
                attrs={"class": "form-select"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the work to be completed",
                }
            ),
            "status": forms.RadioSelect,
            "stage": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].required = True
        self.fields["description"].required = True
        self.fields["tags"].required = True
        self.fields["assignee"].required = False

        self.fields["item_type"].initial = "story"
        self.fields["story_points"].initial = 0
        self.fields["priority"].initial = "medium"
        self.fields["status"].initial = "not_started"
        self.fields["stage"].initial = "planning"

        self.fields["assignee"].empty_label = "Unassigned"
        
        User = get_user_model()
        user_queryset = User.objects.filter(is_superuser=False).order_by("first_name", "last_name", "username")
        self.fields["assignee"].queryset = user_queryset

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError("Enter a task name.")

        return title

    def clean_story_points(self):
        story_points = self.cleaned_data.get("story_points")

        if story_points is None or not 0 <= story_points <= 10:
            raise forms.ValidationError(
                "Story points must be a whole number from 0 to 10."
            )

        return story_points

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")

        if attachment and attachment.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "The attachment must be 10 MB or smaller."
            )

        return attachment


class TaskEditForm(forms.ModelForm):
    """Form used to edit an existing backlog task."""

    class Meta:
        model = Task
        fields = [
            "title",
            "item_type",
            "story_points",
            "tags",
            "priority",
            "assignee",
            "description",
            "status",
            "stage",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter a clear task name",
                }
            ),
            "item_type": forms.RadioSelect,
            "story_points": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                    "max": 10,
                    "step": 1,
                }
            ),
            "tags": forms.CheckboxSelectMultiple,
            "priority": forms.Select(
                attrs={"class": "form-select"}
            ),
            "assignee": forms.Select(
                attrs={"class": "form-select"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the work to be completed",
                }
            ),
            "status": forms.RadioSelect,
            "stage": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].required = True
        self.fields["description"].required = True
        self.fields["tags"].required = True
        self.fields["assignee"].required = False
        self.fields["assignee"].empty_label = "Unassigned"

        User = get_user_model()
        user_queryset = User.objects.filter(is_superuser=False).order_by("first_name", "last_name", "username")
        self.fields["assignee"].queryset = user_queryset

    def clean_title(self):
        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError("Enter a task name.")

        return title

    def clean_story_points(self):
        story_points = self.cleaned_data.get("story_points")

        if story_points is None or not 0 <= story_points <= 10:
            raise forms.ValidationError(
                "Story points must be a whole number from 0 to 10."
            )

        return story_points
