from django import forms

from .models import Task


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
        self.fields["assignee"].required = True

        self.fields["item_type"].initial = "story"
        self.fields["story_points"].initial = 0
        self.fields["priority"].initial = "medium"
        self.fields["status"].initial = "not_started"
        self.fields["stage"].initial = "planning"

        self.fields["assignee"].empty_label = "Choose an assignee"

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
            "priority": forms.RadioSelect,
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
        self.fields["assignee"].required = True

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