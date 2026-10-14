# expenses/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    """A single spending entry."""

    # Fixed category list — keeps analytics clean and predictable.
    # We can add ML auto-categorization later that predicts one of these.
    CATEGORY_CHOICES = [
        ("food",          "🍔 Food & Drink"),
        ("transport",     "🚌 Transport"),
        ("bills",         "🧾 Bills & Utilities"),
        ("shopping",      "🛍️ Shopping"),
        ("health",        "💊 Health"),
        ("entertainment", "🎬 Entertainment"),
        ("education",     "📚 Education"),
        ("other",         "📦 Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")

    # DecimalField for money — NEVER use FloatField for currency.
    # max_digits=10, decimal_places=2 → up to 99,999,999.99
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    description = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            # We query "expenses in this month" a lot — speed it up.
            models.Index(fields=["user", "occurred_at"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"{self.amount} · {self.get_category_display()}"