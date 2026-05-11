from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
from decimal import Decimal


class Biomarker(models.Model):
    CATEGORY_CHOICES = [
        ("METABOLIC", "Metabolic Health"),
        ("CARDIOVASCULAR", "Cardiovascular Health"),
        ("INFLAMMATION", "Inflammation"),
        ("HORMONAL", "Hormonal Health"),
        ("LIVER", "Liver Health"),
        ("KIDNEY", "Kidney Health"),
        ("THYROID", "Thyroid Health"),
        ("OTHER", "Other"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="OTHER")
    range_min = models.FloatField(help_text="Normal range lower bound")
    range_max = models.FloatField(help_text="Normal range upper bound")
    optimal_min = models.FloatField(null=True, blank=True, help_text="Optimal range lower bound")
    optimal_max = models.FloatField(null=True, blank=True, help_text="Optimal range upper bound")
    unit = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.unit})"


class BiomarkerTest(models.Model):
    """A test session — groups multiple biomarker results recorded at the same time."""

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="biomarker_tests")
    data = models.JSONField(blank=True, null=True, help_text="Legacy raw data")
    recorded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Test for {self.client} on {self.recorded_at}"


class BiomarkerResult(models.Model):
    """Individual biomarker value from a test session."""

    STATUS_CHOICES = [
        ("OPTIMAL", "Optimal"),
        ("NORMAL", "Normal"),
        ("LOW", "Low"),
        ("HIGH", "High"),
    ]

    id = models.AutoField(primary_key=True)
    test = models.ForeignKey(BiomarkerTest, on_delete=models.CASCADE, related_name="results")
    biomarker = models.ForeignKey(Biomarker, on_delete=models.CASCADE, related_name="results")
    value = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("test", "biomarker")

    def save(self, *args, **kwargs):
        """Auto-compute status based on biomarker ranges."""
        if not self.status:
            bm = self.biomarker
            if bm.optimal_min is not None and bm.optimal_max is not None:
                if bm.optimal_min <= self.value <= bm.optimal_max:
                    self.status = "OPTIMAL"
                elif bm.range_min <= self.value <= bm.range_max:
                    self.status = "NORMAL"
                elif self.value < bm.range_min:
                    self.status = "LOW"
                else:
                    self.status = "HIGH"
            else:
                if bm.range_min <= self.value <= bm.range_max:
                    self.status = "NORMAL"
                elif self.value < bm.range_min:
                    self.status = "LOW"
                else:
                    self.status = "HIGH"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.biomarker.name}: {self.value} {self.biomarker.unit} ({self.status})"


class PaymentInfo(models.Model):
    """Card payment details (only last 4 digits stored for security)."""

    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="payments")
    cardholder_name = models.CharField(max_length=200)
    card_last_four = models.CharField(max_length=4, help_text="Last 4 digits of card number")
    card_brand = models.CharField(max_length=50, blank=True, help_text="e.g. Visa, Mastercard")
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    payment_method = models.CharField(max_length=100, default="card")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING")
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe PaymentIntent ID")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment •••• {self.card_last_four} – ${self.amount} ({self.payment_status})"


class BillingAddress(models.Model):
    """Billing address associated with a payment."""

    id = models.AutoField(primary_key=True)
    payment = models.OneToOneField(PaymentInfo, on_delete=models.CASCADE, related_name="billing_address")
    street_address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.street_address}, {self.city}, {self.state} {self.zip_code}"


