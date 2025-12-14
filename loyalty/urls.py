"""
URL routing for the loyalty application API.
"""

from rest_framework.routers import DefaultRouter

from loyalty.views import AccrualViewSet, CampaignViewSet, RedemptionViewSet, RewardViewSet, TransactionHistoryViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaigns")
router.register(r"transactions", TransactionHistoryViewSet, basename="transactions")  # Read Only
router.register(r"accruals", AccrualViewSet, basename="accruals")  # Write Only (Earn)
router.register(r"redemption", RedemptionViewSet, basename="redemption")
router.register(r"rewards", RewardViewSet, basename="rewards")
urlpatterns = router.urls
