import stripe
import os
import csv
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers

from .serializer import (
    ClientSerializer, MealPlanSerializer,
    TestKitSerializer, OrderSerializer, OrderDetailSerializer,
    OrderCreateSerializer, DeliveryEventSerializer,
    CheckoutRequestSerializer, PurchaseDetailSerializer, PaymentInfoSerializer,
    BiomarkerSerializer, BiomarkerResultSerializer,
    BiomarkerTestSerializer, BiomarkerTestDetailSerializer,
    ClientPaymentHistorySerializer, ProviderPatientSerializer,
    PricingTierSerializer,
)
from core.models import (
    MealPlan, Client, TestKit, Order, DeliveryEvent,
    PaymentInfo, BillingAddress, Purchase,
    Biomarker, BiomarkerTest, BiomarkerResult,
    Membership, Recommendation, PricingTier,
)
from collections import defaultdict
from datetime import date


# Create your views here.
def index(request):
    return HttpResponse("Welcome to the API endpoint!")


@extend_schema(
    summary="Verify if a kit code exists",
    description="Checks if the provided kit code (order number) exists in the system.",
    parameters=[
        OpenApiParameter(
            name="code",
            description="Kit code or order number to verify",
            required=True,
            location=OpenApiParameter.QUERY,
            type=str,
        ),
    ],
    responses={
        200: inline_serializer(
            "VerifyKitCodeResponse",
            fields={"valid": serializers.BooleanField(), "message": serializers.CharField()},
        ),
        400: inline_serializer(
            "ErrorResponse",
            fields={"message": serializers.CharField()},
        ),
    },
    tags=["Kits"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def verify_kit_code(request):
    """Verify if a kit code (order number) exists in the database."""
    code = request.query_params.get("code", "").strip()
    
    if not code:
        return Response(
            {"valid": False, "message": "Kit code is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if the order number exists
    order_exists = Order.objects.filter(order_number=code).exists()
    
    if order_exists:
        return Response(
            {"valid": True, "message": "Kit code verified successfully"},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"valid": False, "message": "Kit code not found in the system"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(
    summary="Create or update a client",
    description="Creates a new client or updates an existing one if the email already exists.",
    request=ClientSerializer,
    responses={201: ClientSerializer},
    tags=["Clients"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_client(request):
    # extract profile data if present
    client_data = request.data
    instance = Client.get_client_by_email(client_data.get("email"))
    # if client exists, continue to the profile creation
    if instance:
        serializer = ClientSerializer(instance, data=client_data, partial=True)
    else:
        serializer = ClientSerializer(data=client_data)
    if not serializer.is_valid():
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response(serializer.data, status.HTTP_201_CREATED)


@extend_schema(
    summary="Get client by ID",
    description="Retrieve a single client's details by their primary key.",
    responses={200: ClientSerializer, 404: None},
    tags=["Clients"],
)
@api_view(["GET", "PATCH"])
def client_handler(request, pk):
    try:
        client = Client.objects.get(id=pk)
    except Client.DoesNotExist:
        return Response({"error": "Client not found"}, status.HTTP_404_NOT_FOUND)

    if request.method == "PATCH":
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status.HTTP_200_OK)

    serializer = ClientSerializer(client)
    return Response(serializer.data)


def register_user(username, password):
    if not username or not password:
        return None, "Username and password are required"
    if User.objects.filter(username=username).exists():
        return None, "Username already exists"
    user = User.objects.create_user(username=username, password=password)
    return user, None


def create_client_helper(data):
    client_serializer = ClientSerializer(data=data)
    if not client_serializer.is_valid():
        return None, client_serializer.errors
    client_serializer.save()
    return client_serializer, None


@extend_schema(
    summary="Register a new user",
    description=(
        "Creates a new auth user and associated client profile in a single request. "
        "For PROVIDER accounts, only first_name and last_name are required. "
        "For INDIVIDUAL accounts, all health/dietary fields can be provided. "
        "Pass referred_by_code to associate a new patient with a provider."
    ),
    request=inline_serializer(
        name="RegisterRequest",
        fields={
            "username": serializers.CharField(),
            "password": serializers.CharField(),
            "email": serializers.EmailField(),
            "first_name": serializers.CharField(required=False),
            "last_name": serializers.CharField(required=False),
            "type": serializers.ChoiceField(choices=["PROVIDER", "INDIVIDUAL"], required=False),
            "date_of_birth": serializers.DateField(required=False),
            "gender": serializers.CharField(required=False),
            "height": serializers.FloatField(required=False),
            "weight": serializers.FloatField(required=False),
            "dietary_recall": serializers.CharField(required=False),
            "exercise_recall": serializers.CharField(required=False),
            "dietary_typicality": serializers.IntegerField(required=False),
            "dietary_preference_mode": serializers.CharField(required=False),
            "preferred_cuisines": serializers.CharField(required=False),
            "avoided_cuisines": serializers.CharField(required=False),
            "weekly_exercise_routine": serializers.CharField(required=False),
            "exercise_days_per_week": serializers.IntegerField(required=False),
            "exercise_types": serializers.CharField(required=False),
            "provider_notes": serializers.CharField(required=False),
            "referred_by_code": serializers.CharField(required=False),
        },
    ),
    responses={201: ClientSerializer},
    tags=["Auth"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """register user

    For PROVIDER accounts, only first_name, last_name, email, username, and password
    are required. A referral_code is automatically generated for the provider.

    For INDIVIDUAL accounts, all health fields can optionally be provided.
    Pass referred_by_code to link this patient to a provider.

    example (provider):
    {
        "username": "dr.smith@clinic.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Smith",
        "email": "dr.smith@clinic.com",
        "type": "PROVIDER"
    }

    example (individual with referral):
    {
        "username": "patient@email.com",
        "password": "password123",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "patient@email.com",
        "type": "INDIVIDUAL",
        "referred_by_code": "ABC1234567"
    }
    """
    data = request.data.copy()
    username = data.pop("username", None)
    password = data.pop("password", None)

    user, error = register_user(username, password)
    if error:
        return Response(error, status.HTTP_400_BAD_REQUEST)
    data["user"] = user.id

    client_serializer, error = create_client_helper(data)
    if error:
        user.delete()
        return Response(error, status.HTTP_400_BAD_REQUEST)
    return Response(client_serializer.data, status.HTTP_201_CREATED)


@extend_schema(
    summary="Get provider referral info",
    description=(
        "Returns the provider's unique referral code and referred patient count. "
        "The client app is responsible for constructing the full shareable URL "
        "as: <APP_BASE_URL>/register?ref=<referral_code>"
    ),
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Provider's client ID"),
    ],
    responses={200: inline_serializer(
        name="ReferralLinkResponse",
        fields={
            "referral_code": serializers.CharField(),
            "patient_count": serializers.IntegerField(),
        },
    )},
    tags=["Provider"],
)
@api_view(["GET"])
def get_referral_link(request):
    """Return a provider's unique referral code and referred patient count.

    The frontend is responsible for constructing the shareable URL so it always
    reflects the actual app URL (web, mobile, staging, production), regardless
    of where the Django server is hosted.

    Response:
        { "referral_code": "ABC1234567", "patient_count": 3 }
    """
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    try:
        client = Client.objects.get(pk=client_id, type="PROVIDER")
    except Client.DoesNotExist:
        return Response({"error": "Provider not found"}, status.HTTP_404_NOT_FOUND)

    if not client.referral_code:
        client.save()  # Triggers auto-generation via model.save()
        client.refresh_from_db()

    patient_count = client.referred_patients.count()

    return Response({
        "referral_code": client.referral_code,
        "patient_count": patient_count,
    }, status.HTTP_200_OK)


@extend_schema(
    summary="Validate referral code",
    description="Checks whether a referral code belongs to an existing provider account.",
    parameters=[
        OpenApiParameter(name="code", type=str, required=True, description="Provider referral code"),
    ],
    responses={200: inline_serializer(
        name="ValidateReferralCodeResponse",
        fields={
            "isValid": serializers.BooleanField(),
        },
    )},
    tags=["Provider"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def validate_referral_code(request):
    code = (request.GET.get("code") or "").strip().upper()
    if not code:
        return Response({"isValid": False}, status.HTTP_200_OK)

    is_valid = Client.objects.filter(referral_code=code, type="PROVIDER").exists()
    return Response({"isValid": is_valid}, status.HTTP_200_OK)


@extend_schema(
    summary="List provider's patients",
    description=(
        "Returns all patients who registered using the provider's referral link, "
        "ordered by join date (newest first). Includes key health profile data."
    ),
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Provider's client ID"),
    ],
    responses={200: ProviderPatientSerializer(many=True)},
    tags=["Provider"],
)
@api_view(["GET"])
def get_provider_patients(request):
    """Return all patients referred by a provider, with their health info."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    try:
        provider = Client.objects.get(pk=client_id, type="PROVIDER")
    except Client.DoesNotExist:
        return Response({"error": "Provider not found"}, status.HTTP_404_NOT_FOUND)

    patients = (
        provider.referred_patients
        .prefetch_related("biomarker_tests", "orders")
        .order_by("-created_at")
    )
    return Response(ProviderPatientSerializer(patients, many=True).data, status.HTTP_200_OK)


@extend_schema(
    summary="Get pricing tiers for a test kit",
    description="Returns all volume discount pricing tiers for a specific test kit.",
    parameters=[
        OpenApiParameter(name="kit_id", type=int, required=True, description="Test kit ID"),
    ],
    responses={200: PricingTierSerializer(many=True)},
    tags=["Pricing"],
)
@api_view(["GET"])
def get_kit_pricing_tiers(request, kit_id=None):
    """Return pricing tiers for a test kit."""
    kit_id = request.GET.get("kit_id") or kit_id
    
    if not kit_id:
        return Response({"error": "kit_id is required"}, status.HTTP_400_BAD_REQUEST)
    
    try:
        kit = TestKit.objects.get(pk=kit_id)
    except TestKit.DoesNotExist:
        return Response({"error": "Test kit not found"}, status.HTTP_404_NOT_FOUND)
    
    tiers = kit.pricing_tiers.all().order_by("min_quantity")
    return Response(PricingTierSerializer(tiers, many=True).data, status.HTTP_200_OK)


@extend_schema(
    summary="Get all pricing tiers",
    description="Returns all volume discount pricing tiers across all test kits.",
    responses={200: PricingTierSerializer(many=True)},
    tags=["Pricing"],
)
@api_view(["GET"])
def get_all_pricing_tiers(request):
    """Return all pricing tiers."""
    tiers = PricingTier.objects.all().select_related("test_kit").order_by("test_kit", "min_quantity")
    return Response(PricingTierSerializer(tiers, many=True).data, status.HTTP_200_OK)


@extend_schema(
    summary="Login",
    description="Authenticate with username and password. Returns client data on success.",
    request=inline_serializer(
        name="LoginRequest",
        fields={
            "username": serializers.CharField(),
            "password": serializers.CharField(),
        },
    ),
    responses={200: ClientSerializer, 401: None},
    tags=["Auth"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_handler(request):
    print(request)
    data = request.data
    user = authenticate(**data)
    if user is None:
        return Response({"error": "invalid credential"}, status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    try:
        user = User.objects.get(username=user.username)
        client = Client.objects.get(user=user)
        token, _ = Token.objects.get_or_create(user=user)
        client_serializer = ClientSerializer(client)
        request.session["client_id"] = client.id
        print(f"-----debug session client_id set to {client.id} -----")
        print(f"-----debug session data: {request.session.items()} -----")
        return Response({
            **client_serializer.data,
            "token": token.key,
            "token_type": "Token",
        }, status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response({"error": e}, status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Logout",
    description="Log out the current session user and clear server session.",
    responses={200: None},
    tags=["Auth"],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def logout_handler(request):
    try:
        logout(request)
        request.session.flush()
    except Exception:
        pass
    return Response({"message": "logged out"}, status.HTTP_200_OK)


@extend_schema(
    summary="Verify authentication token",
    description="Verify if the provided authentication token is valid.",
    responses={200: inline_serializer(
        name="VerifyTokenResponse",
        fields={"valid": serializers.BooleanField()},
    )},
    tags=["Auth"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_token_handler(request):
    """
    Verify if the user's authentication token is still valid.
    Returns 200 OK if token is valid, 401 if invalid.
    """
    return Response({"valid": True}, status.HTTP_200_OK)


@extend_schema(
    summary="Check email availability",
    description="Check whether a username (email) is already registered.",
    parameters=[
        OpenApiParameter(name="email", type=str, required=True, description="Email address to check"),
    ],
    responses={200: inline_serializer(
        name="EmailCheckResponse",
        fields={"exists": serializers.BooleanField()},
    )},
    tags=["Auth"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def check_email(request):
    """Check if a username (email) already exists.

    Query param: ?email=someone@example.com
    Returns: { "exists": true/false }
    """
    email = request.GET.get("email")
    if not email:
        return Response(
            {"error": "email query param required"},
            status.HTTP_400_BAD_REQUEST,
        )
    exists = User.objects.filter(username=email).exists()
    return Response({"exists": exists}, status.HTTP_200_OK)


@extend_schema(
    summary="Generate a meal plan",
    description="Generate a new meal plan for the given client.",
    responses={200: None},
    tags=["Meal Plans"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_mealPlan(request, client_id):
    client = Client.objects.get(id=client_id)
    return Response({"message": f"will send client info: {client}"}, status.HTTP_200_OK)


@extend_schema(
    summary="Get meal plans",
    description="Retrieve meal plans for a client within an optional date range. Defaults to the current week.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
        OpenApiParameter(name="start_date", type=str, required=False, description="Start date (ISO 8601)"),
        OpenApiParameter(name="end_date", type=str, required=False, description="End date (ISO 8601)"),
    ],
    responses={200: MealPlanSerializer(many=True)},
    tags=["Meal Plans"],
)
@api_view(["GET"])
def meal_plan(request):
    """
    Handles the meal plan requests.
    Accepts client_id, start_date, and end_date as query parameters.
    Returns the meal plan for the specified client and date range.
    """
    client_id = request.GET.get("client_id")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    # Optionally parse start_date and end_date if provided
    start_dt = parse_datetime(start_date) if start_date else None
    end_dt = parse_datetime(end_date) if end_date else None
    meal_plans = MealPlan.get_meal_plans_by_client_and_date(client_id, start_dt, end_dt)
    meal_plan = MealPlanSerializer(meal_plans, many=True)
    return Response(meal_plan.data)


# ── Shipping / Kit Tracking ─────────────────────────────────────────────


@extend_schema(
    summary="List test kits",
    description="Return catalogue of available test kits.",
    responses={200: TestKitSerializer(many=True)},
    tags=["Test Kits"],
)
@api_view(["GET"])
def list_kits(request):
    """Return all available test kits."""
    kits = TestKit.objects.all()
    return Response(TestKitSerializer(kits, many=True).data)


@extend_schema(
    summary="List orders for a client",
    description="Returns all orders for the given client_id, newest first.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: OrderSerializer(many=True)},
    tags=["Orders"],
)
@api_view(["GET"])
def list_orders(request):
    """List orders filtered by client_id query param."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    orders = Order.objects.filter(client_id=client_id).select_related("test_kit")
    return Response(OrderSerializer(orders, many=True).data)


def _csv_safe(value):
    """Prevent spreadsheet formula injection in exported CSV cells."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@extend_schema(
    summary="Export orders as CSV",
    description=(
        "Download the orders table as a CSV file that can be opened directly in "
        "Google Sheets or Excel. Optional `client_id` filters the exported rows."
    ),
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=False, description="Optional Client ID filter"),
    ],
    responses={200: None},
    tags=["Orders"],
)
@api_view(["GET"])
def export_orders_csv(request):
    """Export order rows as CSV for spreadsheet import."""
    client_id = request.GET.get("client_id")

    orders = Order.objects.select_related("client", "test_kit").order_by("-order_date")
    if client_id:
        orders = orders.filter(client_id=client_id)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="orders_export_{date.today().isoformat()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "id",
        "order_number",
        "order_date",
        "status",
        "tracking_number",
        "quantity",
        "client_id",
        "client_name",
        "client_email",
        "test_kit_id",
        "test_kit_name",
        "created_at",
        "updated_at",
    ])

    for order in orders:
        client_name = f"{order.client.first_name} {order.client.last_name}".strip()
        writer.writerow([
            order.id,
            _csv_safe(order.order_number),
            order.order_date.isoformat() if order.order_date else "",
            _csv_safe(order.status),
            _csv_safe(order.tracking_number),
            order.quantity,
            order.client_id,
            _csv_safe(client_name),
            _csv_safe(order.client.email),
            order.test_kit_id,
            _csv_safe(order.test_kit.name),
            order.created_at.isoformat() if order.created_at else "",
            order.updated_at.isoformat() if order.updated_at else "",
        ])

    return response


@extend_schema(
    summary="Create an order",
    description="Place a new test-kit order. Automatically creates an initial 'Order Placed' delivery event.",
    request=OrderCreateSerializer,
    responses={201: OrderDetailSerializer},
    tags=["Orders"],
)
@api_view(["POST"])
def create_order(request):
    """Create a new order and seed the first delivery event."""
    serializer = OrderCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    order = serializer.save()

    # Seed initial delivery event
    DeliveryEvent.objects.create(
        order=order,
        event_type="ORDER_PLACED",
        title="Order Placed",
        description="Your order has been received",
        is_completed=True,
    )

    return Response(OrderDetailSerializer(order).data, status.HTTP_201_CREATED)


@extend_schema(
    summary="Get order detail",
    description="Retrieve full order details including test kit info and delivery event history.",
    responses={200: OrderDetailSerializer, 404: None},
    tags=["Orders"],
)
@api_view(["GET"])
def order_detail(request, pk):
    """Get a single order with nested delivery events."""
    try:
        order = Order.objects.select_related("test_kit").prefetch_related("delivery_events").get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status.HTTP_404_NOT_FOUND)
    return Response(OrderDetailSerializer(order).data)


@extend_schema(
    summary="Update order status",
    description=(
        "Update the order status and optionally append a delivery event. "
        "Send `status` (required) plus optional `title`/`description` for the event."
    ),
    request=inline_serializer(
        name="OrderStatusUpdate",
        fields={
            "status": serializers.ChoiceField(choices=[c[0] for c in Order.STATUS_CHOICES]),
            "title": serializers.CharField(required=False),
            "description": serializers.CharField(required=False),
            "tracking_number": serializers.CharField(required=False, allow_blank=True),
        },
    ),
    responses={200: OrderDetailSerializer},
    tags=["Orders"],
)
@api_view(["PATCH"])
def update_order_status(request, pk):
    """Update order status and create a delivery event."""
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({"error": "Invalid status"}, status.HTTP_400_BAD_REQUEST)

    tracking_number = request.data.get("tracking_number", "").strip()

    order.status = new_status
    if tracking_number:
        order.tracking_number = tracking_number
    order.save()

    # Create delivery event
    title = request.data.get("title", dict(Order.STATUS_CHOICES).get(new_status, new_status))
    description = request.data.get("description", "")
    is_completed = new_status in ("DELIVERED",)

    DeliveryEvent.objects.create(
        order=order,
        event_type=new_status if new_status in dict(DeliveryEvent.EVENT_TYPES) else "IN_TRANSIT",
        title=title,
        description=description,
        is_completed=is_completed,
    )

    # Mark all previous events as completed
    order.delivery_events.exclude(event_type=new_status).update(is_completed=True)

    order.refresh_from_db()
    return Response(
        OrderDetailSerializer(
            Order.objects.select_related("test_kit").prefetch_related("delivery_events").get(pk=pk)
        ).data
    )


@extend_schema(
    summary="Track order by tracking number",
    description="Look up an order by its tracking number.",
    parameters=[
        OpenApiParameter(name="tracking_number", type=str, required=True, description="Tracking number"),
    ],
    responses={200: OrderDetailSerializer, 404: None},
    tags=["Orders"],
)
@api_view(["GET"])
def track_order(request):
    """Look up an order by tracking number."""
    tracking_number = request.GET.get("tracking_number")
    if not tracking_number:
        return Response({"error": "tracking_number is required"}, status.HTTP_400_BAD_REQUEST)
    try:
        order = (
            Order.objects
            .select_related("test_kit")
            .prefetch_related("delivery_events")
            .get(tracking_number=tracking_number)
        )
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status.HTTP_404_NOT_FOUND)
    return Response(OrderDetailSerializer(order).data)


# ── Checkout / Purchases ────────────────────────────────────────────────

import uuid


def _generate_order_number():
    """Generate a unique order number like '182u0572572283'."""
    return uuid.uuid4().hex[:14]


def _generate_tracking_number():
    """Generate a tracking number like 'TK19283JEJT'."""
    return "TK" + uuid.uuid4().hex[:9].upper()


def _detect_card_brand(number: str) -> str:
    """Simple card brand detection from first digits."""
    n = number.replace(" ", "").replace("-", "")
    if n.startswith("4"):
        return "Visa"
    elif n[:2] in ("51", "52", "53", "54", "55"):
        return "Mastercard"
    elif n[:2] in ("34", "37"):
        return "Amex"
    elif n[:4] == "6011" or n[:2] == "65":
        return "Discover"
    return "Card"


@extend_schema(
    summary="Create a PaymentIntent",
    description="Create a Stripe PaymentIntent for a specific test kit. Returns the client secret.",
    request=inline_serializer(
        name="CreatePaymentIntentRequest",
        fields={
            "test_kit_id": serializers.IntegerField(),
            "client_id": serializers.IntegerField(),
        },
    ),
    responses={200: inline_serializer(
        name="PaymentIntentResponse",
        fields={"clientSecret": serializers.CharField()},
    )},
    tags=["Checkout"],
)
@api_view(["POST"])
def create_payment_intent(request):
    data = request.data
    test_kit_id = data.get("test_kit_id")
    client_id = data.get("client_id")
    quantity = int(data.get("quantity", 1))

    if not test_kit_id:
        return Response({"error": "test_kit_id is required"}, status.HTTP_400_BAD_REQUEST)

    try:
        kit = TestKit.objects.get(pk=test_kit_id)
    except TestKit.DoesNotExist:
        return Response({"error": "Test kit not found"}, status.HTTP_404_NOT_FOUND)

    # Calculate amount based on quantity and pricing tiers
    total_price = kit.get_price_for_quantity(quantity)
    amount = int(total_price * 100)

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="usd",
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                "test_kit_id": kit.id,
                "client_id": client_id,
                "quantity": str(quantity),
            }
        )
        return Response({"clientSecret": intent.client_secret}, status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Confirm Payment and Create Order",
    description="Verify a successful Stripe payment and create the corresponding order.",
    request=inline_serializer(
        name="ConfirmPaymentRequest",
        fields={
            "payment_intent_id": serializers.CharField(),
            "street_address": serializers.CharField(),
            "city": serializers.CharField(),
            "state": serializers.CharField(),
            "zip_code": serializers.CharField(),
        },
    ),
    responses={201: PurchaseDetailSerializer, 400: None},
    tags=["Checkout"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_payment(request):
    data = request.data
    payment_intent_id = data.get("payment_intent_id")

    if not payment_intent_id:
        return Response({"error": "payment_intent_id is required"}, status.HTTP_400_BAD_REQUEST)

    try:
        client_id = request.session.get("client_id")
        test_kit_id = data.get("test_kit_id")
        quantity = int(data.get("quantity", 1))

        card_brand = "Card"
        card_last_four = "0000"

        if payment_intent_id != "free_order":
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != "succeeded":
                return Response({"error": f"Payment status is {intent.status}"}, status.HTTP_400_BAD_REQUEST)

            if PaymentInfo.objects.filter(stripe_payment_intent_id=payment_intent_id).exists():
                return Response({"message": "Payment already processed"}, status.HTTP_200_OK)

            test_kit_id = intent.metadata.get("test_kit_id") or test_kit_id
            client_id = intent.metadata.get("client_id") or client_id
            quantity = int(intent.metadata.get("quantity", 1))

            if not test_kit_id or not client_id:
                # fallback: try to use authenticated user's client if metadata missing
                if request.user and request.user.is_authenticated:
                    try:
                        client = Client.objects.get(user=request.user)
                        client_id = client.id
                    except Client.DoesNotExist:
                        return Response({"error": "Missing metadata in payment intent and no linked client for authenticated user"}, status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"error": "Missing metadata in payment intent"}, status.HTTP_400_BAD_REQUEST)

            if intent.charges and intent.charges.data:
                charge = intent.charges.data[0]
                if charge.payment_method_details and charge.payment_method_details.card:
                    card = charge.payment_method_details.card
                    card_brand = card.brand
                    card_last_four = card.last4

        if not client_id and request.user and request.user.is_authenticated:
            try:
                client = Client.objects.get(user=request.user)
                client_id = client.id
            except Client.DoesNotExist:
                return Response({"error": "No linked client for authenticated user"}, status.HTTP_400_BAD_REQUEST)

        if not client_id:
            return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
        if not test_kit_id:
            return Response({"error": "test_kit_id is required"}, status.HTTP_400_BAD_REQUEST)

        client = Client.objects.get(pk=client_id)
        kit = TestKit.objects.get(pk=test_kit_id)

        # Calculate total amount based on quantity and pricing tiers
        total_amount = kit.get_price_for_quantity(quantity)

        payment = PaymentInfo.objects.create(
            client=client,
            cardholder_name=data.get("cardholder_name", ""),
            card_last_four=card_last_four,
            card_brand=card_brand,
            expiry_month=1,
            expiry_year=2026,
            payment_method="card",
            payment_status="COMPLETED",
            amount=total_amount,
            stripe_payment_intent_id=payment_intent_id,
        )

        BillingAddress.objects.create(
            payment=payment,
            street_address=data.get("street_address"),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zip_code"),
        )

        order = Order.objects.create(
            client=client,
            test_kit=kit,
            order_number=_generate_order_number(),
            quantity=quantity,
            tracking_number="",
            status="PENDING",
        )

        DeliveryEvent.objects.create(
            order=order,
            event_type="ORDER_PLACED",
            title="Order Placed",
            description="Your order has been received",
            is_completed=True,
        )

        print("-----debug-----")

        purchase = Purchase.objects.create(
            client=client,
            test_kit=kit,
            payment=payment,
            order=order,
            status="COMPLETED",
        )

        return Response(PurchaseDetailSerializer(purchase).data, status.HTTP_201_CREATED)

    except stripe.error.StripeError as e:
        return Response({"error": str(e)}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']
        
        if not PaymentInfo.objects.filter(stripe_payment_intent_id=payment_intent_id).exists():
             test_kit_id = payment_intent.metadata.get("test_kit_id")
             client_id = payment_intent.metadata.get("client_id")

             if test_kit_id and client_id:
                 try:
                     client = Client.objects.get(pk=client_id)
                     kit = TestKit.objects.get(pk=test_kit_id)
                     
                     card_brand = "Card"
                     card_last_four = "0000"
                     if payment_intent.charges and payment_intent.charges.data:
                         charge = payment_intent.charges.data[0]
                         if charge.payment_method_details and charge.payment_method_details.card:
                             card = charge.payment_method_details.card
                             card_brand = card.brand
                             card_last_four = card.last4

                     payment = PaymentInfo.objects.create(
                         client=client,
                         cardholder_name="",
                         card_last_four=card_last_four,
                         card_brand=card_brand,
                         expiry_month=1,
                         expiry_year=2026,
                         payment_method="card",
                         payment_status="COMPLETED",
                         amount=kit.price,
                         stripe_payment_intent_id=payment_intent_id,
                     )

                     BillingAddress.objects.create(
                         payment=payment,
                         street_address="Webhook Address",
                         city="Webhook City",
                         state="Webhook State",
                         zip_code="00000",
                     )

                     order = Order.objects.create(
                         client=client,
                         test_kit=kit,
                         order_number=_generate_order_number(),
                         tracking_number="",
                         status="PENDING",
                     )

                     DeliveryEvent.objects.create(
                         order=order,
                         event_type="ORDER_PLACED",
                         title="Order Placed",
                         description="Your order has been received (Webhook)",
                         is_completed=True,
                     )

                     Purchase.objects.create(
                         client=client,
                         test_kit=kit,
                         payment=payment,
                         order=order,
                         status="COMPLETED",
                     )
                 except Exception as e:
                     print(f"Error processing webhook for {payment_intent_id}: {e}")
                     return HttpResponse(status=500)

    return HttpResponse(status=200)





@extend_schema(
    summary="Checkout — purchase a test kit",
    description=(
        "Complete checkout: validates card & billing info, creates payment record, "
        "generates an order with tracking number, and returns full purchase details. "
        "Card number and CVV are **never stored**."
    ),
    request=CheckoutRequestSerializer,
    responses={201: PurchaseDetailSerializer, 400: None},
    tags=["Checkout"],
)
@api_view(["POST"])
def checkout(request):
    """Process a test-kit purchase."""
    serializer = CheckoutRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # ── Validate client & kit ───────────────────────────────────────
    try:
        client = Client.objects.get(pk=data["client_id"])
    except Client.DoesNotExist:
        return Response({"error": "Client not found"}, status.HTTP_404_NOT_FOUND)

    try:
        kit = TestKit.objects.get(pk=data["test_kit_id"])
    except TestKit.DoesNotExist:
        return Response({"error": "Test kit not found"}, status.HTTP_404_NOT_FOUND)

    # ── Parse expiry ────────────────────────────────────────────────
    try:
        month_str, year_str = data["expiry_date"].split("/")
        expiry_month = int(month_str)
        expiry_year = int("20" + year_str) if len(year_str) == 2 else int(year_str)
    except (ValueError, IndexError):
        return Response(
            {"error": "expiry_date must be in MM/YY format"},
            status.HTTP_400_BAD_REQUEST,
        )

    card_number = data["card_number"].replace(" ", "").replace("-", "")

    # ── Create PaymentInfo (only last 4 stored) ─────────────────────
    payment = PaymentInfo.objects.create(
        client=client,
        cardholder_name=data["cardholder_name"],
        card_last_four=card_number[-4:],
        card_brand=_detect_card_brand(card_number),
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        amount=kit.price,
        payment_status="COMPLETED",
    )

    # ── Create BillingAddress ───────────────────────────────────────
    BillingAddress.objects.create(
        payment=payment,
        street_address=data["street_address"],
        city=data["city"],
        state=data["state"],
        zip_code=data["zip_code"],
    )

    # ── Create Order ────────────────────────────────────────────────
    order = Order.objects.create(
        client=client,
        test_kit=kit,
        order_number=_generate_order_number(),
        tracking_number="",
        status="PENDING",
    )

    # Seed first delivery event
    DeliveryEvent.objects.create(
        order=order,
        event_type="ORDER_PLACED",
        title="Order Placed",
        description="Your order has been received",
        is_completed=True,
    )

    # ── Create Purchase ─────────────────────────────────────────────
    purchase = Purchase.objects.create(
        client=client,
        test_kit=kit,
        payment=payment,
        order=order,
        status="COMPLETED",
    )

    return Response(PurchaseDetailSerializer(purchase).data, status.HTTP_201_CREATED)


@extend_schema(
    summary="Purchase history",
    description="List all purchases for a given client, newest first.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: PurchaseDetailSerializer(many=True)},
    tags=["Checkout"],
)
@api_view(["GET"])
def purchase_history(request):
    """List all purchases for a client."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    purchases = (
        Purchase.objects
        .filter(client_id=client_id)
        .select_related("test_kit", "payment", "order")
        .prefetch_related("order__delivery_events")
        .order_by("-created_at")
    )
    return Response(PurchaseDetailSerializer(purchases, many=True).data)


@extend_schema(
    summary="Purchase detail",
    description="Get full details of a single purchase.",
    responses={200: PurchaseDetailSerializer, 404: None},
    tags=["Checkout"],
)
@api_view(["GET"])
def purchase_detail(request, pk):
    """Get a single purchase with nested payment, billing, and order info."""
    try:
        purchase = (
            Purchase.objects
            .select_related("test_kit", "payment", "order")
            .prefetch_related("order__delivery_events")
            .get(pk=pk)
        )
    except Purchase.DoesNotExist:
        return Response({"error": "Purchase not found"}, status.HTTP_404_NOT_FOUND)
    return Response(PurchaseDetailSerializer(purchase).data)


# ── Biomarkers & Dashboard Queries ──────────────────────────────────────


@extend_schema(
    summary="List all biomarkers",
    description="Return the full catalogue of biomarkers with categories and reference ranges.",
    parameters=[
        OpenApiParameter(name="category", type=str, required=False, description="Filter by category (e.g. METABOLIC, CARDIOVASCULAR)"),
    ],
    responses={200: BiomarkerSerializer(many=True)},
    tags=["Biomarkers"],
)
@api_view(["GET"])
def list_biomarkers(request):
    """List all biomarkers, optionally filtered by category."""
    category = request.GET.get("category")
    qs = Biomarker.objects.all().order_by("category", "name")
    if category:
        qs = qs.filter(category=category.upper())
    return Response(BiomarkerSerializer(qs, many=True).data)


@extend_schema(
    summary="List biomarker tests for a client",
    description="Return all test sessions for a client, newest first.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: BiomarkerTestSerializer(many=True)},
    tags=["Biomarkers"],
)
@api_view(["GET"])
def list_biomarker_tests(request):
    """List all biomarker test sessions for a client."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    tests = BiomarkerTest.objects.filter(client_id=client_id).order_by("-recorded_at")
    return Response(BiomarkerTestSerializer(tests, many=True).data)


@extend_schema(
    summary="Get biomarker test detail",
    description="Return a single biomarker test with all individual results.",
    responses={200: BiomarkerTestDetailSerializer, 404: None},
    tags=["Biomarkers"],
)
@api_view(["GET"])
def biomarker_test_detail(request, pk):
    """Get a single test session with nested results."""
    try:
        test = (
            BiomarkerTest.objects
            .prefetch_related("results__biomarker")
            .get(pk=pk)
        )
    except BiomarkerTest.DoesNotExist:
        return Response({"error": "Test not found"}, status.HTTP_404_NOT_FOUND)
    return Response(BiomarkerTestDetailSerializer(test).data)


@extend_schema(
    summary="Client dashboard",
    description=(
        "Returns a comprehensive dashboard for a client: profile summary, "
        "health score, latest biomarker results grouped by category, and recent orders."
    ),
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: None},
    tags=["Dashboard"],
)
@api_view(["GET"])
def client_dashboard(request):
    """Aggregated dashboard data matching the UI mockup."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)

    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return Response({"error": "Client not found"}, status.HTTP_404_NOT_FOUND)

    # ── Profile summary ─────────────────────────────────────────────
    age = None
    if client.date_of_birth:
        today = date.today()
        age = today.year - client.date_of_birth.year - (
            (today.month, today.day) < (client.date_of_birth.month, client.date_of_birth.day)
        )

    profile = {
        "name": f"{client.first_name} {client.last_name}".strip(),
        "age": age,
        "height": client.height,
        "weight": client.weight,
        "email": client.email,
    }

    # ── Latest biomarker test ───────────────────────────────────────
    latest_test = (
        BiomarkerTest.objects
        .filter(client=client)
        .prefetch_related("results__biomarker")
        .order_by("-recorded_at")
        .first()
    )

    categorized_results = {}
    health_score = None
    total_markers = 0
    optimal_count = 0

    if latest_test:
        results = latest_test.results.select_related("biomarker").all()
        grouped = defaultdict(list)
        for r in results:
            total_markers += 1
            if r.status in ("OPTIMAL", "NORMAL"):
                optimal_count += 1
            grouped[r.biomarker.get_category_display()].append({
                "biomarker_name": r.biomarker.name,
                "value": r.value,
                "unit": r.biomarker.unit,
                "status": r.status,
                "normal_range": f"Normal: {r.biomarker.range_min}-{r.biomarker.range_max}",
            })

        categorized_results = {
            cat: {"biomarker_count": len(items), "results": items}
            for cat, items in grouped.items()
        }

        if total_markers > 0:
            health_score = round((optimal_count / total_markers) * 100)

    # ── Recent orders ───────────────────────────────────────────────
    recent_orders = Order.objects.filter(client=client).select_related("test_kit")[:5]

    # ── Recommendations ─────────────────────────────────────────────
    recommendations = list(Recommendation.objects.filter(client=client).values_list('text', flat=True))

    return Response({
        "profile": profile,
        "health_score": health_score,
        "total_biomarkers": total_markers,
        "optimal_biomarkers": optimal_count,
        "biomarker_results": categorized_results,
        "latest_test_date": latest_test.recorded_at if latest_test else None,
        "recent_orders": OrderSerializer(recent_orders, many=True).data,
        "recommendations": recommendations,
    })


@extend_schema(
    summary="Client payment history",
    description="Return all payment records for a client with billing addresses.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: ClientPaymentHistorySerializer(many=True)},
    tags=["Payments"],
)
@api_view(["GET"])
def client_payments(request):
    """List all payments for a client."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    payments = (
        PaymentInfo.objects
        .filter(client_id=client_id)
        .select_related("billing_address")
        .order_by("-created_at")
    )
    return Response(ClientPaymentHistorySerializer(payments, many=True).data)


@extend_schema(
    summary="Client membership status",
    description="Return all memberships for a client.",
    parameters=[
        OpenApiParameter(name="client_id", type=int, required=True, description="Client ID"),
    ],
    responses={200: MealPlanSerializer(many=True)},  # Reusing for now or just generic
    tags=["Memberships"],
)
@api_view(["GET"])
def client_memberships(request):
    """List memberships for a client."""
    client_id = request.GET.get("client_id")
    if not client_id:
        return Response({"error": "client_id is required"}, status.HTTP_400_BAD_REQUEST)
    memberships = Membership.objects.filter(client_id=client_id).order_by("-start_date")
    # Using generic data for now since I didn't create a specific serializer
    data = [
        {
            "id": m.id,
            "membership_type": m.membership_type,
            "start_date": m.start_date,
            "end_date": m.end_date,
            "is_active": m.start_date <= timezone.now() <= m.end_date
        }
        for m in memberships
    ]
    return Response(data)




