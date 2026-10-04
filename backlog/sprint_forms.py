from django import forms
from datetime import datetime

from .models import Sprint, SprintBoardPreference, Task


class MoveTaskForm(forms.Form):
    """
    Accepts an active Sprint ID, or an empty value when moving
    a task back to the Product Backlog.
    """

    sprint_id = forms.IntegerField(
        required=False,
        min_value=1,
    )
    assignee_action = forms.CharField(
        required=False,
    )


class SprintTaskStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=Task.STATUS_CHOICES,
    )


class SprintBoardViewForm(forms.Form):
    view_mode = forms.ChoiceField(
        choices=SprintBoardPreference.VIEW_CHOICES,
    )


class SprintStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=Sprint.STATUS_CHOICES,
    )


class WorkSessionForm(forms.Form):
    """Parse the existing separate calendar/clock inputs in the current timezone."""

    start_date = forms.DateField(widget=forms.DateInput(
        format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"},
    ))
    start_time = forms.TimeField(input_formats=["%H:%M"], widget=forms.TimeInput(
        format="%H:%M", attrs={"type": "time", "class": "form-control", "step": "60"},
    ))
    end_date = forms.DateField(widget=forms.DateInput(
        format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"},
    ))
    end_time = forms.TimeField(input_formats=["%H:%M"], widget=forms.TimeInput(
        format="%H:%M", attrs={"type": "time", "class": "form-control", "step": "60"},
    ))

    def clean(self):
        cleaned = super().clean()
        for name in ("start", "end"):
            date, time = cleaned.get(f"{name}_date"), cleaned.get(f"{name}_time")
            if date is not None and time is not None:
                # DateTimeField also rejects ambiguous/nonexistent local times in DST zones.
                cleaned[f"{name}ed_at"] = forms.DateTimeField().clean(datetime.combine(date, time))
        if "started_at" in cleaned and "ended_at" in cleaned:
            if cleaned["ended_at"] <= cleaned["started_at"]:
                raise forms.ValidationError("End date and time must be after start date and time.")
        return cleaned
