"""
Serializers for the Loyalty application.
"""

from rest_framework import serializers

from loyalty.models import Campaign, Customer, Transaction
from loyalty.services import calculate_points


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for the Campaign model.
    """

    class Meta:
        model = Campaign
        fields = ["id", "name", "description", "points_value", "is_active"]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transactions.
    Money comes IN ('amount'), Points go OUT ('points').
    """

    external_id = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    amount = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True)

    points = serializers.IntegerField(source="amount", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "amount", "points", "transaction_type", "description", "created_at", "external_id", "email"]
        read_only_fields = ["id", "created_at", "transaction_type", "points"]

    def create(self, validated_data):
        external_id = validated_data.pop("external_id")
        email = validated_data.pop("email", None)

        money_amount = validated_data.pop("amount")

        organization = self.context["request"].user.organization

        customer, created = Customer.objects.get_or_create(
            organization=organization, external_id=external_id, defaults={"email": email}
        )

        points_to_accrue = calculate_points(money_amount, organization)

        transaction = Transaction.objects.create(
            customer=customer,
            transaction_type=Transaction.EARN,
            amount=points_to_accrue,
            description=validated_data.get("description", ""),
        )

        return transaction
