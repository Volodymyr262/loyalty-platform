"""
URL routing for the loyalty application API.
"""

from rest_framework.routers import DefaultRouter

from loyalty.views import CampaignViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaigns")

urlpatterns = router.urls