class Purchase(models.Model):
    """Ties a checkout transaction together: client + test kit + payment + billing → order."""

    PURCHASE_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="purchases")
    test_kit = models.ForeignKey("TestKit", on_delete=models.CASCADE, related_name="purchases")
    payment = models.OneToOneField(PaymentInfo, on_delete=models.CASCADE, related_name="purchase")
    order = models.OneToOneField("Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchase")
    status = models.CharField(max_length=20, choices=PURCHASE_STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Purchase #{self.id} – {self.test_kit.name} for {self.client}"

class Membership(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    membership_type = models.SmallIntegerField(default=1)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ShippingInfo(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    date_shipped = models.DateTimeField()
    tracking_number = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TestKit(models.Model):
    """Catalog of available test kits (e.g. Premium Test – 650 biomarkers)."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    biomarker_count = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10, help_text="Commission percentage for providers/dietitians (e.g., 10 for 10%)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.biomarker_count} biomarkers)"
    
    def get_price_for_quantity(self, quantity: int) -> Decimal:
        """Calculate the final price for a given quantity based on volume tiers."""
        from django.db.models import Q
        
        if quantity < 1:
            quantity = 1
        
        # Find applicable pricing tier
        tier = self.pricing_tiers.filter(
            min_quantity__lte=quantity
        ).filter(
            Q(max_quantity__isnull=True) | Q(max_quantity__gte=quantity)
        ).order_by("-min_quantity").first()
        if tier:
            discount_multiplier = (Decimal("100") - tier.discount_percent) / Decimal("100")
            unit_price = self.price * discount_multiplier
        else:
            unit_price = self.price
        return unit_price * quantity


class Order(models.Model):
    """Represents a placed test-kit order with shipping/tracking info."""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Order Confirmed"),
        ("SHIPPED", "Shipped"),
        ("IN_TRANSIT", "In Transit"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="orders")
    test_kit = models.ForeignKey(TestKit, on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1, help_text="Number of kits ordered")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    tracking_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order {self.order_number} – {self.test_kit.name} for {self.client}"


class DeliveryEvent(models.Model):
    """Individual delivery milestone (e.g. 'Order Placed', 'Kit Delivered')."""

    EVENT_TYPES = [
        ("ORDER_PLACED", "Order Placed"),
        ("SHIPPED", "Shipped"),
        ("IN_TRANSIT", "In Transit"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),
    ]

    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="delivery_events")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        status = "✓" if self.is_completed else "…"
        return f"[{status}] {self.title} – Order {self.order.order_number}"

class Client(models.Model):
    USER_TYPES = [("PROVIDER", "healthcare"), ("INDIVIDUAL", "individual")]
    # link to auth.user
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, blank=True, null=True)
    # extra fields
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=10, choices=USER_TYPES, default="INDIVIDUAL")
    date_of_birth = models.DateField(blank=True, null=True)
    bio=models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics', blank=True)
    gender = models.CharField(max_length=10, blank=True)
    height = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    ethnicity = models.CharField(max_length=100, blank=True)
    sport = models.CharField(max_length=100, blank=True)
    health_conditions = models.TextField(max_length=100, blank=True)
    dietary_preferences = models.TextField(max_length=100, blank=True)
    allergies = models.TextField(max_length=100, blank=True)
    dietary_recall = models.TextField(blank=True)
    dietary_typicality = models.PositiveSmallIntegerField(null=True, blank=True, help_text="How typical the 24-hour recall is on a 1-10 scale")
    dietary_preference_mode = models.CharField(max_length=20, blank=True, help_text="Whether the client wants similar or different recommendations")
    preferred_cuisines = models.TextField(blank=True)
    avoided_cuisines = models.TextField(blank=True)
    weekly_exercise_routine = models.TextField(blank=True)
    exercise_days_per_week = models.PositiveSmallIntegerField(null=True, blank=True)
    exercise_types = models.TextField(blank=True)
    provider_notes = models.TextField(blank=True)
    fitness_goal = models.CharField(max_length=100, blank=True)
    nutritional_goal = models.TextField(blank=True)
    # Referral system
    referral_code = models.CharField(
        max_length=16, unique=True, blank=True, null=True,
        help_text="Unique code used for provider referral links. Auto-generated for PROVIDER accounts."
    )
    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="referred_patients",
        help_text="The provider who referred this patient."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Auto-generate referral_code for PROVIDER accounts if not already set."""
        if self.type == "PROVIDER" and not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<Client {self.first_name} {self.last_name} ({self.email})>"

    @staticmethod
    def get_client_by_email(email) -> "Client":
        """
        Retrieve a Client object by email.
        Returns the Client instance if found, else None.
        """
        return Client.objects.filter(email=email).first()

    @staticmethod
    def get_client_by_id(client_id) -> "Client":
        """
        Retrieve a Client object by ID.
        Returns the Client instance if found, else None.
        """
        return Client.objects.filter(id=client_id).first()


class MealPlan(models.Model):
    """Represents a meal plan associated with a client and a list of meals.

    This model stores meal plan details, including the client, description, and meals for a specific timestamp.
    """

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    meals = models.TextField(help_text="JSON or comma-separated list of meals")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<MealPlan for client {self.client} for time {self.timestamp}: {self.meals}>"

    @staticmethod
    def get_meal_plans_by_client_and_date(
        client_id, start_date=None, end_date=None
    ) -> "models.QuerySet":
        """
        Retrieve MealPlan objects for a client within a date range.
        If no date range is provided, defaults to current week.
        Returns a QuerySet of MealPlan instances.
        """
        now = timezone.now()
        if start_date is None or end_date is None:
            # Get start and end of current week (Monday to Sunday)
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = start_of_week + timedelta(
                days=6, hours=23, minutes=59, seconds=59
            )
            start_date = start_of_week
            end_date = end_of_week
        return MealPlan.objects.filter(
            client_id=client_id, timestamp__range=(start_date, end_date)
        )

    @staticmethod
    def add_meal_plan(client, meals):
        pass


class Recommendation(models.Model):
    """Personalized recommendations for a client."""

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="recommendations")
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation for {self.client}: {self.text}"


class PricingTier(models.Model):
    """Volume discount tiers for B2B ordering."""

    id = models.AutoField(primary_key=True)
    test_kit = models.ForeignKey(TestKit, on_delete=models.CASCADE, related_name="pricing_tiers")
    min_quantity = models.PositiveIntegerField(help_text="Minimum quantity for this tier")
    max_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum quantity for this tier, null for unlimited")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Discount percentage (e.g., 5.00 for 5%)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["min_quantity"]
        unique_together = ("test_kit", "min_quantity")

    def __str__(self):
        max_qty = f"- {self.max_quantity}" if self.max_quantity else "+"
        return f"{self.test_kit.name}: {self.min_quantity} {max_qty} kits = {self.discount_percent}% off"


class DietitianCommission(models.Model):
    """Tracks commissions earned by dietitians on kit sales."""

    COMMISSION_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
    ]

    id = models.AutoField(primary_key=True)
    provider = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="earned_commissions", help_text="Provider/Dietitian who earned the commission")
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="commission", help_text="Order that triggered the commission")
    kit_quantity = models.PositiveIntegerField(default=1, help_text="Number of kits in the order")
    kit_price = models.FloatField(help_text="Price per kit at time of order")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10, help_text="Commission percentage (e.g., 10 for 10%)")
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Calculated commission amount (kit_price * kit_quantity * commission_percent / 100)")
    status = models.CharField(max_length=20, choices=COMMISSION_STATUS_CHOICES, default="PENDING")
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe transfer ID when payment is sent")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, help_text="When the commission was paid out")

    def __str__(self):
        return f"Commission for {self.provider.first_name} – ${self.commission_amount} ({self.status})"

    def save(self, *args, **kwargs):
        """Auto-calculate commission amount if not already set."""
        if not self.commission_amount:
            kit_price = Decimal(str(self.kit_price))
            kit_quantity = Decimal(self.kit_quantity)
            commission_percent = Decimal(str(self.commission_percent))
            self.commission_amount = (kit_price * kit_quantity * commission_percent) / Decimal("100")
        super().save(*args, **kwargs)
