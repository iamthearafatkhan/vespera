# courses/forms.py
from django import forms
from django.utils import timezone
from .models import Course, StudySession


class CourseForm(forms.ModelForm):
    """Create / edit a course. User enters hours + minutes separately."""

    hours = forms.IntegerField(min_value=0, max_value=2000, initial=0, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")

    class Meta:
        model = Course
        fields = ["title", "description", "color"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # when editing, split total_minutes back into hours / minutes
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
        # stash for save()
        cleaned["total_minutes"] = total
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.total_minutes = self.cleaned_data["total_minutes"]
        if commit:
            obj.save()
        return obj


class StudySessionForm(forms.ModelForm):
    """Log a session. Hours + minutes split for friendly input."""

    hours = forms.IntegerField(min_value=0, max_value=24, initial=0, label="Hours")
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0, label="Minutes")

    class Meta:
        model = StudySession
        fields = ["notes", "occurred_at"]
        widgets = {
            # datetime-local renders a nice native picker
            "occurred_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pre-fill "now" so the user doesn't have to touch it
        self.fields["occurred_at"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

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