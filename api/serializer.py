import uuid

from rest_framework import serializers

from core.models import *

from django.contrib.auth.models import User


class ClientSerializer(serializers.ModelSerializer):
    # Write-only: accept a provider's referral code when a patient registers.
    referred_by_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    dietary_recall = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    exercise_recall = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    def _store_recall_logs(self, instance, dietary_recall=None, exercise_recall=None):
        if dietary_recall is not None and str(dietary_recall).strip():
            DietLog.objects.create(client=instance, recall=str(dietary_recall).strip())
        if exercise_recall is not None and str(exercise_recall).strip():
            ExerciseLog.objects.create(client=instance, recall=str(exercise_recall).strip())

    def _clear_legacy_recall_fields(self, instance):
        updated_fields = []
        if hasattr(instance, "dietary_recall"):
            instance.dietary_recall = ""
            updated_fields.append("dietary_recall")
        if hasattr(instance, "exercise_recall"):
            instance.exercise_recall = ""
            updated_fields.append("exercise_recall")
        if updated_fields:
            instance.save(update_fields=updated_fields)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        latest_diet_log = instance.diet_logs.first()
        latest_exercise_log = instance.exercise_logs.first()
        data["dietary_recall"] = latest_diet_log.recall if latest_diet_log else ""
        data["exercise_recall"] = latest_exercise_log.recall if latest_exercise_log else ""
        data["dietary_recall_created_at"] = latest_diet_log.recorded_at if latest_diet_log else None
        data["exercise_recall_created_at"] = latest_exercise_log.recorded_at if latest_exercise_log else None
        return data

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
            "exercise_recall",
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
        dietary_recall = validated_data.pop("dietary_recall", None)
        exercise_recall = validated_data.pop("exercise_recall", None)
        instance = super().create(validated_data)
        self._clear_legacy_recall_fields(instance)
        self._store_recall_logs(instance, dietary_recall=dietary_recall, exercise_recall=exercise_recall)
        if referred_by_code:
            try:
                provider = Client.objects.get(referral_code=referred_by_code.upper())
                instance.referred_by = provider
                instance.save()
            except Client.DoesNotExist:
                pass  # Invalid code — silently ignore
        return instance

    def update(self, instance, validated_data):
        dietary_recall = validated_data.pop("dietary_recall", None)
        exercise_recall = validated_data.pop("exercise_recall", None)
        instance = super().update(instance, validated_data)
        self._clear_legacy_recall_fields(instance)
        self._store_recall_logs(instance, dietary_recall=dietary_recall, exercise_recall=exercise_recall)
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


class KitCollectionSerializer(serializers.ModelSerializer):
    dietary_recall = serializers.CharField(source="diet_log.recall", read_only=True, allow_null=True)
    exercise_recall = serializers.CharField(source="exercise_log.recall", read_only=True, allow_null=True)

    class Meta:
        model = KitCollection
        fields = [
            "id", "user", "order", "kit_barcode", "status",
            "diet_log", "exercise_log", "shipping_event",
            "dietary_recall", "exercise_recall",
            "created_at", "updated_at",
        ]


class KitResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitResult
        fields = ["id", "kit_barcode", "result_info", "created_at", "updated_at"]


