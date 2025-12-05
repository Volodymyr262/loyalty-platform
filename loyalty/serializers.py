"""
Serializers for the Loyalty application.
"""

from rest_framework import serializers

from loyalty.models import Campaign, Customer, Transaction


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
    Handles the logic of finding/creating a Customer by external_id.
    """

    external_id = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = ["id", "amount", "transaction_type", "description", "created_at", "external_id", "email"]
        read_only_fields = ["id", "created_at", "transaction_type"]

    def create(self, validated_data):
        """
        Custom create logic to link Transaction to a Customer.
        """
        external_id = validated_data.pop("external_id")
        email = validated_data.pop("email", None)

        organization = self.context["request"].user.organization

        customer, created = Customer.objects.get_or_create(
            organization=organization, external_id=external_id, defaults={"email": email}
        )

        transaction = Transaction.objects.create(customer=customer, transaction_type=Transaction.EARN, **validated_data)

        return transaction
