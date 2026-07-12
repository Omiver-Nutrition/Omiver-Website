from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
from decimal import Decimal
from .fields import (
    EncryptedCharField, EncryptedTextField, EncryptedIntegerField,
    EncryptedFloatField, EncryptedDateField
)


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

class ShippingAddress(models.Model):
    """Postal addresses for clients (multiple addresses per client)."""

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        related_name="shipping_addresses",
    )
    label = models.CharField(max_length=50, blank=True, help_text="Label like 'Home' or 'Work'")
    street_address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        label = self.label or "Address"
        return f"{label} — {self.street_address}, {self.city}"


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
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="shipping_info", null=True, blank=True)
    date_shipped = models.DateTimeField()
    tracking_number = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DietLog(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="diet_logs")
    recall = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Diet log for {self.client} at {self.created_at}"

    @property
    def recorded_at(self):
        return self.created_at


class ExerciseLog(models.Model):
    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="exercise_logs")
    recall = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Exercise log for {self.client} at {self.created_at}"

    @property
    def recorded_at(self):
        return self.created_at


class TestKit(models.Model):
    """Catalog of available test kits (e.g. Premium Test – 650 biomarkers)."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    biomarker_count = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True, help_text="Whether this test kit is currently active and available for ordering")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.biomarker_count} biomarkers)"
    
    def get_price_for_quantity(self, quantity: int) -> Decimal:
        """Calculate the final price for a given quantity.

        Pricing tiers were removed; pricing is now linear by unit.
        """
        if quantity < 1:
            quantity = 1
        return self.price * quantity


class Order(models.Model):
    """Represents a placed test-kit order with shipping/tracking info."""

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("CONFIRMED", "Order Confirmed"),
        ("COLLECTED", "Collected"),
        ("TESTING", "Testing"),
        ("SHIPPED", "Shipped"),
        ("IN_TRANSIT", "In Transit"),
        ("OUT_FOR_DELIVERY", "Out for Delivery"),
        ("DELIVERED", "Delivered"),
        ("FINISHED", "Finished"),
        ("CANCELLED", "Cancelled"),
    ]

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="orders")

    order_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1, help_text="Number of kits ordered")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    forward_tracking_number = models.CharField(max_length=100, blank=True)
    return_tracking_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date"]

    def __str__(self):
        kit_name = self.test_kit.name if self.test_kit else "No Kit"
        return f"Order {self.order_number} – {kit_name} for {self.client}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        pending = getattr(self, "_pending_barcode_assignment", None)
        if pending:
            pending.order = self
            pending.client = self.client
            if pending.barcode_number.startswith("KIT-TEMP-"):
                pending.barcode_number = f"KIT-{self.order_number}"
            pending.save()
            self._pending_barcode_assignment = None

        # Update client of all assignments to match the order's client
        for assignment in self.barcode_assignments.all():
            if assignment.client_id != self.client_id:
                assignment.client = self.client
                assignment.save(update_fields=["client"])

    @property
    def barcode_assignment(self):
        return self.barcode_assignments.first()

    @barcode_assignment.setter
    def barcode_assignment(self, value):
        if value:
            if self.pk:
                value.order = self
                value.client = self.client
                value.save(update_fields=["order", "client"])
            else:
                self._pending_barcode_assignment = value
        else:
            if self.pk:
                self.barcode_assignments.all().update(order=None)
            else:
                self._pending_barcode_assignment = None

    @property
    def test_kit(self):
        first_assignment = self.barcode_assignments.first() if self.pk else getattr(self, "_pending_barcode_assignment", None)
        return first_assignment.test_kit if first_assignment else None

    @test_kit.setter
    def test_kit(self, value):
        first_assignment = self.barcode_assignments.first() if self.pk else getattr(self, "_pending_barcode_assignment", None)
        if first_assignment:
            first_assignment.test_kit = value
            if first_assignment.pk:
                first_assignment.save(update_fields=["test_kit"])
        else:
            import uuid
            placeholder_barcode = "KIT-TEMP-" + uuid.uuid4().hex[:8].upper()
            assignment = KitBarcodeAssignment(
                test_kit=value,
                barcode_number=placeholder_barcode,
                client=getattr(self, "client", None)
            )
            if self.pk:
                assignment.order = self
                assignment.save()
            else:
                self._pending_barcode_assignment = assignment

    @property
    def tracking_number(self):
        return self.forward_tracking_number

    @tracking_number.setter
    def tracking_number(self, value):
        self.forward_tracking_number = value or ""


class KitBarcodeAssignment(models.Model):
    """Maps a unique kit barcode to the client/test kit that owns it."""

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        "Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kit_barcode_assignments",
    )
    order = models.ForeignKey(
        "Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barcode_assignments",
    )
    test_kit = models.ForeignKey(TestKit, on_delete=models.CASCADE, related_name="barcode_assignments")
    barcode_number = models.CharField(max_length=100, unique=True, db_index=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order_id and not self.barcode_number.startswith("KIT-"):
            KitBarcodeAssignment.objects.filter(
                order=self.order,
                barcode_number__startswith="KIT-"
            ).delete()

    def __str__(self):
        has_order = getattr(self, "order", None)
        order_label = (self.order.order_number if has_order else "unassigned")
        return f"Barcode {self.barcode_number} – {order_label}"

    @property
    def order_number(self):
        has_order = getattr(self, "order", None)
        return self.order.order_number if has_order else None


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


class KitCollection(models.Model):
    """Tracks the lifecycle of a kit barcode for a client and order."""

    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("SHIPPING", "Shipping"),
        ("DELIVERED", "Delivered"),
        ("COLLECTED", "Collected"),
        ("PENDING", "Pending"),
        ("TESTING", "Testing"),
        ("FINISHED", "Finished"),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey("Client", on_delete=models.CASCADE, related_name="kit_collections")
    order = models.OneToOneField("Order", on_delete=models.CASCADE, related_name="kit_collection", null=True, blank=True)
    kit_barcode = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    collected_at = models.DateTimeField(null=True, blank=True)
    diet_log = models.OneToOneField("DietLog", on_delete=models.SET_NULL, null=True, blank=True, related_name="kit_collection")
    exercise_log = models.OneToOneField("ExerciseLog", on_delete=models.SET_NULL, null=True, blank=True, related_name="kit_collection")
    shipping_event = models.ForeignKey("ShippingInfo", on_delete=models.SET_NULL, null=True, blank=True, related_name="kit_collections")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Kit collection {self.kit_barcode} – {self.status}"


class KitResult(models.Model):
    """Stores the final result payload for a kit barcode."""

    id = models.AutoField(primary_key=True)
    kit_barcode = models.CharField(max_length=100, unique=True, db_index=True)
    result_info = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Result for {self.kit_barcode}"

class Client(models.Model):
    USER_TYPES = [("PROVIDER", "healthcare"), ("INDIVIDUAL", "individual")]
    SECURITY_QUESTIONS = [
        ("PET", "What was the name of your first pet?"),
        ("MOTHER", "What is your mother's maiden name?"),
        ("CITY", "In what city were you born?"),
        ("SCHOOL", "What was the name of your first school?"),
        ("CAR", "What was the make of your first car?"),
    ]
    # link to auth.user
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, blank=True, null=True)
    security_question = models.CharField(max_length=255, choices=SECURITY_QUESTIONS, blank=True)
    security_answer = models.CharField(max_length=255, blank=True)
    # extra fields
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    first_name = EncryptedCharField(max_length=255, blank=True)
    last_name = EncryptedCharField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=USER_TYPES, default="INDIVIDUAL")
    date_of_birth = EncryptedDateField(blank=True, null=True)
    bio = EncryptedTextField(max_length=500, blank=True)
    location = EncryptedCharField(max_length=255, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics', blank=True)
    gender = EncryptedCharField(max_length=255, blank=True)
    height = EncryptedFloatField(blank=True, null=True)
    weight = EncryptedFloatField(blank=True, null=True)
    ethnicity = EncryptedCharField(max_length=255, blank=True)
    sport = EncryptedCharField(max_length=255, blank=True)
    health_conditions = EncryptedTextField(max_length=255, blank=True)
    dietary_preferences = EncryptedTextField(max_length=255, blank=True)
    allergies = EncryptedTextField(max_length=255, blank=True)
    dietary_typicality = EncryptedIntegerField(null=True, blank=True, help_text="How typical the 24-hour recall is on a 5-level scale from unusual to always")
    dietary_preference_mode = EncryptedCharField(max_length=255, blank=True, help_text="Whether the client wants similar or different recommendations")
    preferred_cuisines = EncryptedTextField(blank=True)
    avoided_cuisines = EncryptedTextField(blank=True)
    weekly_exercise_routine = EncryptedTextField(blank=True)
    exercise_days_per_week = EncryptedIntegerField(null=True, blank=True)
    exercise_types = EncryptedTextField(blank=True)
    provider_notes = EncryptedTextField(blank=True)
    fitness_goal = EncryptedCharField(max_length=255, blank=True)
    nutritional_goal = EncryptedTextField(blank=True)
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
        return f"Client {self.id} ({self.email})"

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
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
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

    STATUS_CHOICES = [
        ("DRAFT", "AI Draft Generated"),
        ("PENDING_REVIEW", "Pending Doctor Review"),
        ("REVISING", "AI Revising"),
        ("APPROVED", "Approved"),
    ]

    id = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="recommendations")
    biomarker_test = models.ForeignKey("BiomarkerTest", on_delete=models.CASCADE, related_name="recommendations", null=True, blank=True)
    
    text = models.CharField(max_length=500, blank=True, help_text="Fallback or summary recommendation text")
    
    dietary_draft = models.JSONField(blank=True, null=True, help_text="AI generated initial diet plan")
    exercise_draft = models.JSONField(blank=True, null=True, help_text="AI generated initial exercise plan")
    
    doctor_feedback = models.TextField(blank=True, help_text="Doctor feedback to AI for adjustments")
    doctor_notes = models.TextField(blank=True, help_text="Additional public notes from doctor directly to patient")
    
    dietary_final = models.JSONField(blank=True, null=True, help_text="Refined final diet plan")
    exercise_final = models.JSONField(blank=True, null=True, help_text="Refined final exercise plan")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    approved_by = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'type': 'PROVIDER'}, related_name="approved_recommendations")
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recommendation ({self.status}) for {self.client}"



