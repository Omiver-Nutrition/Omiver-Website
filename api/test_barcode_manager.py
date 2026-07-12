import uuid
from decimal import Decimal
from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from core.models import Client, Order, KitBarcodeAssignment, TestKit
from django.contrib.auth.models import User
from api.barcode_manager import (
    BarcodeManager,
    ClientNotFoundError,
    BarcodeNotFoundError,
    BarcodeConflictError,
    BarcodeMismatchError,
    OrderNotFoundError,
)

class BarcodeManagerTests(TestCase):
    def setUp(self):
        # Create users
        self.user_1 = User.objects.create_user(username="user1@example.com", password="password")
        self.user_2 = User.objects.create_user(username="user2@example.com", password="password")
        
        # Create clients
        self.client_1 = Client.objects.create(
            user=self.user_1,
            email=self.user_1.username,
            first_name="John",
            last_name="Doe",
            type="INDIVIDUAL",
        )
        self.client_2 = Client.objects.create(
            user=self.user_2,
            email=self.user_2.username,
            first_name="Jane",
            last_name="Smith",
            type="INDIVIDUAL",
        )

        # Create test kit
        self.kit = TestKit.objects.create(
            name="Metabolic Starter",
            biomarker_count=10,
            description="Basic metabolic panel",
            price=Decimal("150.00"),
        )

        # Create barcode assignments
        self.barcode_1 = "KIT-BARCODE1"
        self.assignment_1 = KitBarcodeAssignment.objects.create(
            barcode_number=self.barcode_1,
            test_kit=self.kit,
        )

        self.barcode_2 = "KIT-BARCODE2"
        self.assignment_2 = KitBarcodeAssignment.objects.create(
            barcode_number=self.barcode_2,
            test_kit=self.kit,
        )

    def test_link_barcode_to_client_creates_order_when_none_exists(self):
        # When no active order exists
        assignment, already_linked = BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        self.assertFalse(already_linked)
        self.assertEqual(assignment.client, self.client_1)
        self.assertIsNotNone(assignment.order)
        self.assertEqual(assignment.order.status, "CREATED")
        self.assertEqual(assignment.order.client, self.client_1)

    def test_link_barcode_to_client_uses_existing_active_order(self):
        # Pre-create an active order for client_1
        order = Order.objects.create(
            client=self.client_1,
            order_number="ORD-EXISTING1",
            status="CREATED",
        )

        assignment, already_linked = BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        self.assertFalse(already_linked)
        self.assertEqual(assignment.client, self.client_1)
        self.assertEqual(assignment.order, order)

    def test_link_barcode_to_client_already_linked(self):
        # Link it first
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        # Link again
        assignment, already_linked = BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        self.assertTrue(already_linked)
        self.assertEqual(assignment.client, self.client_1)

    def test_link_barcode_to_client_raises_client_not_found(self):
        with self.assertRaises(ClientNotFoundError):
            BarcodeManager.link_barcode_to_client(self.barcode_1, 99999)

    def test_link_barcode_to_client_raises_barcode_not_found(self):
        with self.assertRaises(BarcodeNotFoundError):
            BarcodeManager.link_barcode_to_client("KIT-NONEXISTENT", self.client_1.id)

    def test_link_barcode_to_client_raises_barcode_conflict(self):
        # Link barcode_1 to client_1
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        # Attempt to link barcode_1 to client_2
        with self.assertRaises(BarcodeConflictError):
            BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_2.id)

    def test_link_barcode_to_client_raises_barcode_mismatch(self):
        # Pre-create an active order and assign barcode_1 to it
        order = Order.objects.create(
            client=self.client_1,
            order_number="ORD-MATCH",
            status="CREATED",
            test_kit=self.kit,
        )
        self.assignment_1.order = order
        self.assignment_1.client = self.client_1
        self.assignment_1.save()

        # Try to link barcode_2 to the same client (will find order with different assigned barcode)
        with self.assertRaises(BarcodeMismatchError):
            BarcodeManager.link_barcode_to_client(self.barcode_2, self.client_1.id)

    def test_unlink_barcode_from_client_success(self):
        # First link
        assignment, _ = BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        order = assignment.order

        # Now unlink
        res = BarcodeManager.unlink_barcode_from_client(self.barcode_1, self.client_1.id)
        self.assertTrue(res)

        # Check state of assignment
        assignment.refresh_from_db()
        self.assertNullClientAndOrder = (assignment.client is None and assignment.order is None)
        self.assertTrue(self.assertNullClientAndOrder)

        # Check that a placeholder was created for the order
        placeholders = KitBarcodeAssignment.objects.filter(order=order)
        self.assertEqual(placeholders.count(), 1)
        self.assertTrue(placeholders.first().barcode_number.startswith("KIT-"))

    def test_unlink_barcode_from_client_raises_not_found(self):
        with self.assertRaises(BarcodeNotFoundError):
            BarcodeManager.unlink_barcode_from_client("KIT-NONEXISTENT", self.client_1.id)

        # Try to unlink a barcode linked to another client
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        with self.assertRaises(BarcodeNotFoundError):
            BarcodeManager.unlink_barcode_from_client(self.barcode_1, self.client_2.id)

    def test_mark_collected_success(self):
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        assignment = BarcodeManager.mark_collected(self.barcode_1, self.client_1.id)
        self.assertIsNotNone(assignment.collected_at)

    def test_mark_collected_success_with_explicit_time(self):
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        explicit_time = timezone.make_aware(datetime(2026, 7, 10, 12, 0, 0))
        assignment = BarcodeManager.mark_collected(self.barcode_1, self.client_1.id, collected_at=explicit_time)
        self.assertEqual(assignment.collected_at, explicit_time)

    def test_mark_collected_raises_not_found(self):
        with self.assertRaises(BarcodeNotFoundError):
            BarcodeManager.mark_collected("KIT-NONEXISTENT")

    def test_mark_collected_raises_conflict_if_different_client(self):
        BarcodeManager.link_barcode_to_client(self.barcode_1, self.client_1.id)
        
        with self.assertRaises(BarcodeConflictError):
            BarcodeManager.mark_collected(self.barcode_1, self.client_2.id)

    def test_assign_barcode_to_order_success(self):
        order = Order.objects.create(
            client=self.client_1,
            order_number="ORD-ASSIGN1",
            status="CREATED",
            test_kit=self.kit,
        )

        assignment, created = BarcodeManager.assign_barcode_to_order("ORD-ASSIGN1", self.barcode_1)
        self.assertEqual(assignment.order, order)
        self.assertEqual(assignment.client, self.client_1)
        self.assertEqual(assignment.test_kit, self.kit)

    def test_assign_barcode_to_order_raises_not_found(self):
        with self.assertRaises(OrderNotFoundError):
            BarcodeManager.assign_barcode_to_order("ORD-NONEXISTENT", self.barcode_1)
