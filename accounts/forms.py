# accounts/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


from .models import CURRENCY_CHOICES

User = get_user_model()


class SignupForm(forms.Form):
    """Three fields: full name, username, password (with confirm)."""
    full_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=30, min_length=3)
    password = forms.CharField(widget=forms.PasswordInput, min_length=10)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial="USD", label="Currency")

    # user's chosen security question
    question = forms.ModelChoiceField(queryset=None)
    answer = forms.CharField(max_length=150)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SecurityQuestion
        self.fields["question"].queryset = SecurityQuestion.objects.all()

    def clean_username(self):
        username = self.cleaned_data["username"].lower()  # case-insensitive uniqueness
        if not username.replace("_", "").isalnum():
            raise forms.ValidationError("Only letters, numbers, and underscores allowed.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            # runs our ComplexityValidator + Django defaults
            validate_password(p1)
        return cleaned


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class ResetStep1Form(forms.Form):
    """Verify via security answer OR recovery code — either field works."""
    username = forms.CharField()
    answer = forms.CharField(required=False, max_length=150)
    recovery_code = forms.CharField(required=False, max_length=20)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("answer") and not cleaned.get("recovery_code"):
            raise forms.ValidationError("Provide either your security answer or a recovery code.")
        return cleaned


class SetNewPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, min_length=10)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned