from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Sprint, Task
from .sprint_services import check_sprint_date_overlap


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
            else:
                # AC: Check for overlapping sprint date ranges
                conflict = check_sprint_date_overlap(start_date, end_date)
                if conflict:
                    self.add_error(
                        "start_date",
                        f"Sprint dates cannot overlap with an existing sprint ({conflict.name}: {conflict.start_date} to {conflict.end_date})."
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

        is_started = bool(
            self.instance
            and getattr(self.instance, "pk", None)
            and self.instance.status in ["active", "stopped", "cancelled", "completed"]
        )

        if is_started:
            self.fields["start_date"].widget.attrs["readonly"] = "readonly"
            self.fields["end_date"].widget.attrs["readonly"] = "readonly"
            self.fields["start_date"].help_text = "Sprint start date and end date can only be changed before the sprint starts."
            self.fields["end_date"].help_text = "Sprint start date and end date can only be changed before the sprint starts."

        clean_choices = []
        seen_labels = set()
        for code, label in Sprint.STATUS_CHOICES:
            if code in ["not_started", "planning"]:
                # AC: Once a sprint is started, it cannot be changed back to not started or planning
                if is_started and not self.is_bound:
                    continue
                if label not in seen_labels:
                    seen_labels.add(label)
                    clean_choices.append((code, label))
            elif code in ["stopped", "cancelled"]:
                # Cancelled is only allowed if the sprint is currently active (or already cancelled)
                is_active_or_cancelled = bool(
                    self.instance
                    and getattr(self.instance, "pk", None)
                    and self.instance.status in ["active", "stopped", "cancelled"]
                )
                if not is_active_or_cancelled and not self.is_bound:
                    continue
                if "Cancelled" not in seen_labels:
                    seen_labels.add("Cancelled")
                    clean_choices.append(("stopped", "Cancelled"))
            else:
                if label not in seen_labels:
                    seen_labels.add(label)
                    clean_choices.append((code, label))

        if self.is_bound:
            # Allow codes during POST so clean_status can validate and give precise error messages
            clean_choices.append(("cancelled", "Cancelled"))
            clean_choices.append(("not_started", "Not Started"))
            clean_choices.append(("planning", "Planning"))

        self.fields["status"].choices = clean_choices

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Sprint name is required.")
        return name

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if status == "cancelled":
            status = "stopped"

        current_status = getattr(self.instance, "status", None) if self.instance and self.instance.pk else None

        # AC: A completed or cancelled sprint cannot be changed anymore
        if current_status in ["completed", "stopped", "cancelled"]:
            status_display = "cancelled" if current_status in ["stopped", "cancelled"] else "completed"
            raise forms.ValidationError(f"A {status_display} sprint cannot be changed anymore.")

        # AC: Once a sprint is started, it cannot be changed back to not started or planning
        if current_status in ["active", "stopped", "cancelled", "completed"]:
            if status in ["not_started", "planning"]:
                raise forms.ValidationError(
                    "A started sprint cannot be changed back to not started or planning."
                )

        # AC: Cancelled status is only allowed if the sprint is currently active
        if status == "stopped":
            if current_status not in ["active", "stopped", "cancelled"]:
                raise forms.ValidationError("Only active sprints can be cancelled.")

        return status

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        status = cleaned_data.get("status")

        # AC: A completed or cancelled sprint cannot be changed anymore
        current_status = getattr(self.instance, "status", None) if self.instance and self.instance.pk else None
        if current_status in ["completed", "stopped", "cancelled"]:
            status_display = "cancelled" if current_status in ["stopped", "cancelled"] else "completed"
            raise forms.ValidationError(f"A {status_display} sprint cannot be changed anymore.")

        # AC: They need to change the sprint start date and end date before the sprint starts, after start cannot change anything
        if self.instance and self.instance.pk:
            orig_start = getattr(self.instance, "start_date", None)
            orig_end = getattr(self.instance, "end_date", None)
            is_started = current_status in ["active", "stopped", "cancelled", "completed"]

            if is_started:
                if start_date and orig_start and start_date != orig_start:
                    self.add_error(
                        "start_date",
                        "Sprint start date and end date can only be changed before the sprint starts. After start, dates cannot be changed."
                    )
                if end_date and orig_end and end_date != orig_end and status not in ["stopped", "completed"]:
                    self.add_error(
                        "end_date",
                        "Sprint start date and end date can only be changed before the sprint starts. After start, dates cannot be changed."
                    )

        # Validate start date and end date
        if start_date and end_date:
            if end_date < start_date:
                self.add_error(
                    "end_date",
                    "End date cannot be earlier than start date."
                )
            else:
                # AC: Check for overlapping sprint date ranges
                conflict = check_sprint_date_overlap(
                    start_date,
                    end_date,
                    exclude_sprint_id=self.instance.pk if self.instance else None
                )
                if conflict:
                    self.add_error(
                        "start_date",
                        f"Sprint dates cannot overlap with an existing sprint ({conflict.name}: {conflict.start_date} to {conflict.end_date})."
                    )

        # Enforce single active sprint rule
        if status == "active":
            another_active = (
                Sprint.objects.exclude(pk=self.instance.pk if self.instance else None)
                .filter(status="active")
                .exists()
            )
            if another_active:
                self.add_error(
                    "status",
                    "Another Sprint is already active. Complete it first."
                )

        # AC: If by manual the sprint is set to cancelled or completed, change end date to current date
        if status in ["stopped", "completed"]:
            current_status = getattr(self.instance, "status", None) if self.instance and self.instance.pk else None
            if current_status != status:
                today = timezone.localdate()
                cleaned_data["end_date"] = today
                if start_date and start_date > today:
                    cleaned_data["start_date"] = today

        return cleaned_data

    def save(self, commit=True, user=None):
        sprint = super().save(commit=False)
        if user:
            sprint._changed_by = user
        status = self.cleaned_data.get("status")
        if status in ["stopped", "completed"]:
            if self.cleaned_data.get("end_date"):
                sprint.end_date = self.cleaned_data.get("end_date")
            if self.cleaned_data.get("start_date"):
                sprint.start_date = self.cleaned_data.get("start_date")
        if commit:
            sprint.save()
            self.save_m2m()

            # Reassign sprint tasks for any removed team members if reassignments were specified
            if getattr(self, "data", None):
                User = get_user_model()
                for key, val in self.data.items():
                    if key.startswith("reassign_task_") and val:
                        try:
                            tid = int(key.replace("reassign_task_", ""))
                            task = sprint.tasks.filter(pk=tid).first()
                            if task and str(val).isdigit():
                                new_assignee = User.objects.filter(pk=int(val)).first()
                                if new_assignee:
                                    task.assignee = new_assignee
                                    task.save(update_fields=["assignee", "updated_at"])
                                    from backlog.models import TaskHistory
                                    actor_name = user.get_full_name() or user.username if user else "Admin"
                                    new_name = new_assignee.get_full_name() or new_assignee.username
                                    TaskHistory.objects.create(
                                        task=task,
                                        changed_by=user,
                                        description=f'{actor_name} reassigned task to "{new_name}"',
                                    )
                        except (ValueError, TypeError):
                            pass

        return sprint


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

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk:
            if self.instance.status == 'completed':
                raise forms.ValidationError("A completed task cannot be edited.")
            if self.instance.sprint and self.instance.sprint.status in ['completed', 'stopped', 'cancelled']:
                status_display = 'cancelled' if self.instance.sprint.status in ['stopped', 'cancelled'] else 'completed'
                raise forms.ValidationError(f"Tasks in a {status_display} sprint cannot be edited.")
        return cleaned_data
