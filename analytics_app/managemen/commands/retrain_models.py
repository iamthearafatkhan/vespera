# analytics_app/management/commands/retrain_models.py
# (create the folder: analytics_app/management/commands/)
from django.core.management.base import BaseCommand
from analytics_app.ml import train_dropout_model


class Command(BaseCommand):
    help = "Retrain the dropout-risk model. Schedule nightly."

    def handle(self, *args, **kwargs):
        train_dropout_model()
        self.stdout.write(self.style.SUCCESS("Model retrained."))