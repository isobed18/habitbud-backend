from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Item, ChallengeTemplate, Challenge, UserItem
from .serializers import ItemSerializer, ChallengeTemplateSerializer, ChallengeSerializer
from django.utils import timezone
from users.services import UserService

class ChallengeTemplateListView(generics.ListAPIView):
    """List all system challenges (30 days running, etc)."""
    queryset = ChallengeTemplate.objects.all()
    serializer_class = ChallengeTemplateSerializer
    permission_classes = [IsAuthenticated]

class JoinChallengeView(views.APIView):
    """Start a challenge (Solo or invite friend for Duo)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, template_id):
        template = get_object_or_404(ChallengeTemplate, id=template_id)
        partner_id = request.data.get('partner_id')

        # 1. Type-specific Validation
        if template.challenge_type == 'SOLO' and partner_id:
            return Response({"error": "Solo challenges cannot have a partner."}, status=status.HTTP_400_BAD_REQUEST)
        
        if template.challenge_type == 'DUO' and not partner_id:
            return Response({"error": "partner_id is required for Duo challenges."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Check if already in this challenge (Active, Pending, or Completed)
        existing = Challenge.objects.filter(
            creator=request.user, 
            template=template, 
            status__in=['ACTIVE', 'PENDING', 'COMPLETED']
        ).exists()
        
        if existing:
            return Response({"error": "You search already completed or actively participating in this challenge."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Create Process
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if template.challenge_type == 'SOLO':
            challenge = Challenge.objects.create(
                template=template,
                creator=request.user,
                status='ACTIVE'
            )
            # AUTO-CREATE HABIT for SOLO
            from habits.models import Habit
            Habit.objects.create(
                user=request.user,
                name=template.predefined_habit_name,
                habit_type='count',
                target_count=1,
                frequency='daily',
                challenge=challenge,
                is_challenge_habit=True
            )
            return Response(ChallengeSerializer(challenge).data, status=status.HTTP_201_CREATED)

        else:  # DUO
            partner = get_object_or_404(User, id=partner_id)
            if partner == request.user:
                return Response({"error": "You cannot be your own partner."}, status=status.HTTP_400_BAD_REQUEST)
            
            # --- MUTUAL AUTO-ACCEPT LOGIC ---
            reverse_invite = Challenge.objects.filter(
                creator=partner, 
                partner=request.user, 
                template=template, 
                status='PENDING'
            ).first()

            if reverse_invite:
                reverse_invite.status = 'ACTIVE'
                reverse_invite.save()

                # AUTO-CREATE HABITS for BOTH
                from habits.models import Habit
                for u in [reverse_invite.creator, reverse_invite.partner]:
                    Habit.objects.create(
                        user=u,
                        name=template.predefined_habit_name,
                        habit_type='count',
                        target_count=1,
                        frequency='daily',
                        challenge=reverse_invite,
                        is_challenge_habit=True
                    )
                return Response(ChallengeSerializer(reverse_invite).data, status=status.HTTP_200_OK)
            
            # NORMAL DUO INVITE (Non-mutual)
            challenge = Challenge.objects.create(
                template=template,
                creator=request.user,
                partner=partner,
                status='PENDING'
            )
            return Response(ChallengeSerializer(challenge).data, status=status.HTTP_201_CREATED)

class AcceptChallengeView(views.APIView):
    """Accept or Reject a Duo challenge invitation."""
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        challenge = get_object_or_404(Challenge, id=challenge_id, partner=request.user, status='PENDING')
        action = request.data.get('action') # 'accept' or 'reject'

        if action == 'accept':
            challenge.status = 'ACTIVE'
            challenge.save()

            # AUTO-CREATE HABITS for BOTH SIDES on Duo Acceptance
            from habits.models import Habit
            # Creator's Habit
            Habit.objects.create(
                user=challenge.creator,
                name=challenge.template.predefined_habit_name,
                habit_type='count',
                target_count=1,
                frequency='daily',
                challenge=challenge,
                is_challenge_habit=True
            )
            # Partner's Habit
            Habit.objects.create(
                user=challenge.partner,
                name=challenge.template.predefined_habit_name,
                habit_type='count',
                target_count=1,
                frequency='daily',
                challenge=challenge,
                is_challenge_habit=True
            )

            return Response({"status": "Challenge accepted.", "data": ChallengeSerializer(challenge).data})
        elif action == 'reject':
            challenge.status = 'REJECTED'
            challenge.save()
            return Response({"status": "Challenge rejected."})
        else:
            return Response({"error": "Invalid action. Use 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

class WithdrawChallengeView(views.APIView):
    """Allow creator to cancel a PENDING invitation."""
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        challenge = get_object_or_404(Challenge, id=challenge_id, creator=request.user, status='PENDING')
        challenge.delete()
        return Response({"status": "Challenge invitation withdrawn."}, status=status.HTTP_200_OK)

class ChallengeActiveListView(generics.ListAPIView):
    """List active and pending challenges for the current user."""
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Challenge.objects.filter(
            (Q(creator=self.request.user) | Q(partner=self.request.user)),
            status__in=['ACTIVE', 'PENDING']
        ).order_by('status', '-start_date')


class VerifyDuoView(views.APIView):
    """Mutual verification for DUO challenges."""
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        challenge = get_object_or_404(Challenge, id=challenge_id, status='ACTIVE')
        user = request.user

        if challenge.template.challenge_type != 'DUO':
            return Response({"error": "Only Duo challenges require mutual verification."}, status=status.HTTP_400_BAD_REQUEST)

        if user == challenge.creator:
            challenge.creator_verified_partner = True
        elif user == challenge.partner:
            challenge.partner_verified_creator = True
        else:
            return Response({"error": "Not a participant."}, status=status.HTTP_403_FORBIDDEN)

        challenge.save()
        
        # Check if both verified and both completed (to advance streak)
        from .services import ChallengeService
        ChallengeService._check_and_advance(challenge)

        return Response(ChallengeSerializer(challenge).data)

class UserInventoryView(generics.ListAPIView):
    """List items owned by the current user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_items = UserItem.objects.filter(user=request.user).select_related('item')
        data = []
        for ui in user_items:
            data.append({
                "id": ui.item.id,
                "name": ui.item.name,
                "description": ui.item.description,
                "image": ui.item.image.url if ui.item.image else None,
                "rarity": ui.item.rarity,
                "obtained_at": ui.obtained_at
            })
        return Response(data)

class ChallengeCompletedListView(generics.ListAPIView):
    """List successfully completed challenges for the current user."""
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Challenge.objects.filter(
            (Q(creator=self.request.user) | Q(partner=self.request.user)),
            status='COMPLETED'
        ).order_by('-start_date')
