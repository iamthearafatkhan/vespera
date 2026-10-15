# courses/forms.py
from django import forms
from django.utils import timezone
from .models import Course, StudySession


# Available color swatches for course cards.
# Keys must match the values stored in Course.color.
COLOR_SWATCHES = [
    {"key": "violet",  "hex": "#8b7bff", "label": "Violet"},
    {"key": "teal",    "hex": "#2ee7d6", "label": "Teal"},
    {"key": "emerald", "hex": "#10b981", "label": "Emerald"},
    {"key": "amber",   "hex": "#f5a623", "label": "Amber"},
    {"key": "rose",    "hex": "#ef4444", "label": "Rose"},
    {"key": "slate",   "hex": "#64748b", "label": "Slate"},
]


class CourseForm(forms.ModelForm):
    """Create / edit a course."""

    hours = forms.IntegerField(min_value=0, max_value=2000, initial=0, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")

    color = forms.ChoiceField(
        choices=[(s["key"], s["label"]) for s in COLOR_SWATCHES],
        initial="violet",
        label="Color",
    )

    class Meta:
        model = Course
        fields = ["title", "description", "platform", "course_url", "color"]
        widgets = {
            "course_url": forms.URLInput(attrs={"placeholder": "https://…"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # expose swatches to the template
        self.swatches = COLOR_SWATCHES
        # on edit, split total_minutes back into hours / minutes
        if self.instance and self.instance.pk:
            h, m = divmod(self.instance.total_minutes, 60)
            self.fields["hours"].initial = h
            self.fields["minutes"].initial = m

    def clean(self):
        cleaned = super().clean()
        h = cleaned.get("hours") or 0
        m = cleaned.get("minutes") or 0
        total = h * 60 + m
        if total <= 0:
            raise forms.ValidationError("Total course length must be at least 1 minute.")
        cleaned["total_minutes"] = total
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.total_minutes = self.cleaned_data["total_minutes"]
        if commit:
            obj.save()
        return obj


class StudySessionForm(forms.ModelForm):
    """Log a single study session against a course."""

    hours = forms.IntegerField(min_value=0, max_value=24, initial=0, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")

    class Meta:
        model = StudySession
        fields = ["notes", "occurred_at"]
        widgets = {
            "occurred_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["occurred_at"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        self.fields["occurred_at"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned = super().clean()
        h = cleaned.get("hours") or 0
        m = cleaned.get("minutes") or 0
        total = h * 60 + m
        if total <= 0:
            raise forms.ValidationError("A session must be at least 1 minute.")
        cleaned["minutes_total"] = total
        return cleaned

    def save(self, commit=True, *, course, user):
        obj = super().save(commit=False)
        obj.course = course
        obj.user = user
        obj.minutes = self.cleaned_data["minutes_total"]
        if commit:
            obj.save()
        return obj