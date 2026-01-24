from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from habits.models import Habit, HabitCompletion, HabitHistory
from challange.models import Challenge, ChallengeTemplate, Item, UserItem
from achievement.models import Achievement
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create demo users with rich history, streaks, and achievements'

    def handle(self, *args, **kwargs):
        # 1. Define Demo Users
        demo_users_data = [
            {
                'username': 'aslan_berk',
                'email': 'berk@example.com',
                'bio': 'Disiplin her şeydir. 30 günlük koşu serimi asla bozmam.',
                'xp': 4500,
                'level': 10,
                'points': 2500,
                'habits': [
                    {'name': 'Sabah Koşusu', 'type': 'count', 'target': 1, 'streak': 45},
                    {'name': 'Kitap Okuma', 'type': 'count', 'target': 1, 'streak': 12},
                    {'name': 'Meditasyon', 'type': 'count', 'target': 1, 'streak': 5},
                ],
                'achievements': ['Erken Kalkan Yol Alır', 'Koşu Canavarı', 'Disiplin Abidesi'],
                'items': ['Golden Shoes', 'Heart Locket']
            },
            {
                'username': 'zeynep_enerji',
                'email': 'zeynep@example.com',
                'bio': 'Sağlıklı yaşam ve bol su! 💧 Habit Tracker ile hayatım değişti.',
                'xp': 6200,
                'level': 12,
                'points': 5000,
                'habits': [
                    {'name': 'Su İçme (3L)', 'type': 'count', 'target': 1, 'streak': 60},
                    {'name': 'Yoga', 'type': 'count', 'target': 1, 'streak': 20},
                    {'name': 'Sağlıklı Beslenme', 'type': 'count', 'target': 1, 'streak': 30},
                ],
                'achievements': ['Su Ejderhası', 'Esneklik Ustası', '60 Günlük Başarı'],
                'items': ['Crystal Bottle']
            },
            {
                'username': 'demir_disiplin',
                'email': 'demir@example.com',
                'bio': 'Kod yazmak ve spor yapmak hobim değil, yaşam tarzım.',
                'xp': 3200,
                'level': 8,
                'points': 1200,
                'habits': [
                    {'name': 'Kod Yazma', 'type': 'count', 'target': 1, 'streak': 100},
                    {'name': 'Gym', 'type': 'count', 'target': 1, 'streak': 3},
                ],
                'achievements': ['Kod Dehası', '100 Günlük Maraton'],
                'items': ['Keyboard of Wisdom']
            }
        ]

        today = timezone.now().date()

        for u_data in demo_users_data:
            # Delete if exists to recreate
            User.objects.filter(username=u_data['username']).delete()
            
            user = User.objects.create_user(
                username=u_data['username'],
                email=u_data['email'],
                password='password123',
                bio=u_data['bio'],
                xp=u_data['xp'],
                level=u_data['level'],
                points=u_data['points']
            )
            self.stdout.write(self.style.SUCCESS(f"User created: {user.username}"))

            # 2. Create Habits & History
            for h_data in u_data['habits']:
                habit = Habit.objects.create(
                    user=user,
                    name=h_data['name'],
                    habit_type=h_data['type'],
                    target_count=h_data['target'] if h_data['type'] == 'count' else None,
                    frequency='daily',
                    streak=h_data['streak'],
                    best_streak=h_data['streak'] + 5,
                    color=random.choice(['blue', 'green', 'purple', 'orange', 'pink'])
                )

                # Generate history for the last 30 days based on streak
                for i in range(40):
                    history_date = today - timedelta(days=i)
                    
                    # If streak is 45, we fill at least the last 45 days. 
                    # Let's just fill for the last 40 days for demo.
                    if i < h_data['streak']:
                        # Completed day
                        HabitCompletion.objects.create(habit=habit, completed_at=history_date)
                        HabitHistory.objects.create(
                            habit=habit, 
                            date=history_date, 
                            count=h_data['target']
                        )
                    elif random.random() > 0.4: # Some random history before the streak
                        HabitHistory.objects.create(
                            habit=habit, 
                            date=history_date, 
                            count=random.randint(0, h_data['target'] if h_data['type'] == 'count' else 1)
                        )

            # 3. Create Achievements
            for ach_name in u_data['achievements']:
                Achievement.objects.create(
                    user=user,
                    name=ach_name,
                    description=f"Awarded for exceptional performance in {ach_name} milestones."
                )

            # 4. Inventory items
            for item_name in u_data['items']:
                try:
                    item = Item.objects.get(name=item_name)
                    UserItem.objects.create(user=user, item=item)
                    self.stdout.write(f"Added {item.name} to {user.username}")
                except Item.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Item {item_name} not found!"))

            # 5. Some completed challenges
            templates = ChallengeTemplate.objects.all()
            if templates.exists():
                for i in range(2):
                    template = random.choice(templates)
                    
                    partner = None
                    if template.challenge_type == 'DUO':
                        # Find another demo user or create a ghost partner
                        other_users = User.objects.exclude(id=user.id)
                        if other_users.exists():
                            partner = other_users.first()
                        else:
                            # Create a dummy partner if no other users exist yet
                            partner = User.objects.get_or_create(username="demo_partner", email="partner@demo.com")[0]

                    Challenge.objects.create(
                        template=template,
                        creator=user,
                        partner=partner,
                        status='COMPLETED',
                        current_streak=template.duration_days,
                        start_date=today - timedelta(days=template.duration_days + 5)
                    )
                self.stdout.write(f"History and challenges populated for {user.username}")

        self.stdout.write(self.style.SUCCESS("Demo users and rich history successfully created!"))
