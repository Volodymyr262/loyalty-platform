"""
URL routing for the loyalty application API.
"""

from rest_framework.routers import DefaultRouter

from loyalty.views import CampaignViewSet, RewardViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaigns")
router.register(r"transactions", TransactionViewSet, basename="transactions")
router.register(r"rewards", RewardViewSet, basename="rewards")
urlpatterns = router.urls
