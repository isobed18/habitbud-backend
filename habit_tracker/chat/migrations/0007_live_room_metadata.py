import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chat", "0006_conversation_avatar_conversation_created_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="live_room_type",
            field=models.CharField(
                choices=[("general", "General"), ("study", "Study"), ("workout", "Workout")],
                default="general",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="required_habit_slug",
            field=models.SlugField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="conversation",
            name="capacity",
            field=models.PositiveSmallIntegerField(default=8),
        ),
        migrations.AddField(
            model_name="conversation",
            name="privacy",
            field=models.CharField(
                choices=[("friends", "Friends"), ("private", "Private"), ("public", "Public")],
                default="friends",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="join_policy",
            field=models.CharField(
                choices=[("open", "Open"), ("request", "Request")],
                default="open",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="pomodoro_work_minutes",
            field=models.PositiveSmallIntegerField(default=25),
        ),
        migrations.AddField(
            model_name="conversation",
            name="pomodoro_break_minutes",
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.CreateModel(
            name="LiveRoomJoinRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")], default="pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="join_requests", to="chat.conversation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="live_room_join_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("room", "user")},
            },
        ),
    ]
