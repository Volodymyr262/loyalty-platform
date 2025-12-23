"""
Tests for Django Signals and Cache Invalidation.
"""

from django.core.cache import cache

from core.context import set_current_organization_id
from loyalty.services import get_active_campaigns
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import OrganizationFactory


class TestCampaignCacheInvalidation:
    """
    Verifies that modifying a Campaign correctly clears the Redis cache.
    """

    def teardown_method(self):
        cache.clear()

    def test_cache_is_populated_on_access(self):
        """
        Scenario: Calling get_active_campaigns should store data in cache.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        CampaignFactory(organization=org, is_active=True)

        cache_key = f"active_campaigns:{org.id}"

        # Cache should be empty initially (assuming teardown works)
        cache.delete(cache_key)
        assert cache.get(cache_key) is None

        # Call the service
        campaigns = get_active_campaigns(org.id)
        assert len(campaigns) == 1

        # Verify Redis has the data
        assert cache.get(cache_key) is not None
        assert len(cache.get(cache_key)) == 1

    def test_signal_clears_cache_on_save(self):
        """
        Scenario: Updating a campaign (via save()) should delete the cache key.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        campaign = CampaignFactory(organization=org, is_active=True)

        cache_key = f"active_campaigns:{org.id}"

        # Populate Cache
        get_active_campaigns(org.id)
        assert cache.get(cache_key) is not None

        # Modify Campaign (triggers post_save signal)
        campaign.name = "Updated Name"
        campaign.save()

        # Verify Cache is gone
        assert cache.get(cache_key) is None

        # Fetch again (should be fresh)
        updated_list = get_active_campaigns(org.id)
        assert updated_list[0].name == "Updated Name"

    def test_signal_clears_cache_on_delete(self):
        """
        Scenario: Deleting a campaign should delete the cache key.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        campaign = CampaignFactory(organization=org, is_active=True)

        cache_key = f"active_campaigns:{org.id}"

        # Populate Cache
        get_active_campaigns(org.id)
        assert cache.get(cache_key) is not None

        # Delete Campaign (triggers post_delete signal)
        campaign.delete()

        # Verify Cache is gone
        assert cache.get(cache_key) is None

        # Fetch again (should be empty)
        assert len(get_active_campaigns(org.id)) == 0
