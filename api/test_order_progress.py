"""Tests for the order's derived status and round-trip progress.

`Order.status` is no longer a column: it is folded out of the order's
`DeliveryEvent` feed. These tests pin down that fold, because it is now the
single source of truth for everything the customer sees about where their kit
is.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Client, DeliveryEvent, Order, TestKit


class OrderStatusDerivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rider@example.com", password="pw")
        self.client_obj = Client.objects.create(
            user=self.user,
            email=self.user.username,
            first_name="Rae",
            last_name="Rider",
            type="INDIVIDUAL",
        )
        self.kit = TestKit.objects.create(
            name="Round Trip Panel",
            biomarker_count=10,
            description="",
            price=Decimal("100.00"),
        )
        self.order = Order.objects.create(
            client=self.client_obj,
            test_kit=self.kit,
            order_number="ORD-RT-1",
            quantity=1,
        )

    def _stage(self, key):
        return next(s for s in self.order.progress if s["key"] == key)

    def test_order_with_no_events_is_created(self):
        self.assertEqual(self.order.status, "CREATED")
        self.assertEqual([s["done"] for s in self.order.progress], [False] * 5)

    def test_order_placed_event_reports_as_created(self):
        """The event feed says ORDER_PLACED; the public vocabulary says CREATED."""
        self.order.record_event("ORDER_PLACED")

        self.assertEqual(self.order.status, "CREATED")
        self.assertTrue(self._stage("ORDER_PLACED")["done"])
        self.assertFalse(self._stage("SHIPPED")["done"])

    def test_status_reports_the_furthest_stage_not_the_latest_event(self):
        """A stray early event must not drag a further-along order backwards."""
        self.order.record_event("DELIVERED")
        self.order.record_event("ORDER_PLACED")

        self.assertEqual(self.order.status, "DELIVERED")

    def test_carrier_scans_roll_up_to_shipped_but_keep_their_own_name(self):
        self.order.record_event("OUT_FOR_DELIVERY")

        # The precise scan is preserved for display...
        self.assertEqual(self.order.status, "OUT_FOR_DELIVERY")
        # ...but it is the SHIPPED milestone that lights up, not a sixth stage.
        self.assertTrue(self._stage("SHIPPED")["done"])
        self.assertFalse(self._stage("DELIVERED")["done"])

    def test_earlier_stages_complete_when_a_later_event_arrives(self):
        """Carriers skip scans, so DELIVERED implies the kit shipped."""
        self.order.record_event("DELIVERED")

        self.assertTrue(self._stage("ORDER_PLACED")["done"])
        self.assertTrue(self._stage("SHIPPED")["done"])
        self.assertTrue(self._stage("DELIVERED")["done"])
        self.assertFalse(self._stage("SAMPLE_SHIPPED")["done"])

    def test_return_leg_progresses_after_delivery(self):
        self.order.record_event("DELIVERED")
        self.order.record_event("SAMPLE_SHIPPED")

        self.assertEqual(self.order.status, "SAMPLE_SHIPPED")
        self.assertTrue(self._stage("SAMPLE_SHIPPED")["done"])
        self.assertFalse(self._stage("SAMPLE_DELIVERED")["done"])

        self.order.record_event("SAMPLE_DELIVERED")
        self.assertEqual(self.order.status, "SAMPLE_DELIVERED")
        self.assertTrue(all(s["done"] for s in self.order.progress))

    def test_journey_is_split_into_outbound_and_return_legs(self):
        legs = [s["leg"] for s in self.order.progress]
        self.assertEqual(legs, ["outbound", "outbound", "outbound", "return", "return"])

    def test_cancellation_short_circuits_the_journey(self):
        self.order.record_event("SHIPPED")
        self.order.record_event("CANCELLED")

        self.assertEqual(self.order.status, "CANCELLED")
        # A cancelled order is not "partly complete"; nothing is shown as done.
        self.assertFalse(any(s["done"] for s in self.order.progress))

    def test_stage_timestamp_is_the_first_time_it_happened(self):
        first = self.order.record_event("SHIPPED")
        self.order.record_event("IN_TRANSIT")

        self.assertEqual(self._stage("SHIPPED")["timestamp"], first.timestamp)

    def test_get_status_display_is_human_readable(self):
        self.order.record_event("SAMPLE_SHIPPED")

        self.assertEqual(self.order.get_status_display(), "Sample Shipped")

    def test_record_event_completes_previous_events(self):
        self.order.record_event("SHIPPED")
        self.order.record_event("DELIVERED")

        self.assertEqual(self.order.delivery_events.filter(is_completed=False).count(), 0)

    def test_unknown_events_do_not_affect_progress(self):
        """Events outside the journey (e.g. an exception scan) are inert."""
        DeliveryEvent.objects.create(order=self.order, event_type="ORDER_PLACED", title="Placed")
        DeliveryEvent.objects.create(order=self.order, event_type="CUSTOMS_HOLD", title="Held")

        self.assertEqual(self.order.status, "CREATED")


class OrderProgressApiTests(TestCase):
    """The app renders the timeline straight from the API payload."""

    def setUp(self):
        self.user = User.objects.create_user(username="api@example.com", password="pw")
        self.client_obj = Client.objects.create(
            user=self.user,
            email=self.user.username,
            first_name="Ada",
            last_name="Api",
            type="INDIVIDUAL",
        )
        self.kit = TestKit.objects.create(
            name="API Panel", biomarker_count=5, description="", price=Decimal("50.00")
        )
        self.order = Order.objects.create(
            client=self.client_obj, test_kit=self.kit, order_number="ORD-API-1", quantity=1
        )
        self.order.record_event("SAMPLE_SHIPPED")

    def test_order_detail_exposes_progress_and_display_status(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("order_detail", args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SAMPLE_SHIPPED")
        self.assertEqual(payload["status_display"], "Sample Shipped")

        progress = payload["progress"]
        self.assertEqual([s["key"] for s in progress], [
            "ORDER_PLACED", "SHIPPED", "DELIVERED", "SAMPLE_SHIPPED", "SAMPLE_DELIVERED",
        ])
        self.assertEqual([s["done"] for s in progress], [True, True, True, True, False])

        # Only the stage that actually has an event carries a timestamp, and it
        # must be a JSON-safe string rather than a datetime. Stages that are
        # merely implied by a later event are done but undated.
        by_key = {s["key"]: s for s in progress}
        self.assertIsInstance(by_key["SAMPLE_SHIPPED"]["timestamp"], str)
        self.assertIsNone(by_key["ORDER_PLACED"]["timestamp"])
        self.assertIsNone(by_key["SAMPLE_DELIVERED"]["timestamp"])
