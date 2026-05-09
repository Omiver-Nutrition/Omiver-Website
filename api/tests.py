import csv

from django.test import TestCase
from django.urls import reverse

from core.models import Client, Order, TestKit


class ExportOrdersCsvTests(TestCase):
	def setUp(self):
		self.client_a = Client.objects.create(
			email="alice@example.com",
			first_name="Alice",
			last_name="Ng",
			type="INDIVIDUAL",
		)
		self.client_b = Client.objects.create(
			email="bob@example.com",
			first_name="Bob",
			last_name="Ray",
			type="INDIVIDUAL",
		)
		self.kit = TestKit.objects.create(
			name="Starter Kit",
			biomarker_count=120,
			description="Starter",
			price="99.00",
		)

		self.order_a = Order.objects.create(
			client=self.client_a,
			test_kit=self.kit,
			order_number="ORD-ALICE-001",
			tracking_number="TRK-1",
			status="PENDING",
			quantity=2,
		)
		self.order_b = Order.objects.create(
			client=self.client_b,
			test_kit=self.kit,
			order_number="ORD-BOB-001",
			tracking_number="TRK-2",
			status="CONFIRMED",
			quantity=1,
		)

	def test_export_orders_csv_returns_attachment(self):
		response = self.client.get(reverse("export_orders_csv"))

		self.assertEqual(response.status_code, 200)
		self.assertIn("text/csv", response["Content-Type"])
		self.assertIn("attachment; filename=", response["Content-Disposition"])

		rows = list(csv.reader(response.content.decode("utf-8").splitlines()))
		self.assertEqual(
			rows[0],
			[
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
			],
		)

		exported_order_numbers = {row[1] for row in rows[1:]}
		self.assertIn(self.order_a.order_number, exported_order_numbers)
		self.assertIn(self.order_b.order_number, exported_order_numbers)

	def test_export_orders_csv_supports_client_filter(self):
		response = self.client.get(reverse("export_orders_csv"), {"client_id": self.client_a.id})

		self.assertEqual(response.status_code, 200)
		rows = list(csv.reader(response.content.decode("utf-8").splitlines()))

		self.assertEqual(len(rows), 2)  # header + 1 filtered row
		self.assertEqual(rows[1][1], self.order_a.order_number)
		self.assertEqual(rows[1][6], str(self.client_a.id))
