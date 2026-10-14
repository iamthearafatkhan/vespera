# expenses/forms.py
from django import forms
from django.utils import timezone
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["amount", "category", "description", "occurred_at"]
        widgets = {
            "occurred_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # default the "when" field to now so user doesn't have to touch it
        self.fields["occurred_at"].initial = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        self.fields["occurred_at"].input_formats = ["%Y-%m-%dT%H:%M"]