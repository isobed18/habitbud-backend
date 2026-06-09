from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from challange.models import Item, ChallengeTemplate


class Command(BaseCommand):
    help = 'Populate production-ready items and challenge templates'

    def _icon_png(self, emoji, bg):
        image = Image.new("RGBA", (256, 256), bg)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("seguiemj.ttf", 124)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), emoji, font=font)
        x = (256 - (bbox[2] - bbox[0])) / 2
        y = (256 - (bbox[3] - bbox[1])) / 2 - 8
        draw.rounded_rectangle((10, 10, 246, 246), radius=42, outline=(255, 255, 255, 120), width=4)
        draw.text((x, y), emoji, font=font, fill=(255, 255, 255, 255))
        out = BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()

    def _upsert_item(self, data):
        item, _ = Item.objects.update_or_create(
            slug=data["slug"],
            defaults={
                "name": data["name"],
                "description": data["description"],
                "rarity": data["rarity"],
                "anchor": data["anchor"],
                "item_scale": data.get("item_scale", 1.0),
                "is_shop_item": data.get("is_shop_item", False),
                "price_points": data.get("price_points", 0),
                "shop_sort": data.get("shop_sort", 100),
            },
        )
        if not item.image:
            item.image.save(f"{item.slug}_icon.png", ContentFile(self._icon_png(data["emoji"], data["bg"])), save=True)
        return item

    def handle(self, *args, **kwargs):
        items_data = [
            {
                "slug": "study_lamp", "name": "Study Lamp", "emoji": "📚",
                "description": "Ders çalışma serileri için odak lambası.", "rarity": "rare",
                "anchor": "none", "bg": "#4f46e5", "is_shop_item": False,
            },
            {
                "slug": "runner_shoes", "name": "Runner Shoes", "emoji": "👟",
                "description": "Koşu ve yürüyüş görevlerinin simgesi.", "rarity": "epic",
                "anchor": "none", "bg": "#f97316", "is_shop_item": False,
            },
            {
                "slug": "hydration_flask", "name": "Hydration Flask", "emoji": "💧",
                "description": "Su alışkanlığını tamamlayanlar için.", "rarity": "rare",
                "anchor": "hand", "bg": "#0891b2", "is_shop_item": False,
            },
            {
                "slug": "gym_dumbbell", "name": "Gym Dumbbell", "emoji": "🏋️",
                "description": "Spor odaları ve gym görevleri için ağırlık.", "rarity": "epic",
                "anchor": "hand", "bg": "#334155", "is_shop_item": False,
            },
            {
                "slug": "focus_headband", "name": "Focus Headband", "emoji": "🎯",
                "description": "Odak modunu sevenler için kozmetik.", "rarity": "common",
                "anchor": "head", "bg": "#16a34a", "is_shop_item": True, "price_points": 180, "shop_sort": 10,
            },
            {
                "slug": "neon_glasses", "name": "Neon Glasses", "emoji": "🕶️",
                "description": "Profil stilini parlatan nadir gözlük.", "rarity": "rare",
                "anchor": "face", "bg": "#7c3aed", "is_shop_item": True, "price_points": 320, "shop_sort": 20,
            },
            {
                "slug": "streak_cape", "name": "Streak Cape", "emoji": "🔥",
                "description": "Uzun seriler için gösterişli pelerin.", "rarity": "legendary",
                "anchor": "back", "bg": "#dc2626", "is_shop_item": True, "price_points": 900, "shop_sort": 30,
            },
        ]

        items = {data["slug"]: self._upsert_item(data) for data in items_data}

        ChallengeTemplate.objects.all().delete()
        self.stdout.write(self.style.WARNING('Cleared existing challenge templates.'))

        templates_data = [
            {
                'name': '7 Day Study Sprint',
                'description': '7 gün boyunca ders çalışma habitini tamamla. Ödül: Study Lamp.',
                'predefined_habit_name': 'Studying',
                'challenge_type': 'SOLO',
                'duration_days': 7,
                'reward_xp': 180,
                'reward_points': 120,
                'reward_item': items['study_lamp'],
            },
            {
                'name': '7 Day Water Warrior',
                'description': '7 gün su alışkanlığını tamamla. Ödül: Hydration Flask.',
                'predefined_habit_name': 'Drinking Water',
                'challenge_type': 'SOLO',
                'duration_days': 7,
                'reward_xp': 120,
                'reward_points': 90,
                'reward_item': items['hydration_flask'],
            },
            {
                'name': '14 Day Runner',
                'description': '14 gün koşu/yürüyüş serisi yap. Ödül: Runner Shoes.',
                'predefined_habit_name': 'Running',
                'challenge_type': 'SOLO',
                'duration_days': 14,
                'reward_xp': 320,
                'reward_points': 220,
                'reward_item': items['runner_shoes'],
            },
            {
                'name': '7 Day Study Buddy',
                'description': 'Arkadaşınla 7 gün ders çalışın ve birbirinizi doğrulayın. Ödül: Study Lamp.',
                'predefined_habit_name': 'Studying',
                'challenge_type': 'DUO',
                'duration_days': 7,
                'reward_xp': 260,
                'reward_points': 180,
                'reward_item': items['study_lamp'],
            },
            {
                'name': '14 Day Gym Duo',
                'description': 'Partnerinle 14 gün spor habitini tamamla. Ödül: Gym Dumbbell.',
                'predefined_habit_name': 'Gym',
                'challenge_type': 'DUO',
                'duration_days': 14,
                'reward_xp': 420,
                'reward_points': 280,
                'reward_item': items['gym_dumbbell'],
            },
        ]

        for data in templates_data:
            ChallengeTemplate.objects.update_or_create(name=data['name'], defaults=data)
            self.stdout.write(self.style.SUCCESS(f"Seeded Template: {data['name']}"))

        self.stdout.write(self.style.SUCCESS('Successfully populated challenge data.'))
