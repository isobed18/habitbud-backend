from datetime import time

from django.core.management.base import BaseCommand

from habits.models import HabitTemplate

# (slug, name, icon, category, color, target, frequency, reminder_copy, reminder_hour)
TEMPLATES = [
    ("water",      "Su İç",         "💧", "health",       "blue",   8, "daily",
     "Bugün su içtin mi? Streak'in bitmeden su check'ini gönder! 💧", 11),
    ("walk",       "Yürüyüş",       "🚶", "fitness",      "green",  1, "daily",
     "Yürüyüş zamanı! Bugünkü yürüyüş check'ini gönder 🚶", 18),
    ("workout",    "Spor",          "🏋️", "fitness",      "orange", 1, "daily",
     "Antrenmanı atlama — terli bir check'i arkadaşlarına gönder 🏋️", 18),
    ("run",        "Koşu",          "🏃", "fitness",      "orange", 1, "daily",
     "Hadi koş! Bugünkü koşu check'ini gönder 🏃", 7),
    ("read",       "Kitap Oku",     "📖", "mind",         "purple", 1, "daily",
     "Birkaç sayfa oku ve kitap check'ini gönder 📖", 21),
    ("meditate",   "Meditasyon",    "🧘", "mind",         "purple", 1, "daily",
     "Bir nefes al. Meditasyon check'ini gönder 🧘", 8),
    ("sleep",      "Zamanında Uyu", "😴", "health",       "blue",   1, "daily",
     "Sakinleş — uyku check'ini gönder ve streak'i koru 😴", 22),
    ("stretch",    "Esneme",        "🤸", "fitness",      "green",  1, "daily",
     "Biraz esne! Esneme check'ini gönder 🤸", 9),
    ("vitamins",   "Vitamin Al",    "💊", "health",       "yellow", 1, "daily",
     "Vitaminini aldın mı? Check'ini gönder 💊", 9),
    ("journal",    "Günlük Tut",    "📝", "mind",         "pink",   1, "daily",
     "Günde bir satır — günlük check'ini gönder 📝", 21),
    ("no_sugar",   "Şekersiz Gün",  "🍭", "lifestyle",    "pink",   1, "daily",
     "Şekersiz bir gün — bugünkü check'ini gönder 🍭", 20),
    ("study",      "Ders Çalış",    "📚", "productivity", "purple", 1, "daily",
     "Odaklanma zamanı! Ders check'ini gönder 📚", 16),
    ("tidy",       "Toparlan",      "🧹", "productivity", "green",  1, "daily",
     "5 dakikalık toparlanma — check'ini gönder 🧹", 19),
    ("fruit",      "Meyve Ye",      "🍎", "health",       "green",  2, "daily",
     "Biraz meyve ye ve check'ini gönder 🍎", 13),
    ("gratitude",  "Şükran",        "🙏", "mind",         "yellow", 1, "daily",
     "Şükrettiğin bir şey yaz — check'ini gönder 🙏", 21),
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
