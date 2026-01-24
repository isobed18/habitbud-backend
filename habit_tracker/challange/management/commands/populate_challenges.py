from django.core.management.base import BaseCommand
from challange.models import Item, ChallengeTemplate

class Command(BaseCommand):
    help = 'Populate initial items and challenge templates'

    def handle(self, *args, **kwargs):
        # 1. Create Items
        items_data = [
            {'name': 'Golden Shoes', 'description': 'The ultimate running gear.', 'rarity': 'epic'},
            {'name': 'Crystal Bottle', 'description': 'Hydration is key.', 'rarity': 'rare'},
            {'name': 'Keyboard of Wisdom', 'description': 'Code like a god.', 'rarity': 'epic'},
            {'name': 'Heart Locket', 'description': 'Symbol of legendary friendship.', 'rarity': 'legendary'},
        ]
        
        items = {}
        for item_data in items_data:
            item, created = Item.objects.get_or_create(
                name=item_data['name'], 
                defaults={'description': item_data['description'], 'rarity': item_data['rarity']}
            )
            items[item.name] = item
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Item: {item.name}'))

        # 2. Cleanup Existing Templates to avoid confusion
        ChallengeTemplate.objects.all().delete()
        self.stdout.write(self.style.WARNING('Cleared existing challenge templates.'))

        # 3. Create Challenge Templates
        templates_data = [
            {
                'name': '30 Day Runner', 
                'description': 'Run for 30 consecutive days. Rewards: Golden Shoes + 500 XP.', 
                'predefined_habit_name': 'Running',
                'challenge_type': 'SOLO', 
                'duration_days': 30, 
                'reward_xp': 500, 
                'reward_points': 500,
                'reward_item': items['Golden Shoes']
            },
            {
                'name': '7 Day Water Warrior', 
                'description': 'Drink 3L water daily for 7 days. Quick start reward.', 
                'predefined_habit_name': 'Drinking Water',
                'challenge_type': 'SOLO', 
                'duration_days': 7, 
                'reward_xp': 100, 
                'reward_points': 100,
                'reward_item': items['Crystal Bottle']
            },
            {
                'name': '7 Day Productivity Duo', 
                'description': 'Duo: Code with your buddy for 7 days. Easy start.', 
                'predefined_habit_name': 'Coding',
                'challenge_type': 'DUO', 
                'duration_days': 7, 
                'reward_xp': 150, 
                'reward_points': 150,
                'reward_item': items['Keyboard of Wisdom']
            },
            {
                'name': '30 Day Study Buddy', 
                'description': 'Duo Challenge: Study with a friend daily. Both must complete and verify each other.', 
                'predefined_habit_name': 'Studying',
                'challenge_type': 'DUO', 
                'duration_days': 30, 
                'reward_xp': 1000, 
                'reward_points': 1000,
                'reward_item': items['Heart Locket']
            },
            {
                'name': '30 Day Gym Rats', 
                'description': 'Duo: Hit the gym with your partner for a month straight.', 
                'predefined_habit_name': 'Gym',
                'challenge_type': 'DUO', 
                'duration_days': 30, 
                'reward_xp': 1200, 
                'reward_points': 1200,
                'reward_item': items['Golden Shoes']
            },
        ]

        for t_data in templates_data:
            template, created = ChallengeTemplate.objects.get_or_create(
                name=t_data['name'],
                defaults=t_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Template: {template.name}'))
            else:
                # Update existing for development
                for key, value in t_data.items():
                    setattr(template, key, value)
                template.save()
                self.stdout.write(f'Updated Template: {template.name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated challange data.'))
