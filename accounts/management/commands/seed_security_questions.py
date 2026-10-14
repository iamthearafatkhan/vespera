# accounts/management/commands/seed_security_questions.py
from django.core.management.base import BaseCommand
from accounts.models import SecurityQuestion

QUESTIONS = [
    "What is your favourite pet's name?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What is your favourite book?",
]

class Command(BaseCommand):
    help = "Seed the fixed list of security questions."

    def handle(self, *args, **kwargs):
        for q in QUESTIONS:
            SecurityQuestion.objects.get_or_create(text=q)
        self.stdout.write(self.style.SUCCESS("Security questions seeded."))