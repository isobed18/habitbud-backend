from django.urls import path
from .views import (
    ChallengeTemplateListView, JoinChallengeView, 
    ChallengeActiveListView, VerifyDuoView,
    AcceptChallengeView, WithdrawChallengeView,
    ChallengeCompletedListView, ItemShopView, BuyItemView
)

urlpatterns = [
    path('templates/', ChallengeTemplateListView.as_view(), name='challenge-templates'),
    path('join/<uuid:template_id>/', JoinChallengeView.as_view(), name='challenge-join'),
    path('accept/<uuid:challenge_id>/', AcceptChallengeView.as_view(), name='challenge-accept'),
    path('withdraw/<uuid:challenge_id>/', WithdrawChallengeView.as_view(), name='challenge-withdraw'),
    path('active/', ChallengeActiveListView.as_view(), name='challenge-active'),
    path('completed/', ChallengeCompletedListView.as_view(), name='challenge-completed'),
    path('<uuid:challenge_id>/verify/', VerifyDuoView.as_view(), name='challenge-verify'),
    path('shop/', ItemShopView.as_view(), name='item-shop'),
    path('shop/<uuid:item_id>/buy/', BuyItemView.as_view(), name='item-buy'),
]
