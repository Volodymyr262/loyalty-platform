"""
Unit tests for Loyalty Serializers.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from core.context import set_current_organization_id
from loyalty.models import Transaction
from loyalty.serializers import (
    AccrualSerializer,
    CampaignSerializer,
    CustomerSerializer,
    RedemptionSerializer,
    TransactionReadSerializer,
)
from tests.factories.loyalty import CampaignFactory, CustomerFactory, RewardFactory, TransactionFactory
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
        transaction = TransactionFactory(amount=500, transaction_type=Transaction.EARN, description="Test")

        serializer = TransactionReadSerializer(transaction)
        data = serializer.data

        assert "id" in data
        assert "points" in data
        assert data["points"] == 500
        assert "transaction_type" in data
        assert data["transaction_type"] == Transaction.EARN

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

    # --- NEW TESTS FOR CREATE METHOD ---

    def test_accrual_create_success(self):
        """
        Test actual creation of transaction via Serializer.save().
        This covers AccrualSerializer.create method.
        """
        # 1. Setup User and Context (Serializer needs request.user.organization)
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        # Mocking the request object
        request = MagicMock()
        request.user = user
        context = {"request": request}

        # 2. Input Data
        data = {"external_id": "new_customer_123", "amount": "100.00", "description": "Test Accrual"}

        # 3. Save
        serializer = AccrualSerializer(data=data, context=context)
        assert serializer.is_valid()
        transaction = serializer.save()

        # 4. Verify
        assert transaction.id is not None
        assert transaction.amount == 100  # Default 1:1 calc
        assert transaction.customer.external_id == "new_customer_123"
        assert transaction.customer.organization == user.organization

    def test_accrual_create_handles_service_errors(self):
        """
        Test that DjangoValidationError from service is converted to DRF ValidationError.
        """
        user = UserFactory()
        request = MagicMock()
        request.user = user
        context = {"request": request}

        data = {"external_id": "cust_1", "amount": "100.00"}

        # We mock the service to raise a validation error
        with patch("loyalty.serializers.LoyaltyService.process_transaction") as mock_service:
            mock_service.side_effect = DjangoValidationError("Service Error")

            serializer = AccrualSerializer(data=data, context=context)
            assert serializer.is_valid()

            # Should raise DRF ValidationError
            try:
                serializer.save()
                pytest.fail("Should have raised ValidationError")
            except DRFValidationError as e:
                assert "Service Error" in str(e.detail)


class TestRedemptionSerializer:
    """
    Tests for RedemptionSerializer (Validation and Creation).
    """

    def test_validate_success(self):
        """
        Scenario: Valid customer and valid active reward.
        Expected: Validation passes.
        """
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        customer = CustomerFactory(organization=user.organization)
        reward = RewardFactory(organization=user.organization, is_active=True)

        data = {"customer_external_id": customer.external_id, "reward_id": reward.id}

        request = MagicMock()
        request.user = user
        context = {"request": request}

        serializer = RedemptionSerializer(data=data, context=context)
        assert serializer.is_valid() is True

    def test_validate_reward_not_found(self):
        """
        Scenario: Reward ID does not exist.
        Expected: ValidationError.
        """
        user = UserFactory()
        request = MagicMock()
        request.user = user

        data = {"customer_external_id": "any", "reward_id": 9999}  # Invalid ID

        serializer = RedemptionSerializer(data=data, context={"request": request})
        assert serializer.is_valid() is False
        assert "Reward not found" in str(serializer.errors)

    def test_validate_reward_inactive(self):
        """
        Scenario: Reward exists but is_active=False.
        Expected: ValidationError.
        """
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        reward = RewardFactory(organization=user.organization, is_active=False)

        data = {"customer_external_id": "any", "reward_id": reward.id}

        request = MagicMock()
        request.user = user

        serializer = RedemptionSerializer(data=data, context={"request": request})
        assert serializer.is_valid() is False
        assert "inactive" in str(serializer.errors)

    def test_validate_customer_not_found(self):
        """
        Scenario: Customer ID does not exist for this tenant.
        Expected: ValidationError.
        """
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        reward = RewardFactory(organization=user.organization)

        data = {"customer_external_id": "non_existent_client", "reward_id": reward.id}

        request = MagicMock()
        request.user = user

        serializer = RedemptionSerializer(data=data, context={"request": request})
        assert serializer.is_valid() is False
        assert "Customer not found" in str(serializer.errors)

    def test_create_redemption_success(self):
        """
        Scenario: User has enough points.
        Expected: Transaction created with negative amount.
        """
        # 1. Setup
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        # Customer with 100 points
        customer = CustomerFactory(organization=user.organization)
        TransactionFactory(customer=customer, amount=100)

        # Reward costs 50 points
        reward = RewardFactory(organization=user.organization, point_cost=50)

        request = MagicMock()
        request.user = user
        context = {"request": request}

        data = {"customer_external_id": customer.external_id, "reward_id": reward.id}

        # 2. Execute
        serializer = RedemptionSerializer(data=data, context=context)
        assert serializer.is_valid()
        tx = serializer.save()

        # 3. Assert
        assert tx.amount == -50
        assert tx.customer == customer
        assert "Redeemed" in tx.description

    def test_create_redemption_insufficient_funds(self):
        """
        Scenario: User has 0 points, reward costs 50.
        Expected: Service raises ValidationError -> Serializer raises DRF ValidationError.
        """
        user = UserFactory()
        set_current_organization_id(user.organization.id)

        customer = CustomerFactory(organization=user.organization)
        # 0 Points

        reward = RewardFactory(organization=user.organization, point_cost=50)

        request = MagicMock()
        request.user = user
        context = {"request": request}

        data = {"customer_external_id": customer.external_id, "reward_id": reward.id}

        serializer = RedemptionSerializer(data=data, context=context)
        assert serializer.is_valid()

        # The save() method calls service.process_transaction(), which checks balance
        try:
            serializer.save()
            pytest.fail("Should fail due to insufficient funds")
        except DRFValidationError as e:
            assert "Insufficient funds" in str(e.detail)


class TestCustomerSerializer:
    def test_serializer_includes_calculated_balance(self):
        """
        Serializer must include a 'balance' field derived from transactions.
        """
        # Setup data
        customer = CustomerFactory()

        set_current_organization_id(customer.organization.id)

        # Add transactions: +100, +50, -30 = 120 Total
        TransactionFactory(customer=customer, amount=100, transaction_type=Transaction.EARN)
        TransactionFactory(customer=customer, amount=50, transaction_type=Transaction.EARN)
        TransactionFactory(customer=customer, amount=-30, transaction_type=Transaction.SPEND)

        # Serialize
        serializer = CustomerSerializer(customer)
        data = serializer.data

        # Assertions
        assert "id" in data
        assert "balance" in data
        assert float(data["balance"]) == 120.00
