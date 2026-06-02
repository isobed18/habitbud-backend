from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from habits.models import Habit, HabitConnection, HabitGroup, HabitGroupMember
from chat.models import Conversation, ChatMessage
from django.urls import reverse
from django.db.models import Count, Q
import datetime

User = get_user_model()

class HabitJunctionTests(APITestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username='alice', password='password123', email='alice@example.com')
        self.u2 = User.objects.create_user(username='bob', password='password123', email='bob@example.com')
        self.u3 = User.objects.create_user(username='charlie', password='password123', email='charlie@example.com')

        # Establish friendships
        from friends.models import Friendship
        Friendship.objects.create(from_user=self.u1, to_user=self.u2, status=Friendship.Status.ACCEPTED)
        Friendship.objects.create(from_user=self.u2, to_user=self.u3, status=Friendship.Status.ACCEPTED)
        Friendship.objects.create(from_user=self.u1, to_user=self.u3, status=Friendship.Status.ACCEPTED)

        # Alice's habit
        self.h1 = Habit.objects.create(
            user=self.u1,
            name='Water Intake',
            habit_type='count',
            target_count=5,
            frequency='daily'
        )

    def test_create_habit_connection_success(self):
        self.client.force_authenticate(user=self.u1)
        url = reverse('habit-connection-create')
        data = {
            'habit_id': str(self.h1.id),
            'friend_id': str(self.u2.id)
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HabitConnection.objects.count(), 1)
        
        conn = HabitConnection.objects.first()
        self.assertEqual(conn.user1, self.u1)
        self.assertEqual(conn.user2, self.u2)
        self.assertEqual(conn.status, 'pending')

    def test_create_duplicate_habit_connection_fails(self):
        self.client.force_authenticate(user=self.u1)
        # Create first connection
        HabitConnection.objects.create(
            user1=self.u1,
            user2=self.u2,
            habit1=self.h1,
            habit_name=self.h1.name,
            status='pending'
        )

        url = reverse('habit-connection-create')
        data = {
            'habit_id': str(self.h1.id),
            'friend_id': str(self.u2.id)
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_accept_habit_connection_auto_creates_habit(self):
        conn = HabitConnection.objects.create(
            user1=self.u1,
            user2=self.u2,
            habit1=self.h1,
            habit_name=self.h1.name,
            status='pending'
        )

        self.client.force_authenticate(user=self.u2)
        url = reverse('habit-connection-respond', kwargs={'connection_id': conn.id})
        res = self.client.post(url, {'action': 'accept'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        conn.refresh_from_db()
        self.assertEqual(conn.status, 'accepted')
        self.assertIsNotNone(conn.habit2)
        
        # Verify Bob has a matching habit now
        bob_habit = Habit.objects.filter(user=self.u2, name=self.h1.name).first()
        self.assertIsNotNone(bob_habit)
        self.assertEqual(bob_habit.target_count, self.h1.target_count)

    def test_accept_habit_connection_uses_existing_habit(self):
        # Bob already has the same habit
        bob_existing_habit = Habit.objects.create(
            user=self.u2,
            name='Water Intake',
            habit_type='count',
            target_count=8,
            frequency='daily'
        )

        conn = HabitConnection.objects.create(
            user1=self.u1,
            user2=self.u2,
            habit1=self.h1,
            habit_name=self.h1.name,
            status='pending'
        )

        self.client.force_authenticate(user=self.u2)
        url = reverse('habit-connection-respond', kwargs={'connection_id': conn.id})
        res = self.client.post(url, {'action': 'accept'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        conn.refresh_from_db()
        self.assertEqual(conn.status, 'accepted')
        # Check that it uses the existing habit and does not create a new one
        self.assertEqual(conn.habit2, bob_existing_habit)
        self.assertEqual(Habit.objects.filter(user=self.u2, name='Water Intake').count(), 1)

    def test_group_habit_creation_and_farming_prevention(self):
        # Create accepted duo connection first between Alice and Bob
        HabitConnection.objects.create(
            user1=self.u1,
            user2=self.u2,
            habit1=self.h1,
            habit_name=self.h1.name,
            status='accepted'
        )

        self.client.force_authenticate(user=self.u1)
        url = reverse('habit-group-create')
        data = {
            'name': 'Healthy Friends',
            'habit_id': str(self.h1.id),
            'participant_ids': [str(self.u2.id), str(self.u3.id)]
        }
        
        # Should fail because Alice and Bob already share a connection for 'Water Intake'
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("zaten 'Water Intake' alışkanlığı için bağlılar", res.data['error'])

    def test_mutual_verification_streak_and_rewards_duo(self):
        # Alice and Bob accepted connection
        h2 = Habit.objects.create(
            user=self.u2,
            name='Water Intake',
            habit_type='count',
            target_count=5,
            frequency='daily'
        )
        conn = HabitConnection.objects.create(
            user1=self.u1,
            user2=self.u2,
            habit1=self.h1,
            habit2=h2,
            habit_name=self.h1.name,
            status='accepted'
        )

        # Alice completes habit
        self.h1.count = 5
        self.h1.save()

        # Bob completes habit
        h2.count = 5
        h2.save()

        # Create conversation room
        conv = Conversation.objects.create()
        conv.participants.add(self.u1, self.u2)

        # Alice submits check
        msg1 = ChatMessage.objects.create(
            conversation=conv,
            sender=self.u1,
            message_type=ChatMessage.MessageType.PROOF,
            related_habit=self.h1,
            verification_status=ChatMessage.VerificationStatus.PENDING
        )

        # Bob verifies Alice's check
        self.client.force_authenticate(user=self.u2)
        url = reverse('check-verify', kwargs={'message_id': msg1.id})
        res = self.client.post(url, {'action': 'verify'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        conn.refresh_from_db()
        self.assertTrue(conn.user1_verified_today)
        self.assertFalse(conn.user2_verified_today)
        self.assertEqual(conn.streak, 0) # Not completed yet since Bob hasn't verified

        # Bob submits check
        msg2 = ChatMessage.objects.create(
            conversation=conv,
            sender=self.u2,
            message_type=ChatMessage.MessageType.PROOF,
            related_habit=h2,
            verification_status=ChatMessage.VerificationStatus.PENDING
        )

        # Alice verifies Bob's check
        self.client.force_authenticate(user=self.u1)
        url = reverse('check-verify', kwargs={'message_id': msg2.id})
        res = self.client.post(url, {'action': 'verify'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        conn.refresh_from_db()
        self.assertTrue(conn.user1_verified_today)
        self.assertTrue(conn.user2_verified_today)
        self.assertEqual(conn.streak, 1) # Both completed, duo streak is 1!

        # Verify XP & Diamond additions
        self.u1.refresh_from_db()
        self.u2.refresh_from_db()
        # Alice verifier rewards for verifying Bob (verifier: 10 XP + 1 Diamond)
        # Plus Duo complete bonus (+15 XP + 3 Diamonds)
        # Plus Bob check verify sender rewards (15 XP + 2 Diamonds)
        self.assertTrue(self.u1.xp > 0)
        self.assertTrue(self.u1.points > 0)

    def test_create_connection_prevented_by_existing_group(self):
        # Alice and Bob share a HabitGroup for 'Water Intake'
        conv = Conversation.objects.create(name='Group Conv', is_group=True)
        conv.participants.add(self.u1, self.u2, self.u3)
        
        group = HabitGroup.objects.create(
            name='Water Intake',
            creator=self.u1,
            conversation=conv
        )
        HabitGroupMember.objects.create(group=group, user=self.u1, habit=self.h1)
        
        h2 = Habit.objects.create(user=self.u2, name='Water Intake', habit_type='count', target_count=5)
        HabitGroupMember.objects.create(group=group, user=self.u2, habit=h2)
        
        # Now try to create a direct connection for 'Water Intake' between Alice and Bob
        self.client.force_authenticate(user=self.u1)
        url = reverse('habit-connection-create')
        data = {
            'habit_id': str(self.h1.id),
            'friend_id': str(self.u2.id)
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("zaten ortak bir 'Water Intake' grubundasınız", res.data['error'])

    def test_group_reserve_and_automatic_save(self):
        # Create group
        conv = Conversation.objects.create(name='Group Conv', is_group=True)
        conv.participants.add(self.u1, self.u2, self.u3)
        group = HabitGroup.objects.create(name='Water Intake', creator=self.u1, conversation=conv, streak=3)
        
        m1 = HabitGroupMember.objects.create(group=group, user=self.u1, habit=self.h1)
        h2 = Habit.objects.create(user=self.u2, name='Water Intake', habit_type='count', target_count=5)
        m2 = HabitGroupMember.objects.create(group=group, user=self.u2, habit=h2)
        h3 = Habit.objects.create(user=self.u3, name='Water Intake', habit_type='count', target_count=5)
        m3 = HabitGroupMember.objects.create(group=group, user=self.u3, habit=h3)

        # Give Bob a freeze and reserve it
        self.u2.streak_freezes = 2
        self.u2.save()
        
        self.client.force_authenticate(user=self.u2)
        url = reverse('group-reserve', kwargs={'conversation_id': conv.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        self.u2.refresh_from_db()
        self.assertEqual(self.u2.streak_freezes, 1)
        self.assertEqual(group.conversation.reserves.count(), 1)
        
        # Withdraw reserve
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.u2.refresh_from_db()
        self.assertEqual(self.u2.streak_freezes, 2)
        self.assertEqual(group.conversation.reserves.count(), 0)

        # Reserve again
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Simulate day change without completing habits yesterday
        # Bob's reserve should save the group streak
        group.last_reset_date = datetime.date.today() - datetime.timedelta(days=1)
        group.save()
        
        group.check_and_reset_progress()
        group.refresh_from_db()
        
        # Streak stays 3, and a freeze usage was recorded
        self.assertEqual(group.streak, 3)
        self.assertEqual(group.conversation.freeze_usages.count(), 1)
        # Reserve is used
        reserve = group.conversation.reserves.first()
        self.assertTrue(reserve.used)
        self.assertFalse(reserve.can_withdraw)

    def test_reactive_streak_recovery(self):
        conv = Conversation.objects.create()
        conv.participants.add(self.u1, self.u2)

        h2 = Habit.objects.create(user=self.u2, name='Water Intake', habit_type='count', target_count=5)
        conn = HabitConnection.objects.create(
            user1=self.u1, user2=self.u2, habit1=self.h1, habit2=h2,
            habit_name=self.h1.name, status='accepted', streak=5
        )
        
        # Day resets without completions -> streak becomes 0, eligible for recovery
        conn.last_reset_date = datetime.date.today() - datetime.timedelta(days=1)
        conn.save()
        
        conn.check_and_reset_progress()
        conn.refresh_from_db()
        self.assertEqual(conn.streak, 0)
        self.assertEqual(conn.recovery_eligible_date, datetime.date.today() - datetime.timedelta(days=1))
        
        # Alice recovers it reactively
        self.u1.streak_freezes = 1
        self.u1.save()
        
        conv = Conversation.objects.annotate(p_count=Count('participants')).filter(
            participants=self.u1
        ).filter(
            participants=self.u2
        ).filter(p_count=2, is_group=False).first()
        
        self.client.force_authenticate(user=self.u1)
        url = reverse('streak-recovery', kwargs={'conversation_id': conv.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        conn.refresh_from_db()
        self.assertEqual(conn.streak, 5) # Restored!
        self.assertIsNone(conn.recovery_eligible_date)
        
        self.u1.refresh_from_db()
        self.assertEqual(self.u1.streak_freezes, 0)

    def test_pending_leave_and_adaptation_mode(self):
        conv = Conversation.objects.create(name='Group Conv', is_group=True)
        conv.participants.add(self.u1, self.u2, self.u3)
        group = HabitGroup.objects.create(name='Water Intake', creator=self.u1, conversation=conv, streak=4)
        
        m1 = HabitGroupMember.objects.create(group=group, user=self.u1, habit=self.h1)
        h2 = Habit.objects.create(user=self.u2, name='Water Intake', habit_type='count', target_count=5)
        m2 = HabitGroupMember.objects.create(group=group, user=self.u2, habit=h2)
        h3 = Habit.objects.create(user=self.u3, name='Water Intake', habit_type='count', target_count=5)
        m3 = HabitGroupMember.objects.create(group=group, user=self.u3, habit=h3)

        # Bob requests to leave
        self.client.force_authenticate(user=self.u2)
        url = reverse('habit-group-leave', kwargs={'group_id': group.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        m2.refresh_from_db()
        self.assertIsNotNone(m2.pending_leave_at)
        
        # Simulate 24 hours later
        from django.utils import timezone
        m2.pending_leave_at = timezone.now() - datetime.timedelta(hours=25)
        m2.save()
        
        group.check_and_reset_progress()
        group.refresh_from_db()
        
        # Bob should be deleted from members, and adaptation mode active for 7 days
        self.assertEqual(group.memberships.count(), 2)
        self.assertTrue(group.adaptation_mode_active)
        self.assertEqual(group.adaptation_mode_until, datetime.date.today() + datetime.timedelta(days=7))
        
        # If remaining members complete habits today, streak remains frozen (4)
        self.h1.count = 5
        self.h1.save()
        h3.count = 5
        h3.save()
        
        # Create proof verification
        msg1 = ChatMessage.objects.create(
            conversation=conv, sender=self.u1, message_type=ChatMessage.MessageType.PROOF,
            related_habit=self.h1, verification_status=ChatMessage.VerificationStatus.PENDING
        )
        self.client.force_authenticate(user=self.u3)
        res = self.client.post(reverse('check-verify', kwargs={'message_id': msg1.id}), {'action': 'verify'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        msg2 = ChatMessage.objects.create(
            conversation=conv, sender=self.u3, message_type=ChatMessage.MessageType.PROOF,
            related_habit=h3, verification_status=ChatMessage.VerificationStatus.PENDING
        )
        self.client.force_authenticate(user=self.u1)
        res = self.client.post(reverse('check-verify', kwargs={'message_id': msg2.id}), {'action': 'verify'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        group.refresh_from_db()
        self.assertEqual(group.streak, 4) # Streak frozen!

    def test_adaptation_mode_zero_tolerance(self):
        conv = Conversation.objects.create(name='Group Conv', is_group=True)
        conv.participants.add(self.u1, self.u2)
        group = HabitGroup.objects.create(
            name='Water Intake', creator=self.u1, conversation=conv, streak=4,
            adaptation_mode_active=True, adaptation_mode_until=datetime.date.today() + datetime.timedelta(days=6)
        )
        
        m1 = HabitGroupMember.objects.create(group=group, user=self.u1, habit=self.h1)
        h3 = Habit.objects.create(user=self.u2, name='Water Intake', habit_type='count', target_count=5)
        m3 = HabitGroupMember.objects.create(group=group, user=self.u2, habit=h3)
        
        # Day changes without all members completing
        group.last_reset_date = datetime.date.today() - datetime.timedelta(days=1)
        group.save()
        
        group.check_and_reset_progress()
        group.refresh_from_db()
        
        # Zero tolerance -> streak becomes 0, adaptation mode deactivates
        self.assertEqual(group.streak, 0)
        self.assertFalse(group.adaptation_mode_active)

