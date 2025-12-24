"""
Serializers for the Loyalty application.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from loyalty.models import Campaign, Customer, Reward, Transaction
from loyalty.services import LoyaltyService, calculate_points


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for the Campaign model.
    """

    class Meta:
        model = Campaign
        fields = ["id", "name", "description", "points_value", "reward_type", "rules", "is_active"]


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["id", "name", "description", "point_cost", "is_active"]
        read_only_fields = ["id"]


class TransactionReadSerializer(serializers.ModelSerializer):
    points = serializers.IntegerField(source="amount", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "points", "transaction_type", "description", "created_at", "customer"]


class AccrualSerializer(serializers.ModelSerializer):
    """
    Serializer for Accruals (Earning points).
    """

    # INPUT: Money (only for write). .
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True)

    # OUTPUT: points (only for read).
    points = serializers.IntegerField(source="amount", read_only=True)

    external_id = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = ["id", "external_id", "amount", "points", "description", "email"]
        read_only_fields = ["id", "points"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Accrual amount must be positive.")
        return value

    def _get_organization(self):
        request = self.context.get("request")
        if request.auth and hasattr(request.auth, "organization"):
            return request.auth.organization
        if request.user and request.user.is_authenticated:
            return request.user.organization
        raise serializers.ValidationError("Organization context missing.")

    def create(self, validated_data):
        external_id = validated_data.pop("external_id")
        email = validated_data.pop("email", None)
        money_amount = validated_data.pop("amount")

        organization = self._get_organization()

        customer, _ = Customer.objects.get_or_create(
            organization=organization, external_id=external_id, defaults={"email": email}
        )

        points = calculate_points(money_amount, customer)
        service = LoyaltyService()

        try:
            transaction = service.process_transaction(
                customer=customer, amount=points, description=validated_data.get("description", "")
            )
        except DjangoValidationError as e:
            raise serializers.ValidationError({"detail": e.messages if hasattr(e, "messages") else str(e)}) from e

        return transaction


class RedemptionSerializer(serializers.Serializer):
    """
    Serializer specifically for spending points.
    """

    customer_external_id = serializers.CharField()
    reward_id = serializers.IntegerField()

    def validate(self, data):
        request = self.context.get("request")

        if request.auth and hasattr(request.auth, "organization"):
            organization = request.auth.organization
        elif request.user and request.user.is_authenticated:
            organization = request.user.organization
        else:
            raise serializers.ValidationError("Authentication required.")

        # 1. Validate Reward
        try:
            reward = Reward.objects.get(id=data["reward_id"], organization=organization)
            if not reward.is_active:
                raise serializers.ValidationError("This reward is currently inactive.")
            data["reward"] = reward
        except Reward.DoesNotExist as e:  # Catch the exception as variable 'e'
            raise serializers.ValidationError("Reward not found.") from e

        # 2. Validate Customer
        try:
            customer = Customer.objects.get(external_id=data["customer_external_id"], organization=organization)
            data["customer"] = customer
        except Customer.DoesNotExist as e:  # Catch the exception as variable 'e'
            raise serializers.ValidationError("Customer not found.") from e

        return data

    def create(self, validated_data):
        customer = validated_data["customer"]
        reward = validated_data["reward"]
        points_to_spend = -reward.point_cost

        service = LoyaltyService()

        try:
            transaction = service.process_transaction(
                customer=customer, amount=points_to_spend, description=f"Redeemed: {reward.name}"
            )
            return transaction

        except DjangoValidationError as e:
            raise serializers.ValidationError({"detail": e.messages if hasattr(e, "messages") else str(e)}) from e


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.
    Read-only view of customer data including calculated balance.
    """

    # Fetch the balance dynamically using the 'get_balance' method on the model
    balance = serializers.DecimalField(source="get_balance", read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = Customer
        fields = ["id", "external_id", "email", "balance"]
