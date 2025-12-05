"""
Unit tests for Loyalty Serializers.
"""

from loyalty.models import Customer, Transaction
from loyalty.serializers import CampaignSerializer, TransactionSerializer
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import UserFactory


class TestCampaignSerializer:
    """
    Test that Campaign model is correctly converted to JSON.
    """

    def test_campaign_serializer_contains_expected_fields(self):
        campaign = CampaignFactory(name="Test Campaign", points_value=100)

        serializer = CampaignSerializer(campaign)
        data = serializer.data

        assert data["id"] == campaign.id
        assert data["name"] == campaign.name
        assert data["points_value"] == 100

        assert "organization" not in data


class TestTransactionSerializer:
    """
    Test TransactionSerializer specific logic.
    """

    def test_serialization_output_format(self):
        """
        Ensure that when reading a transaction, we see 'points' but NOT 'amount'.
        """
        user = UserFactory()
        org = user.organization

        customer = Customer.objects.create(external_id="123", organization=org)

        transaction = Transaction.objects.create(
            customer=customer, organization=org, amount=500, transaction_type=Transaction.EARN, description="Test"
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data

        assert "id" in data
        assert "points" in data
        assert data["points"] == 500

        assert "amount" not in data
        assert "external_id" not in data

    def test_validation_required_fields(self):
        """
        Ensure serializer fails if required fields are missing.
        """
        data = {"description": "Just description"}
        serializer = TransactionSerializer(data=data)

        assert serializer.is_valid() is False
        assert "amount" in serializer.errors
        assert "external_id" in serializer.errors

    def test_amount_validation_format(self):
        """
        Ensure 'amount' accepts decimal/float strings.
        """
        data = {"external_id": "USER_1", "amount": "100.50"}
        serializer = TransactionSerializer(data=data)
        assert serializer.is_valid() is True
