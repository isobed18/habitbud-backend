from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_customuser_streak_freezes_streakfreezeusage"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_paid",
            field=models.BooleanField(default=False),
        ),
    ]
