# courses/migrations/000X_backfill_colors.py
from django.db import migrations


def backfill(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    palette = ["violet", "teal", "emerald", "amber", "rose", "slate"]

    for i, course in enumerate(Course.objects.all()):
        if not course.color:                     # empty or None
            course.color = palette[i % len(palette)]
            course.save(update_fields=["color"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("courses", "0001_initial")]   # adjust if needed
    operations = [migrations.RunPython(backfill, noop)]