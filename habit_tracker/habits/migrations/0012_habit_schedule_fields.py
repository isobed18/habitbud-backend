from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('habits', '0011_habittemplate_habit_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='habit',
            name='schedule_type',
            field=models.CharField(choices=[('daily', 'Daily'), ('weekdays', 'Weekdays'), ('times_per_week', 'Times per week')], default='daily', max_length=20),
        ),
        migrations.AddField(
            model_name='habit',
            name='schedule_weekdays',
            field=models.CharField(blank=True, default='', help_text="Comma-separated weekday numbers, e.g. '0,2,4'", max_length=20),
        ),
        migrations.AddField(
            model_name='habit',
            name='schedule_target_count',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='habit',
            name='schedule_locked',
            field=models.BooleanField(default=False),
        ),
    ]
