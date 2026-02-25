from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from habits.models import Habit, HabitCompletion, HabitHistory, HabitVerification
from friends.models import Friendship
from challange.models import Challenge, ChallengeTemplate, Item, UserItem
from achievement.models import Achievement
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create demo users with verification streaks, friendships, and achievements'

    def handle(self, *args, **kwargs):
        # Populate challenges first (ensures Items exist)
        from django.core.management import call_command
        self.stdout.write(self.style.WARNING('Running populate_challenges...'))
        call_command('populate_challenges')
        
        today = timezone.now().date()

        # =====================================================================
        # 1. DEMO USERS
        # =====================================================================
        demo_users_data = [
            {
                'username': 'runner',
                'email': 'runner@example.com',
                'bio': 'Disiplin her şeydir. 30 günlük koşu serimi asla bozmam.',
                'habits': [
                    {'name': 'Sabah Koşusu', 'target': 1, 'verified_days': 45, 'color': 'green'},
                    {'name': 'Kitap Okuma', 'target': 1, 'verified_days': 12, 'color': 'purple'},
                    {'name': 'Meditasyon', 'target': 1, 'verified_days': 5, 'color': 'blue'},
                ],
                'achievements': ['Erken Kalkan Yol Alır', 'Koşu Canavarı', 'Disiplin Abidesi'],
                'items': ['Golden Shoes', 'Heart Locket'],
            },
            {
                'username': 'drinker',
                'email': 'drinker@example.com',
                'bio': 'Sağlıklı yaşam ve bol su! 💧 Habit Tracker ile hayatım değişti.',
                'habits': [
                    {'name': 'Su İçme (3L)', 'target': 1, 'verified_days': 60, 'color': 'blue'},
                    {'name': 'Yoga', 'target': 1, 'verified_days': 20, 'color': 'pink'},
                    {'name': 'Sağlıklı Beslenme', 'target': 1, 'verified_days': 30, 'color': 'green'},
                ],
                'achievements': ['Su Ejderhası', 'Esneklik Ustası', '60 Günlük Başarı'],
                'items': ['Crystal Bottle'],
            },
            {
                'username': 'coder',
                'email': 'coder@example.com',
                'bio': 'Kod yazmak ve spor yapmak hobim değil, yaşam tarzım.',
                'habits': [
                    {'name': 'Kod Yazma', 'target': 1, 'verified_days': 100, 'color': 'orange'},
                    {'name': 'Gym', 'target': 1, 'verified_days': 3, 'color': 'yellow'},
                ],
                'achievements': ['Kod Dehası', '100 Günlük Maraton'],
                'items': ['Keyboard of Wisdom'],
            },
        ]

        created_users = {}

        for u_data in demo_users_data:
            # Clean slate — delete if exists
            User.objects.filter(username=u_data['username']).delete()
            
            user = User.objects.create_user(
                username=u_data['username'],
                email=u_data['email'],
                password='password123',
                bio=u_data['bio'],
            )
            created_users[u_data['username']] = user
            self.stdout.write(self.style.SUCCESS(f"User created: {user.username}"))

            # -----------------------------------------------------------------
            # 2. HABITS + COMPLETIONS + VERIFICATIONS
            # -----------------------------------------------------------------
            for h_data in u_data['habits']:
                habit = Habit.objects.create(
                    user=user,
                    name=h_data['name'],
                    habit_type='count',
                    target_count=h_data['target'],
                    frequency='daily',
                    color=h_data['color'],
                )

                verified_days = h_data['verified_days']
                
                for i in range(min(verified_days + 10, 60)):
                    history_date = today - timedelta(days=i)
                    
                    if i < verified_days:
                        # Completed + Verified day
                        HabitCompletion.objects.create(habit=habit, completed_at=history_date)
                        HabitVerification.objects.create(habit=habit, verified_date=history_date)
                        HabitHistory.objects.create(
                            habit=habit, date=history_date, count=h_data['target']
                        )
                    elif random.random() > 0.5:
                        # Some random incomplete history
                        HabitHistory.objects.create(
                            habit=habit, date=history_date,
                            count=random.randint(0, h_data['target'])
                        )
                
                # Let dynamic calculation set the fields
                habit.streak = habit.calculate_streak()
                habit.best_streak = habit.streak + random.randint(0, 5)
                habit.verification_streak = habit.calculate_verification_streak()
                habit.verified_count = verified_days
                habit.completed_count = habit.completions.count()
                habit.last_completed_date = today
                habit.last_proof_submission_date = today
                habit.count = h_data['target']  # "completed today"
                habit.save()
                
                self.stdout.write(f"  Habit: {habit.name} | streak={habit.streak} | v_streak={habit.verification_streak}")

            # -----------------------------------------------------------------
            # 3. ACHIEVEMENTS
            # -----------------------------------------------------------------
            for ach_name in u_data['achievements']:
                Achievement.objects.create(
                    user=user,
                    name=ach_name,
                    description=f"Awarded for exceptional performance in {ach_name}."
                )

            # -----------------------------------------------------------------
            # 4. INVENTORY ITEMS
            # -----------------------------------------------------------------
            for item_name in u_data['items']:
                try:
                    item = Item.objects.get(name=item_name)
                    UserItem.objects.create(user=user, item=item)
                except Item.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Item {item_name} not found!"))

        # =====================================================================
        # 5. FRIENDSHIPS WITH STREAKS
        # =====================================================================
        pairs = [
            ('runner', 'drinker', 15),
            ('runner', 'coder', 7),
            ('drinker', 'coder', 30),
        ]
        for from_name, to_name, streak in pairs:
            from_user = created_users[from_name]
            to_user = created_users[to_name]
            Friendship.objects.create(
                from_user=from_user,
                to_user=to_user,
                status=Friendship.Status.ACCEPTED,
                streak=streak,
                last_interaction_date=today,
            )
            self.stdout.write(f"  Friendship: {from_name} <-> {to_name} (streak={streak})")

        # =====================================================================
        # 6. COMPLETED CHALLENGES
        # =====================================================================
        templates = list(ChallengeTemplate.objects.all())
        if templates:
            for user in created_users.values():
                template = random.choice(templates)
                partner = None
                if template.challenge_type == 'DUO':
                    others = [u for u in created_users.values() if u != user]
                    partner = random.choice(others) if others else None
                
                Challenge.objects.create(
                    template=template,
                    creator=user,
                    partner=partner,
                    status='COMPLETED',
                    current_streak=template.duration_days,
                    start_date=today - timedelta(days=template.duration_days + 5),
                )

        # =====================================================================
        # 7. RECALCULATE XP & LEVELS
        # =====================================================================
        from users.gamification import GamificationEngine
        for user in created_users.values():
            total_xp = 0
            for habit in user.habits.all():
                # XP from verified days
                for _ in range(habit.verified_count):
                    xp, _, _ = GamificationEngine.calculate_full_reward(
                        GamificationEngine.BASE_VERIFY_XP,
                        habit.verification_streak,
                        0
                    )
                    total_xp += xp
            
            user.xp = total_xp
            user.level = GamificationEngine.calculate_level(total_xp)
            user.points = total_xp  # points = xp for now
            user.save(update_fields=['xp', 'level', 'points'])
            self.stdout.write(f"  {user.username}: XP={user.xp} Level={user.level}")

        self.stdout.write(self.style.SUCCESS("\n✅ Demo users, friendships, and rich history created!"))
