import uuid
from decimal import Decimal
from django.db import transaction
from core.models import (
    Client, TestKit, Order, KitBarcodeAssignment, DeliveryEvent,
    PaymentInfo, BillingAddress, Purchase, KitCollection
)

class OrderIntakeError(Exception):
    """Base exception for order intake errors."""
    pass

class ClientNotFoundError(OrderIntakeError):
    """Raised when the client does not exist."""
    pass

class TestKitNotFoundError(OrderIntakeError):
    """Raised when the test kit does not exist."""
    pass

class InvalidPaymentInfoError(OrderIntakeError):
    """Raised when the payment details are invalid."""
    pass


class OrderManager:
    @staticmethod
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

    @staticmethod
    def _ensure_collection_for_order(order: Order, kit_barcode: str | None = None) -> KitCollection:
        barcode_value = (kit_barcode or getattr(getattr(order, "barcode_assignment", None), "barcode_number", "") or order.order_number).strip()
        collection, _ = KitCollection.objects.get_or_create(
            order=order,
            defaults={
                "user": order.client,
                "kit_barcode": barcode_value,
                "status": order.status if order.status in dict(KitCollection.STATUS_CHOICES) else "CREATED",
            },
        )
        updates = []
        if collection.user_id != order.client_id:
            collection.user = order.client
            updates.append("user")
        if barcode_value and collection.kit_barcode != barcode_value:
            collection.kit_barcode = barcode_value
            updates.append("kit_barcode")
        if updates:
            collection.save(update_fields=updates + ["updated_at"])
        return collection

    @staticmethod
    @transaction.atomic
    def intake_order(
        client_id: int,
        test_kit_id: int,
        order_number: str | None = None,
        barcode_number: str | None = None,
        forward_tracking_number: str | None = None,
        return_tracking_number: str | None = None,
        payment_data: dict | None = None,
        billing_address_data: dict | None = None
    ) -> Order:
        """
        Processes and records an order, handling both free and paid checkouts.
        """
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            raise ClientNotFoundError("Client not found")

        try:
            kit = TestKit.objects.get(pk=test_kit_id)
        except TestKit.DoesNotExist:
            raise TestKitNotFoundError("Test kit not found")

        # 1. Handle Payment if provided
        payment = None
        if payment_data:
            try:
                month_str, year_str = payment_data["expiry_date"].split("/")
                expiry_month = int(month_str)
                expiry_year = int("20" + year_str) if len(year_str) == 2 else int(year_str)
            except (ValueError, IndexError, KeyError):
                raise InvalidPaymentInfoError("expiry_date must be in MM/YY format")

            raw_card_number = payment_data.get("card_number", "").replace(" ", "").replace("-", "")
            if not raw_card_number or len(raw_card_number) < 4:
                raise InvalidPaymentInfoError("Invalid card number")

            payment = PaymentInfo.objects.create(
                client=client,
                cardholder_name=payment_data.get("cardholder_name", ""),
                card_last_four=raw_card_number[-4:],
                card_brand=OrderManager._detect_card_brand(raw_card_number),
                expiry_month=expiry_month,
                expiry_year=expiry_year,
                amount=payment_data.get("amount") or kit.price,
                payment_status="COMPLETED",
            )

            # Record billing address
            if billing_address_data:
                BillingAddress.objects.create(
                    payment=payment,
                    street_address=billing_address_data.get("street_address", ""),
                    city=billing_address_data.get("city", ""),
                    state=billing_address_data.get("state", ""),
                    zip_code=billing_address_data.get("zip_code", ""),
                )

        # 2. Handle Barcode Assignment
        if not barcode_number:
            barcode_number = "KIT-" + uuid.uuid4().hex[:8].upper()

        barcode_assignment, _ = KitBarcodeAssignment.objects.update_or_create(
            barcode_number=barcode_number,
            defaults={
                "client": client,
                "test_kit": kit,
            }
        )

        # 3. Create the Order
        if not order_number:
            order_number = uuid.uuid4().hex[:14]

        order = Order.objects.create(
            client=client,
            barcode_assignment=barcode_assignment,
            order_number=order_number,
            forward_tracking_number=forward_tracking_number or "",
            return_tracking_number=return_tracking_number or "",
            status="CREATED",
        )

        # Ensure collection entry
        OrderManager._ensure_collection_for_order(order, kit_barcode=barcode_number)

        # 4. Seed initial delivery event
        DeliveryEvent.objects.create(
            order=order,
            event_type="ORDER_PLACED",
            title="Order Placed",
            description="Your order has been received",
            is_completed=True,
        )

        # 5. Create Purchase if payment was made
        if payment:
            Purchase.objects.create(
                client=client,
                test_kit=kit,
                payment=payment,
                order=order,
                status="COMPLETED",
            )

        return order
