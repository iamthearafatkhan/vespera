# accounts/models.py
import hashlib
import secrets
import string

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user. We inherit everything from AbstractUser
    (username, password, is_active, is_staff, date_joined, last_login, ...)
    and add a full_name. Email is left blank / unused by design.
    """
    full_name = models.CharField(max_length=150)

    def __str__(self):
        return self.username


class SecurityQuestion(models.Model):
    """The fixed list of questions users can pick from (seeded via command)."""
    text = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.text


class UserSecurityAnswer(models.Model):
    """One answer per user. Stored hashed, never plaintext."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="security_answer")
    question = models.ForeignKey(SecurityQuestion, on_delete=models.PROTECT)
    answer_hash = models.CharField(max_length=64)   # sha256 hex = 64 chars

    @staticmethod
    def hash_answer(raw: str) -> str:
        # normalize so "Rex " and "rex" match
        normalized = raw.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def check_answer(self, raw: str) -> bool:
        return self.answer_hash == self.hash_answer(raw)


class RecoveryCode(models.Model):
    """One-time codes for password reset when the security answer is forgotten."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=64, db_index=True)  # sha256 hex
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def hash_code(code: str) -> str:
        # SHA-256 is fine here: the code itself is 62^12 ≈ 3.2e21 possibilities,
        # so brute force is infeasible regardless of hash speed.
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def generate_codes(n: int = 8):
        """Return a list of (plain_code, code_hash) pairs — plain is shown ONCE."""
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