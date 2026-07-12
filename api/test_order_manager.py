import uuid
from decimal import Decimal
from django.test import TestCase
from core.models import Client, TestKit, Order, PaymentInfo, BillingAddress, Purchase, KitBarcodeAssignment, DeliveryEvent
from django.contrib.auth.models import User
from api.order_manager import (
    OrderManager,
    OrderIntakeError,
    ClientNotFoundError,
    TestKitNotFoundError,
    InvalidPaymentInfoError,
)

class OrderManagerTests(TestCase):
    def setUp(self):
        # Create user & client
        self.user = User.objects.create_user(username="customer@example.com", password="password")
        self.client = Client.objects.create(
            user=self.user,
            email=self.user.username,
            first_name="Alice",
            last_name="Wonderland",
            type="INDIVIDUAL",
        )

        # Create test kit
        self.kit = TestKit.objects.create(
            name="Advanced Biomarker Panel",
            biomarker_count=50,
            description="Premium health check",
            price=Decimal("299.00"),
        )

    def test_intake_order_free_success(self):
        # Intake a free order (no payment info)
        order = OrderManager.intake_order(
            client_id=self.client.id,
            test_kit_id=self.kit.id,
        )

        self.assertIsNotNone(order)
        self.assertEqual(order.client, self.client)
        self.assertEqual(order.status, "CREATED")
        self.assertTrue(order.order_number != "")
        
        # Verify barcode assignment was created
        self.assertIsNotNone(order.barcode_assignment)
        self.assertTrue(order.barcode_assignment.barcode_number.startswith("KIT-"))
        
        # Verify delivery event was seeded
        events = DeliveryEvent.objects.filter(order=order)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().event_type, "ORDER_PLACED")
        
        # Verify NO purchase or payment records exist
        self.assertFalse(PaymentInfo.objects.filter(client=self.client).exists())
        self.assertFalse(Purchase.objects.filter(client=self.client).exists())

    def test_intake_order_paid_success(self):
        payment_data = {
            "cardholder_name": "Alice Wonderland",
            "card_number": "4111 2222 3333 4444",
            "expiry_date": "12/28",
        }
        billing_data = {
            "street_address": "123 Magic St",
            "city": "Wonderland",
            "state": "Fantasy",
            "zip_code": "90210",
        }

        # Intake a paid order
        order = OrderManager.intake_order(
            client_id=self.client.id,
            test_kit_id=self.kit.id,
            payment_data=payment_data,
            billing_address_data=billing_data,
        )

        self.assertIsNotNone(order)
        
        # Verify payment was created
        payment = PaymentInfo.objects.get(client=self.client)
        self.assertEqual(payment.cardholder_name, "Alice Wonderland")
        self.assertEqual(payment.card_last_four, "4444")
        self.assertEqual(payment.card_brand, "Visa")
        self.assertEqual(payment.expiry_month, 12)
        self.assertEqual(payment.expiry_year, 2028)
        self.assertEqual(payment.amount, self.kit.price)
        self.assertEqual(payment.payment_status, "COMPLETED")

        # Verify billing address was created
        billing = BillingAddress.objects.get(payment=payment)
        self.assertEqual(billing.street_address, "123 Magic St")

        # Verify purchase record was created
        purchase = Purchase.objects.get(order=order)
        self.assertEqual(purchase.client, self.client)
        self.assertEqual(purchase.test_kit, self.kit)
        self.assertEqual(purchase.payment, payment)
        self.assertEqual(purchase.status, "COMPLETED")

    def test_intake_order_raises_client_not_found(self):
        with self.assertRaises(ClientNotFoundError):
            OrderManager.intake_order(99999, self.kit.id)

    def test_intake_order_raises_test_kit_not_found(self):
        with self.assertRaises(TestKitNotFoundError):
            OrderManager.intake_order(self.client.id, 99999)

    def test_intake_order_raises_invalid_payment_expiry(self):
        payment_data = {
            "cardholder_name": "Alice Wonderland",
            "card_number": "4111 2222 3333 4444",
            "expiry_date": "invalid-date",
        }
        with self.assertRaises(InvalidPaymentInfoError):
            OrderManager.intake_order(
                client_id=self.client.id,
                test_kit_id=self.kit.id,
                payment_data=payment_data,
            )
