from rest_framework import serializers

from core.models import *

from django.contrib.auth.models import User


class ClientSerializer(serializers.ModelSerializer):
    # Write-only: accept a provider's referral code when a patient registers.
    referred_by_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "user",
            "email",
            "first_name",
            "last_name",
            "type",
            "date_of_birth",
            "gender",
            "height",
            "weight",
            "ethnicity",
            "allergies",
            "dietary_recall",
            "dietary_typicality",
            "dietary_preference_mode",
            "preferred_cuisines",
            "avoided_cuisines",
            "weekly_exercise_routine",
            "exercise_days_per_week",
            "exercise_types",
            "provider_notes",
            "sport",
            "health_conditions",
            "dietary_preferences",
            "fitness_goal",
            "nutritional_goal",
            # Referral system
            "referral_code",
            "referred_by",
            "referred_by_code",
        ]
        read_only_fields = ["referral_code", "referred_by"]

    def create(self, validated_data):
        referred_by_code = validated_data.pop("referred_by_code", None)
        instance = super().create(validated_data)
        if referred_by_code:
            try:
                provider = Client.objects.get(referral_code=referred_by_code.upper())
                instance.referred_by = provider
                instance.save()
            except Client.DoesNotExist:
                pass  # Invalid code — silently ignore
        return instance

class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = "__all__"


class TestKitSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestKit
        fields = "__all__"


class DeliveryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryEvent
        fields = ["id", "event_type", "title", "description", "timestamp", "is_completed"]


class OrderSerializer(serializers.ModelSerializer):
    """Used for list views — lightweight."""
    test_kit_name = serializers.CharField(source="test_kit.name", read_only=True)
    biomarker_count = serializers.IntegerField(source="test_kit.biomarker_count", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "client", "test_kit", "test_kit_name", "biomarker_count",
            "order_number", "order_date", "status", "tracking_number",
            "created_at", "updated_at",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Used for detail views — includes nested kit and delivery events."""
    test_kit = TestKitSerializer(read_only=True)
    delivery_events = DeliveryEventSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "client", "test_kit", "order_number", "order_date",
            "status", "tracking_number", "delivery_events",
            "created_at", "updated_at",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Used for creating orders."""
    class Meta:
        model = Order
        fields = ["client", "test_kit", "order_number", "tracking_number"]


# ── Checkout / Payment ──────────────────────────────────────────────────


class BillingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingAddress
        fields = ["street_address", "city", "state", "zip_code"]


class PaymentInfoSerializer(serializers.ModelSerializer):
    billing_address = BillingAddressSerializer(read_only=True)

    class Meta:
        model = PaymentInfo
        fields = [
            "id", "cardholder_name", "card_last_four", "card_brand",
            "expiry_month", "expiry_year", "payment_method",
            "payment_status", "amount", "created_at", "billing_address",
        ]


class CheckoutRequestSerializer(serializers.Serializer):
    """Accepts the full checkout form data from the UI."""
    # who is paying
    client_id = serializers.IntegerField()
    test_kit_id = serializers.IntegerField()

    # card info
    cardholder_name = serializers.CharField(max_length=200)
    card_number = serializers.CharField(max_length=19, help_text="Full card number (will NOT be stored)")
    expiry_date = serializers.CharField(max_length=7, help_text="MM/YY format")
    cvv = serializers.CharField(max_length=4, help_text="CVV (will NOT be stored)")

    # billing address
    street_address = serializers.CharField(max_length=300)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    zip_code = serializers.CharField(max_length=20)


class PurchaseDetailSerializer(serializers.ModelSerializer):
    """Returns full purchase detail with nested payment, billing, and order."""
    payment = PaymentInfoSerializer(read_only=True)
    test_kit = TestKitSerializer(read_only=True)
    order = OrderDetailSerializer(read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id", "client", "test_kit", "payment", "order",
            "status", "created_at", "updated_at",
        ]


# ── Biomarkers & Dashboard ──────────────────────────────────────────────


class BiomarkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biomarker
        fields = [
            "id", "name", "description", "category",
            "range_min", "range_max", "optimal_min", "optimal_max", "unit",
        ]


class BiomarkerResultSerializer(serializers.ModelSerializer):
    biomarker_name = serializers.CharField(source="biomarker.name", read_only=True)
    unit = serializers.CharField(source="biomarker.unit", read_only=True)
    category = serializers.CharField(source="biomarker.category", read_only=True)
    normal_range = serializers.SerializerMethodField()

    class Meta:
        model = BiomarkerResult
        fields = [
            "id", "biomarker", "biomarker_name", "category",
            "value", "unit", "status", "normal_range",
        ]

    def get_normal_range(self, obj):
        bm = obj.biomarker
        return f"Normal: {bm.range_min}-{bm.range_max}"


class BiomarkerTestSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for biomarker tests."""
    result_count = serializers.IntegerField(source="results.count", read_only=True)

    class Meta:
        model = BiomarkerTest
        fields = ["id", "client", "recorded_at", "result_count", "created_at"]


class BiomarkerTestDetailSerializer(serializers.ModelSerializer):
    """Detail serializer with nested results."""
    results = BiomarkerResultSerializer(many=True, read_only=True)

    class Meta:
        model = BiomarkerTest
        fields = ["id", "client", "recorded_at", "results", "created_at"]


class ClientPaymentHistorySerializer(serializers.ModelSerializer):
    """Payment info with billing address for query endpoints."""
    billing_address = BillingAddressSerializer(read_only=True)

    class Meta:
        model = PaymentInfo
        fields = [
            "id", "cardholder_name", "card_last_four", "card_brand",
            "expiry_month", "expiry_year", "payment_method",
            "payment_status", "amount", "billing_address", "created_at",
        ]


class ProviderPatientSerializer(serializers.ModelSerializer):
    """Compact patient profile for the provider dashboard patient list."""
    full_name = serializers.SerializerMethodField()
    latest_test_date = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "height",
            "weight",
            "ethnicity",
            "health_conditions",
            "dietary_preferences",
            "dietary_recall",
            "dietary_typicality",
            "dietary_preference_mode",
            "preferred_cuisines",
            "avoided_cuisines",
            "weekly_exercise_routine",
            "exercise_days_per_week",
            "exercise_types",
            "provider_notes",
            "fitness_goal",
            "created_at",
            "latest_test_date",
            "total_orders",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    def get_latest_test_date(self, obj):
        test = obj.biomarker_tests.order_by("-recorded_at").first()
        return test.recorded_at if test else None

    def get_total_orders(self, obj):
        return obj.orders.count()


class PricingTierSerializer(serializers.ModelSerializer):
    """Serializer for volume discount pricing tiers."""
    
    class Meta:
        model = PricingTier
        fields = [
            "id",
            "test_kit",
            "min_quantity",
            "max_quantity",
            "discount_percent",
            "created_at",
        ]
