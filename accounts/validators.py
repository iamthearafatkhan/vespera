# accounts/validators.py
import re
from django.core.exceptions import ValidationError


class ComplexityValidator:
    """Require at least one uppercase, one lowercase, and one digit."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain an uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain a lowercase letter.")
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain a number.")

    def get_help_text(self):
        return "Must include an uppercase letter, a lowercase letter, and a number."