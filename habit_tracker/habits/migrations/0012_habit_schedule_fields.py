from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("habits", "0011_habittemplate_habit_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="habit",
            name="schedule_type",
            field=models.CharField(
                choices=[
                    ("daily", "Daily"),
                    ("specific_weekdays", "Specific weekdays"),
                    ("weekly_count", "Times per week"),
                    ("monthly_count", "Times per month"),
                ],
                default="daily",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="habit",
            name="schedule_weekdays",
            field=models.CharField(blank=True, default="", help_text="Comma-separated weekday numbers, Monday=0.", max_length=20),
        ),
        migrations.AddField(
            model_name="habit",
            name="schedule_target_count",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="habit",
            name="schedule_locked",
            field=models.BooleanField(default=False),
        ),
    ]
