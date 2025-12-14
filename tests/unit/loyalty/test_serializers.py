"""
Unit tests for Loyalty Serializers.
"""

from loyalty.models import Customer, Transaction
from loyalty.serializers import AccrualSerializer, CampaignSerializer, TransactionReadSerializer
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import UserFactory


class TestCampaignSerializer:
    """
    Test that Campaign model is correctly converted to JSON.
    """

    def test_campaign_serializer_contains_expected_fields(self):
        campaign = CampaignFactory(
            name="Test Campaign", points_value=100, reward_type="bonus", rules={"min_amount": 1000}
        )

        serializer = CampaignSerializer(campaign)
        data = serializer.data

        assert data["id"] == campaign.id
        assert data["name"] == campaign.name
        assert data["points_value"] == 100
        assert data["reward_type"] == "bonus"
        assert data["rules"] == {"min_amount": 1000}

        assert "organization" not in data


class TestTransactionSerializers:
    """
    Tests for the split serializers: TransactionReadSerializer and AccrualSerializer.
    """

    def test_read_serializer_output_format(self):
        """
        Test TransactionReadSerializer (GET).
        It should return 'amount', 'transaction_type', etc.
        """
        user = UserFactory()
        org = user.organization
        customer = Customer.objects.create(external_id="123", organization=org)

        transaction = Transaction.objects.create(
            customer=customer, organization=org, amount=500, transaction_type=Transaction.EARN, description="Test"
        )

        serializer = TransactionReadSerializer(transaction)
        data = serializer.data

        assert "id" in data
        assert "points" in data
        assert data["points"] == 500
        assert "transaction_type" in data

    def test_accrual_validation_required_fields(self):
        """
        Test AccrualSerializer (POST).
        Ensure it fails if required fields (amount, external_id) are missing.
        """
        data = {"description": "Just description"}

        serializer = AccrualSerializer(data=data)

        assert serializer.is_valid() is False
        assert "amount" in serializer.errors
        assert "external_id" in serializer.errors

    def test_accrual_amount_validation_format(self):
        """
        Test AccrualSerializer (POST).
        Ensure 'amount' accepts decimal strings.
        """
        data = {"external_id": "USER_1", "amount": "100.50"}
        serializer = AccrualSerializer(data=data)

        assert serializer.is_valid() is True

    def test_accrual_negative_amount_validation(self):
        """
        Test AccrualSerializer (POST).
        Ensure negative amounts are rejected (Validation we added specifically for Accruals).
        """
        data = {"external_id": "USER_1", "amount": "-100.00"}
        serializer = AccrualSerializer(data=data)

        assert serializer.is_valid() is False
        assert "amount" in serializer.errors
        assert "must be positive" in str(serializer.errors["amount"])