class OrderSerializer(serializers.ModelSerializer):
    """Used for list views — lightweight."""
    test_kit_name = serializers.CharField(source="test_kit.name", read_only=True)
    biomarker_count = serializers.IntegerField(source="test_kit.biomarker_count", read_only=True)
    barcode_number = serializers.SerializerMethodField()
    tracking_number = serializers.CharField(source="forward_tracking_number", read_only=True)
    kit_barcode = serializers.SerializerMethodField()
    collection_status = serializers.SerializerMethodField()
    diet_log_id = serializers.SerializerMethodField()
    exercise_log_id = serializers.SerializerMethodField()
    shipping_event_id = serializers.SerializerMethodField()
    result_info = serializers.SerializerMethodField()

    def get_barcode_number(self, obj):
        assignment = getattr(obj, "barcode_assignment", None)
        return assignment.barcode_number if assignment else None

    def _collection(self, obj):
        return getattr(obj, "kit_collection", None)

    def get_kit_barcode(self, obj):
        collection = self._collection(obj)
        if collection and collection.kit_barcode:
            return collection.kit_barcode
        assignment = getattr(obj, "barcode_assignment", None)
        return assignment.barcode_number if assignment else None

    def get_collection_status(self, obj):
        collection = self._collection(obj)
        return collection.status if collection else None

    def get_diet_log_id(self, obj):
        collection = self._collection(obj)
        return collection.diet_log_id if collection else None

    def get_exercise_log_id(self, obj):
        collection = self._collection(obj)
        return collection.exercise_log_id if collection else None

    def get_shipping_event_id(self, obj):
        collection = self._collection(obj)
        return collection.shipping_event_id if collection else None

    def get_result_info(self, obj):
        collection = self._collection(obj)
        if not collection:
            return None
        result = KitResult.objects.filter(kit_barcode=collection.kit_barcode).first()
        return result.result_info if result else None

    class Meta:
        model = Order
        fields = [
            "id", "client", "test_kit", "test_kit_name", "biomarker_count", "barcode_number",
            "kit_barcode", "collection_status", "diet_log_id", "exercise_log_id", "shipping_event_id", "result_info",
            "order_number", "order_date", "status", "forward_tracking_number", "return_tracking_number", "tracking_number",
            "created_at", "updated_at",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    """Used for detail views — includes nested kit and delivery events."""
    test_kit = TestKitSerializer(read_only=True)
    delivery_events = DeliveryEventSerializer(many=True, read_only=True)
    barcode_number = serializers.SerializerMethodField()
    tracking_number = serializers.CharField(source="forward_tracking_number", read_only=True)
    kit_barcode = serializers.SerializerMethodField()
    collection_status = serializers.SerializerMethodField()
    diet_log_id = serializers.SerializerMethodField()
    exercise_log_id = serializers.SerializerMethodField()
    shipping_event_id = serializers.SerializerMethodField()
    result_info = serializers.SerializerMethodField()

    def get_barcode_number(self, obj):
        assignment = getattr(obj, "barcode_assignment", None)
        return assignment.barcode_number if assignment else None

    def _collection(self, obj):
        return getattr(obj, "kit_collection", None)

    def get_kit_barcode(self, obj):
        collection = self._collection(obj)
        if collection and collection.kit_barcode:
            return collection.kit_barcode
        assignment = getattr(obj, "barcode_assignment", None)
        return assignment.barcode_number if assignment else None

    def get_collection_status(self, obj):
        collection = self._collection(obj)
        return collection.status if collection else None

    def get_diet_log_id(self, obj):
        collection = self._collection(obj)
        return collection.diet_log_id if collection else None

    def get_exercise_log_id(self, obj):
        collection = self._collection(obj)
        return collection.exercise_log_id if collection else None

    def get_shipping_event_id(self, obj):
        collection = self._collection(obj)
        return collection.shipping_event_id if collection else None

    def get_result_info(self, obj):
        collection = self._collection(obj)
        if not collection:
            return None
        result = KitResult.objects.filter(kit_barcode=collection.kit_barcode).first()
        return result.result_info if result else None

    class Meta:
        model = Order
        fields = [
            "id", "client", "test_kit", "barcode_number", "kit_barcode", "collection_status",
            "diet_log_id", "exercise_log_id", "shipping_event_id", "result_info", "order_number", "order_date",
            "status", "forward_tracking_number", "return_tracking_number", "tracking_number", "delivery_events",
            "created_at", "updated_at",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Used for creating orders."""

    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=False)
    client_id = serializers.IntegerField(write_only=True, required=False)
    test_kit = serializers.PrimaryKeyRelatedField(queryset=TestKit.objects.all(), required=False)
    test_kit_id = serializers.IntegerField(write_only=True, required=False)
    test_kit_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    barcode_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    kit_codes = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    tracking_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = [
            "client", "client_id", "test_kit", "test_kit_id",
            "test_kit_name", "barcode_number", "kit_codes", "order_number", "tracking_number",
            "forward_tracking_number", "return_tracking_number",
        ]
        extra_kwargs = {
            "order_number": {"required": False, "allow_blank": True},
            "forward_tracking_number": {"required": False, "allow_blank": True},
            "return_tracking_number": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        client = attrs.get("client")
        test_kit = attrs.get("test_kit")
        client_id = attrs.pop("client_id", None)
        test_kit_id = attrs.pop("test_kit_id", None)
        kit_codes = attrs.get("kit_codes") or []

        if client is None and client_id is not None:
            client = Client.objects.filter(pk=client_id).first()
            if not client:
                raise serializers.ValidationError({"client_id": "Client not found."})
            attrs["client"] = client

        if test_kit is None and test_kit_id is not None:
            test_kit = TestKit.objects.filter(pk=test_kit_id).first()
            if not test_kit:
                raise serializers.ValidationError({"test_kit_id": "Test kit not found."})
            attrs["test_kit"] = test_kit

        barcode_number = str(attrs.get("barcode_number", "")).strip()
        if not barcode_number and kit_codes:
            barcode_number = str(kit_codes[0]).strip()
            attrs["barcode_number"] = barcode_number

        if not attrs.get("forward_tracking_number"):
            legacy_tracking_number = str(attrs.get("tracking_number", "")).strip()
            if legacy_tracking_number:
                attrs["forward_tracking_number"] = legacy_tracking_number

        if not attrs.get("test_kit"):
            barcode_assignment = None
            if barcode_number:
                barcode_assignment = KitBarcodeAssignment.objects.select_related("test_kit").filter(
                    barcode_number=barcode_number
                ).first()

            if barcode_assignment:
                attrs["test_kit"] = barcode_assignment.test_kit
            else:
                test_kit_name = str(attrs.pop("test_kit_name", "") or "").strip()
                if test_kit_name:
                    test_kit = TestKit.objects.filter(name__iexact=test_kit_name).first()
                    if test_kit:
                        attrs["test_kit"] = test_kit

        if not attrs.get("client"):
            raise serializers.ValidationError({"client": "Client is required."})
        if not attrs.get("test_kit"):
            raise serializers.ValidationError({"test_kit": "Test kit is required."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("client_id", None)
        validated_data.pop("test_kit_id", None)
        kit_codes = validated_data.pop("kit_codes", [])
        barcode_number = (validated_data.pop("barcode_number", "") or "").strip()
        if not barcode_number and kit_codes:
            barcode_number = str(kit_codes[0]).strip()

        forward_tracking_number = validated_data.pop("forward_tracking_number", "") or validated_data.pop("tracking_number", "")
        return_tracking_number = validated_data.pop("return_tracking_number", "")

        order = Order.objects.create(
            client=validated_data["client"],
            test_kit=validated_data["test_kit"],
            order_number=validated_data.get("order_number") or uuid.uuid4().hex[:14],
            forward_tracking_number=forward_tracking_number,
            return_tracking_number=return_tracking_number,
        )

        barcode_value = barcode_number or order.order_number
        KitBarcodeAssignment.objects.update_or_create(
            order=order,
            defaults={
                "client": validated_data["client"],
                "order_number": order.order_number,
                "test_kit": validated_data["test_kit"],
                "barcode_number": barcode_value,
            },
        )
        return order


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
    dietary_recall = serializers.SerializerMethodField()
    exercise_recall = serializers.SerializerMethodField()
    dietary_recall_created_at = serializers.SerializerMethodField()
    exercise_recall_created_at = serializers.SerializerMethodField()

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
            "exercise_recall",
            "dietary_recall_created_at",
            "exercise_recall_created_at",
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

    def get_dietary_recall(self, obj):
        latest_diet_log = obj.diet_logs.first()
        return latest_diet_log.recall if latest_diet_log else ""

    def get_exercise_recall(self, obj):
        latest_exercise_log = obj.exercise_logs.first()
        return latest_exercise_log.recall if latest_exercise_log else ""

    def get_dietary_recall_created_at(self, obj):
        latest_diet_log = obj.diet_logs.first()
        return latest_diet_log.recorded_at if latest_diet_log else None

    def get_exercise_recall_created_at(self, obj):
        latest_exercise_log = obj.exercise_logs.first()
        return latest_exercise_log.recorded_at if latest_exercise_log else None


class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = ["id", "client", "label", "street_address", "city", "state", "zip_code", "country", "is_default", "created_at"]


