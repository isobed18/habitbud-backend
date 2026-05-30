from datetime import time

from django.core.management.base import BaseCommand

from habits.models import HabitTemplate

# (slug, name, icon, category, color, target, frequency, reminder_copy, reminder_hour)
TEMPLATES = [
    ("water",      "Drink Water",   "💧", "health",       "blue",   8, "daily",
     "Did you drink water today? Send your water check before your streak breaks! 💧", 11),
    ("walk",       "Take a Walk",   "🚶", "fitness",      "green",  1, "daily",
     "Time for a walk! Snap your walk check today 🚶", 18),
    ("workout",    "Workout",       "🏋️", "fitness",      "orange", 1, "daily",
     "Don't skip your workout — send a sweaty check to your friends 🏋️", 18),
    ("run",        "Go for a Run",  "🏃", "fitness",      "orange", 1, "daily",
     "Lace up! Send your run check today 🏃", 7),
    ("read",       "Read a Book",   "📖", "mind",         "purple", 1, "daily",
     "Read a few pages and send your reading check 📖", 21),
    ("meditate",   "Meditate",      "🧘", "mind",         "purple", 1, "daily",
     "Take a breath. Send your meditation check 🧘", 8),
    ("sleep",      "Sleep on Time", "😴", "health",       "blue",   1, "daily",
     "Wind down — send your sleep check and keep the streak alive 😴", 22),
    ("stretch",    "Stretch",       "🤸", "fitness",      "green",  1, "daily",
     "Loosen up! Send your stretch check 🤸", 9),
    ("vitamins",   "Take Vitamins", "💊", "health",       "yellow", 1, "daily",
     "Did you take your vitamins? Send your check 💊", 9),
    ("journal",    "Journal",       "📝", "mind",         "pink",   1, "daily",
     "A line a day — send your journal check 📝", 21),
    ("no_sugar",   "No Sugar",      "🍭", "lifestyle",    "pink",   1, "daily",
     "Stay sweet without sugar — send today's check 🍭", 20),
    ("study",      "Study",         "📚", "productivity", "purple", 1, "daily",
     "Focus time! Send your study check 📚", 16),
    ("tidy",       "Tidy Up",       "🧹", "productivity", "green",  1, "daily",
     "5-minute tidy — send your check 🧹", 19),
    ("fruit",      "Eat Fruit",     "🍎", "health",       "green",  2, "daily",
     "Grab some fruit and send your check 🍎", 13),
    ("gratitude",  "Gratitude",     "🙏", "mind",         "yellow", 1, "daily",
     "Name one thing you're grateful for — send your check 🙏", 21),
]


class Command(BaseCommand):
    help = "Seed the predefined habit template catalog."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for order, (slug, name, icon, category, color, target, freq, copy, hour) in enumerate(TEMPLATES):
            obj, was_created = HabitTemplate.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "icon": icon,
                    "category": category,
                    "color": color,
                    "habit_type": "count",
                    "default_target_count": target,
                    "default_frequency": freq,
                    "reminder_copy": copy,
                    "reminder_time": time(hour, 0),
                    "sort_order": order,
                    "is_active": True,
                },
            )
            created += was_created
            updated += not was_created
        self.stdout.write(self.style.SUCCESS(
            f"Habit templates seeded: {created} created, {updated} updated, {len(TEMPLATES)} total."
        ))
