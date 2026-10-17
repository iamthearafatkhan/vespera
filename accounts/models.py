# accounts/models.py
import hashlib
import secrets
import string

from django.contrib.auth.models import AbstractUser
from django.db import models


CURRENCY_CHOICES = [
    ("USD", "US Dollar ($)"),
    ("EUR", "Euro (€)"),
    ("GBP", "British Pound (£)"),
    ("BDT", "Bangladeshi Taka (৳)"),
    ("INR", "Indian Rupee (₹)"),
    ("JPY", "Japanese Yen (¥)"),
    ("SAR", "Saudi Riyal (﷼)"),
]

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "BDT": "৳",
    "INR": "₹",
    "JPY": "¥",
    "SAR": "﷼",
}


class User(AbstractUser):
    """Custom user. Inherits username/password/is_active/etc. from AbstractUser."""
    full_name = models.CharField(max_length=150)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="USD",
    )

    @property
    def currency_symbol(self) -> str:
        return CURRENCY_SYMBOLS.get(self.currency, "$")

    def __str__(self):
        return self.username


class SecurityQuestion(models.Model):
    text = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.text


class UserSecurityAnswer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="security_answer")
    question = models.ForeignKey(SecurityQuestion, on_delete=models.PROTECT)
    answer_hash = models.CharField(max_length=64)

    @staticmethod
    def hash_answer(raw: str) -> str:
        normalized = raw.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def check_answer(self, raw: str) -> bool:
        return self.answer_hash == self.hash_answer(raw)


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def generate_codes(n: int = 8):
        alphabet = string.ascii_uppercase + string.digits
        out = []
        for _ in range(n):
            raw = "".join(secrets.choice(alphabet) for _ in range(12))
            formatted = f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"
            out.append((formatted, RecoveryCode.hash_code(formatted)))
        return out

    def mark_used(self):
        from django.utils import timezone
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])