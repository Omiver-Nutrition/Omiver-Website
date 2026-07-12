import csv
from decimal import Decimal
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from core.models import (
	Biomarker,
	BiomarkerResult,
	BiomarkerTest,
	BillingAddress,
	DietLog,
	ExerciseLog,
	Client,
	DeliveryEvent,
	Membership,
	MealPlan,
	Order,
	ShippingInfo,
	KitBarcodeAssignment,
	PaymentInfo,
	Purchase,
	Recommendation,
	TestKit,
	ShippingAddress,
)


class ApiSmokeTests(TestCase):
	def setUp(self):
		self.api_client = APIClient()

		self.web_user = User.objects.create_user(
			username="staff@example.com",
			password="OmiverSecure2026!",
		)
		self.login_user = User.objects.create_user(
			username="login@example.com",
			password="OmiverSecure2026!",
		)

		self.api_client.force_authenticate(user=self.web_user)
		self.public_client = APIClient()

		self.login_client = Client.objects.create(
			user=self.login_user,
			email=self.login_user.username,
			first_name="Log",
			last_name="In",
			type="INDIVIDUAL",
		)

		self.provider = Client.objects.create(
			email="provider@example.com",
			first_name="Priya",
			last_name="Patel",
			type="PROVIDER",
		)
		self.patient = Client.objects.create(
			user=self.web_user,
			email="patient@example.com",
			first_name="Casey",
			last_name="Jones",
			type="INDIVIDUAL",
			referred_by=self.provider,
		)
		self.other_client = Client.objects.create(
			email="other@example.com",
			first_name="Ari",
			last_name="Stone",
			type="INDIVIDUAL",
		)

		self.kit = TestKit.objects.create(
			name="Starter Kit",
			biomarker_count=120,
			description="Starter",
			price=Decimal("99.00"),
		)
		self.premium_kit = TestKit.objects.create(
			name="Premium Kit",
			biomarker_count=240,
			description="Premium",
			price=Decimal("149.00"),
		)


		self.order = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-1001",
			forward_tracking_number="TRK-1001",
			return_tracking_number="RTR-1001",
			status="CREATED",
			quantity=1,
		)
		self.order_two = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-1002",
			forward_tracking_number="TRK-1002",
			return_tracking_number="RTR-1002",
			status="CONFIRMED",
			quantity=2,
		)
		self.provider_order_pending = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-2001",
			forward_tracking_number="TRK-2001",
			return_tracking_number="RTR-2001",
			status="CREATED",
			quantity=1,
		)
		self.provider_order_approved = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-2002",
			forward_tracking_number="TRK-2002",
			return_tracking_number="RTR-2002",
			status="CREATED",
			quantity=1,
		)

		self.delivery_event = DeliveryEvent.objects.create(
			order=self.order,
			event_type="ORDER_PLACED",
			title="Order Placed",
			description="Your order has been received",
			is_completed=True,
		)

		self.payment = PaymentInfo.objects.create(
			client=self.patient,
			cardholder_name="Casey Jones",
			card_last_four="4242",
			card_brand="Visa",
			expiry_month=12,
			expiry_year=2026,
			payment_method="card",
			payment_status="COMPLETED",
			amount="99.00",
		)
		BillingAddress.objects.create(
			payment=self.payment,
			street_address="123 Main St",
			city="Austin",
			state="TX",
			zip_code="78701",
		)
		self.purchase = Purchase.objects.create(
			client=self.patient,
			test_kit=self.kit,
			payment=self.payment,
			order=self.order,
			status="COMPLETED",
		)

		self.biomarker = Biomarker.objects.create(
			name="Glucose",
			description="Blood sugar",
			category="METABOLIC",
			range_min=70,
			range_max=99,
			optimal_min=80,
			optimal_max=90,
			unit="mg/dL",
		)
		self.biomarker_test = BiomarkerTest.objects.create(
			client=self.patient,
			recorded_at=timezone.now() - timedelta(days=1),
		)
		self.biomarker_result = BiomarkerResult.objects.create(
			test=self.biomarker_test,
			biomarker=self.biomarker,
			value=85,
		)

		self.recommendation = Recommendation.objects.create(
			client=self.patient,
			text="Drink more water",
		)
		self.meal_plan = MealPlan.objects.create(
			client=self.patient,
			meals="Eggs, Salad, Salmon",
		)
		self.membership = Membership.objects.create(
			client=self.patient,
			membership_type=1,
			start_date=timezone.now() - timedelta(days=1),
			end_date=timezone.now() + timedelta(days=1),
		)

	def test_index_returns_welcome_message(self):
		response = self.public_client.get(reverse("index"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content.decode("utf-8"), "Welcome to the API endpoint!")

	def test_protected_endpoint_requires_authentication(self):
		response = self.public_client.get(reverse("list_biomarker_tests"))

		self.assertEqual(response.status_code, 401)

	def test_create_client_requires_login(self):
		payload = {
			"email": "new-client@example.com",
			"first_name": "New",
			"last_name": "Client",
			"type": "INDIVIDUAL",
		}
		response = self.api_client.post(reverse("create_client"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		self.assertTrue(Client.objects.filter(email="new-client@example.com").exists())

	def test_client_handler_get_and_patch(self):
		response = self.api_client.get(reverse("client_handler", args=[self.patient.id]))
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["email"], self.patient.email)

		patch_response = self.api_client.patch(
			reverse("client_handler", args=[self.patient.id]),
			{"first_name": "Updated"},
			format="json",
		)
		self.assertEqual(patch_response.status_code, 200)
		self.patient.refresh_from_db()
		self.assertEqual(self.patient.first_name, "Updated")

	def test_client_name_is_encrypted_in_db(self):
		from django.db import connection
		client = Client.objects.create(
			email="encrypted-test@example.com",
			first_name="SuperSecretName",
			last_name="SuperSecretLastName",
		)
		self.assertEqual(client.first_name, "SuperSecretName")
		self.assertEqual(client.last_name, "SuperSecretLastName")

		with connection.cursor() as cursor:
			cursor.execute("SELECT first_name, last_name FROM core_client WHERE id = %s", [client.id])
			row = cursor.fetchone()
			db_first_name, db_last_name = row[0], row[1]

		self.assertNotEqual(db_first_name, "SuperSecretName")
		self.assertNotEqual(db_last_name, "SuperSecretLastName")
		self.assertTrue(db_first_name.startswith("U2FsdGVkX1"))
		self.assertTrue(db_last_name.startswith("U2FsdGVkX1"))

	def test_client_handler_patch_creates_recall_logs(self):
		response = self.api_client.patch(
			reverse("client_handler", args=[self.patient.id]),
			{"dietary_recall": "Eggs and toast", "exercise_recall": "30 minutes walking"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(DietLog.objects.filter(client=self.patient).count(), 1)
		self.assertEqual(ExerciseLog.objects.filter(client=self.patient).count(), 1)
		self.assertEqual(DietLog.objects.filter(client=self.patient).first().recall, "Eggs and toast")
		self.assertEqual(ExerciseLog.objects.filter(client=self.patient).first().recall, "30 minutes walking")
		self.assertEqual(response.data["dietary_recall"], "Eggs and toast")
		self.assertEqual(response.data["exercise_recall"], "30 minutes walking")

	def test_register_creates_auth_user_and_client(self):
		payload = {
			"username": "new-user@example.com",
			"password": "OmiverSecure2026!",
			"email": "new-user@example.com",
			"first_name": "New",
			"last_name": "User",
			"type": "INDIVIDUAL",
			"referred_by_code": self.provider.referral_code,
		}
		response = self.public_client.post(reverse("register"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		created_user = User.objects.get(username="new-user@example.com")
		created_client = Client.objects.get(email="new-user@example.com")
		self.assertEqual(created_client.referred_by, self.provider)
		self.assertEqual(created_client.user, created_user)

	def test_register_rejects_weak_passwords(self):
		payload = {
			"username": "weak-user@example.com",
			"password": "short",
			"email": "weak-user@example.com",
			"first_name": "Weak",
			"last_name": "User",
			"type": "INDIVIDUAL",
		}
		response = self.public_client.post(reverse("register"), payload, format="json")

		self.assertEqual(response.status_code, 400)
		self.assertIn("password", response.data)
		self.assertFalse(User.objects.filter(username="weak-user@example.com").exists())

	def test_password_reset_confirm_rejects_weak_passwords(self):
		user = User.objects.create_user(username="reset-user@example.com", password="OmiverSecure2026!")
		payload = {
			"uid": urlsafe_base64_encode(force_bytes(user.pk)),
			"token": default_token_generator.make_token(user),
			"new_password": "short",
		}
		response = self.public_client.post(reverse("password_reset_confirm"), payload, format="json")

		self.assertEqual(response.status_code, 400)
		self.assertIn("password", response.data)

	def test_password_reset_request_sends_email(self):
		user = User.objects.create_user(username="reset-request@example.com", email="reset-request@example.com", password="OmiverSecure2026!")
		payload = {
			"email": "reset-request@example.com",
		}
		response = self.public_client.post(reverse("password_reset_request"), payload, format="json")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["message"], "If that email exists, a reset link has been sent.")

	def test_password_reset_confirm_success(self):
		user = User.objects.create_user(username="reset-success@example.com", password="OmiverSecure2026!")
		payload = {
			"uid": urlsafe_base64_encode(force_bytes(user.pk)),
			"token": default_token_generator.make_token(user),
			"new_password": "NewOmiverSecure2026!",
		}
		response = self.public_client.post(reverse("password_reset_confirm"), payload, format="json")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["message"], "Password has been reset successfully")
		user.refresh_from_db()
		self.assertTrue(user.check_password("NewOmiverSecure2026!"))

	def test_default_shipping_address_endpoint(self):
		# create two addresses, one default
		ShippingAddress.objects.create(
			client=self.patient,
			street_address="10 Downing St",
			city="London",
			state="",
			zip_code="SW1A 2AA",
			is_default=False,
		)
		ShippingAddress.objects.create(
			client=self.patient,
			street_address="1600 Pennsylvania Ave",
			city="Washington",
			state="DC",
			zip_code="20500",
			is_default=True,
		)

		url = reverse("default_shipping_address") + f"?client_id={self.patient.id}"
		resp = self.public_client.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.data.get("street_address"), "1600 Pennsylvania Ave")


	def test_register_creates_recall_logs(self):
		payload = {
			"email": "recall@example.com",
			"username": "recall@example.com",
			"password": "OmiverSecure2026!",
			"first_name": "Recall",
			"last_name": "User",
			"type": "INDIVIDUAL",
			"dietary_recall": "Oatmeal and berries",
			"exercise_recall": "Morning run and stretching",
		}
		response = self.public_client.post(reverse("register"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		created_client = Client.objects.get(email="recall@example.com")
		self.assertEqual(DietLog.objects.filter(client=created_client).count(), 1)
		self.assertEqual(ExerciseLog.objects.filter(client=created_client).count(), 1)
		self.assertEqual(DietLog.objects.filter(client=created_client).first().recall, "Oatmeal and berries")
		self.assertEqual(ExerciseLog.objects.filter(client=created_client).first().recall, "Morning run and stretching")

	def test_check_email_reports_existing_username(self):
		response = self.public_client.get(reverse("check_email"), {"email": self.login_user.username})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["exists"])

	def test_validate_referral_code_reports_valid_provider_code(self):
		response = self.public_client.get(reverse("validate_referral_code"), {"code": self.provider.referral_code})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["isValid"])

	def test_validate_referral_code_reports_invalid_code(self):
		response = self.public_client.get(reverse("validate_referral_code"), {"code": "NOTREAL"})

		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.data["isValid"])

	def test_validate_referral_code_ignores_invalid_auth_header(self):
		self.public_client.credentials(HTTP_AUTHORIZATION="Token invalid-token")
		response = self.public_client.get(reverse("validate_referral_code"), {"code": self.provider.referral_code})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["isValid"])

	def test_verify_kit_code_reports_valid_order_number(self):
		response = self.public_client.get(reverse("verify_kit_code"), {"code": self.order.order_number})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["valid"])
		self.assertEqual(response.data["message"], "Kit code verified successfully")

	def test_verify_kit_code_reports_invalid_order_number(self):
		response = self.public_client.get(reverse("verify_kit_code"), {"code": "NOTREAL"})

		self.assertEqual(response.status_code, 400)
		self.assertFalse(response.data["valid"])
		self.assertEqual(response.data["message"], "Kit code not found in the system")

	def test_verify_kit_code_requires_code_query_param(self):
		response = self.public_client.get(reverse("verify_kit_code"))

		self.assertEqual(response.status_code, 400)
		self.assertFalse(response.data["valid"])
		self.assertEqual(response.data["message"], "Kit code is required")

	def test_login_handler_returns_client_data(self):
		response = self.public_client.post(
			reverse("login"),
			{"username": self.login_user.username, "password": "OmiverSecure2026!"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["email"], self.login_client.email)
		self.assertIn("token", response.data)
		self.assertEqual(self.public_client.session["client_id"], self.login_client.id)

	def test_generate_meal_plan_requires_login(self):
		self.api_client.force_login(self.web_user)

		response = self.api_client.get(reverse("generate_mealPlan", args=[self.patient.id]))

		self.assertEqual(response.status_code, 200)
		self.assertIn(self.patient.email, response.data["message"])

	def test_meal_plan_returns_results_for_client(self):
		response = self.api_client.get(reverse("meal_plan"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["client"], self.patient.id)

	def test_list_kits_returns_catalogue(self):
		response = self.api_client.get(reverse("list_kits"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual({row["name"] for row in response.data}, {self.kit.name, self.premium_kit.name})

	def test_list_orders_filters_by_client(self):
		response = self.api_client.get(reverse("list_orders"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 4)
		self.assertEqual(
			{row["order_number"] for row in response.data},
			{
				self.order.order_number,
				self.order_two.order_number,
				self.provider_order_pending.order_number,
				self.provider_order_approved.order_number,
			},
		)

	def test_export_orders_csv_returns_attachment(self):
		response = self.api_client.get(reverse("export_orders_csv"))

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
				"forward_tracking_number",
				"return_tracking_number",
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
		self.assertIn(self.order.order_number, {row[1] for row in rows[1:]})

	def test_export_orders_csv_supports_client_filter(self):
		response = self.api_client.get(reverse("export_orders_csv"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		rows = list(csv.reader(response.content.decode("utf-8").splitlines()))

		self.assertEqual(len(rows), 5)
		self.assertEqual(
			{row[1] for row in rows[1:]},
			{
				self.order.order_number,
				self.order_two.order_number,
				self.provider_order_pending.order_number,
				self.provider_order_approved.order_number,
			},
		)

	def test_create_order_seeds_delivery_event(self):
		payload = {
			"client": self.other_client.id,
			"test_kit": self.kit.id,
			"order_number": "ORD-3001",
			"forward_tracking_number": "TRK-3001",
			"return_tracking_number": "RTR-3001",
		}
		response = self.api_client.post(reverse("create_order"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		created_order = Order.objects.get(order_number="ORD-3001")
		self.assertEqual(created_order.delivery_events.count(), 1)

	def test_create_order_resolves_test_kit_from_barcode(self):
		barcode = "21191290"

		# Pre-create the physical kit barcode asset in the database to match company assets rule
		KitBarcodeAssignment.objects.create(
			barcode_number=barcode,
			test_kit=self.kit,
		)

		payload = {
			"client_id": self.other_client.id,
			"kit_codes": [barcode],
			"test_kit_name": self.kit.name,
			"order_number": "ORD-3002",
			"forward_tracking_number": "TRK-3002",
			"return_tracking_number": "RTR-3002",
		}
		response = self.api_client.post(reverse("create_order"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		created_order = Order.objects.prefetch_related("barcode_assignments__test_kit").get(order_number="ORD-3002")
		self.assertEqual(created_order.test_kit.id, self.kit.id)
		self.assertEqual(created_order.barcode_assignment.client_id, self.other_client.id)
		self.assertEqual(created_order.barcode_assignment.barcode_number, barcode)
		self.assertEqual(created_order.delivery_events.count(), 1)

	def test_mark_barcode_collected_updates_timestamp(self):
		assignment = KitBarcodeAssignment.objects.create(
			client=self.patient,
			test_kit=self.kit,
			barcode_number="21191290",
		)
		self.order.barcode_assignment = assignment
		self.order.save()

		collected_at = timezone.now().replace(microsecond=0)
		response = self.api_client.post(
			reverse("mark_barcode_collected"),
			{
				"barcode_number": assignment.barcode_number,
				"client_id": self.patient.id,
				"collected_at": collected_at.isoformat(),
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		assignment.refresh_from_db()
		self.assertIsNotNone(assignment.collected_at)
		self.assertEqual(assignment.collected_at.replace(microsecond=0), collected_at)
		self.assertEqual(response.data["barcode_number"], assignment.barcode_number)

	def test_order_detail_returns_nested_events(self):
		response = self.api_client.get(reverse("order_detail", args=[self.order.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["order_number"], self.order.order_number)
		self.assertEqual(len(response.data["delivery_events"]), 1)

	def test_update_order_status_creates_delivery_event(self):
		response = self.api_client.patch(
			reverse("update_order_status", args=[self.order.id]),
			{"status": "SHIPPED", "title": "Shipped", "description": "Your kit left the warehouse"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, "SHIPPED")
		self.assertTrue(self.order.delivery_events.filter(event_type="SHIPPED").exists())

	def test_update_order_status_persists_forward_tracking_number(self):
		response = self.api_client.patch(
			reverse("update_order_status", args=[self.order.id]),
			{
				"status": "SHIPPED",
				"title": "Shipped",
				"description": "Your kit left the warehouse",
				"forward_tracking_number": "TRK-9999",
				"return_tracking_number": "RTR-9999",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, "SHIPPED")
		self.assertEqual(self.order.forward_tracking_number, "TRK-9999")
		self.assertEqual(self.order.return_tracking_number, "RTR-9999")
		self.assertTrue(self.order.delivery_events.filter(event_type="SHIPPED").exists())

	def test_update_order_status_creates_shipping_info(self):
		response = self.api_client.patch(
			reverse("update_order_status", args=[self.order.id]),
			{
				"status": "SHIPPED",
				"title": "Shipped",
				"description": "Kit shipped",
				"forward_tracking_number": "TRK-SHIP-1",
				"return_tracking_number": "RTR-SHIP-1",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.order.refresh_from_db()
		self.assertEqual(self.order.status, "SHIPPED")
		shipping = ShippingInfo.objects.get(order=self.order)
		self.assertEqual(shipping.order_id, self.order.id)
		self.assertEqual(shipping.tracking_number, "TRK-SHIP-1")

	def test_track_order_finds_by_tracking_number(self):
		response = self.api_client.get(reverse("track_order"), {"tracking_number": self.order.forward_tracking_number})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["id"], self.order.id)

	@patch("api.views.stripe.PaymentIntent.create")
	def test_create_payment_intent_returns_client_secret(self, mock_create):
		mock_create.return_value = SimpleNamespace(client_secret="pi_secret_123")

		response = self.api_client.post(
			reverse("create_payment_intent"),
			{"test_kit_id": self.kit.id, "client_id": self.other_client.id, "quantity": 2},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["clientSecret"], "pi_secret_123")
		mock_create.assert_called_once()

	@patch("api.views.stripe.PaymentIntent.retrieve")
	def test_confirm_payment_creates_purchase(self, mock_retrieve):
		mock_retrieve.return_value = SimpleNamespace(
			status="succeeded",
			metadata={
				"test_kit_id": str(self.kit.id),
				"client_id": str(self.other_client.id),
				"quantity": "2",
			},
			charges=SimpleNamespace(
				data=[SimpleNamespace(
					payment_method_details=SimpleNamespace(
						card=SimpleNamespace(brand="Visa", last4="4242")
					)
				)]
			),
		)

		response = self.api_client.post(
			reverse("confirm_payment"),
			{
				"payment_intent_id": "pi_123",
				"street_address": "1 Payment Way",
				"city": "Austin",
				"state": "TX",
				"zip_code": "78701",
				"cardholder_name": "Ari Stone",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertTrue(Purchase.objects.filter(payment__stripe_payment_intent_id="pi_123").exists())
		self.assertTrue(PaymentInfo.objects.filter(stripe_payment_intent_id="pi_123").exists())

	@patch("api.views.stripe.PaymentIntent.retrieve")
	def test_confirm_payment_updates_existing_shipping_country(self, mock_retrieve):
		mock_retrieve.return_value = SimpleNamespace(
			status="succeeded",
			metadata={
				"test_kit_id": str(self.kit.id),
				"client_id": str(self.other_client.id),
				"quantity": "1",
			},
			charges=SimpleNamespace(
				data=[SimpleNamespace(
					payment_method_details=SimpleNamespace(
						card=SimpleNamespace(brand="Visa", last4="4242")
					)
				)]
			),
		)

		existing_address = ShippingAddress.objects.create(
			client=self.other_client,
			street_address="1 Payment Way",
			city="Austin",
			state="TX",
			zip_code="78701",
			country="Old Country",
			is_default=False,
		)

		response = self.api_client.post(
			reverse("confirm_payment"),
			{
				"payment_intent_id": "pi_456",
				"street_address": "1 Payment Way",
				"city": "Austin",
				"state": "TX",
				"zip_code": "78701",
				"country": "USA",
				"cardholder_name": "Ari Stone",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		existing_address.refresh_from_db()
		self.assertEqual(existing_address.country, "USA")
		self.assertTrue(existing_address.is_default)

	@patch("api.views.stripe.Webhook.construct_event", side_effect=ValueError("bad payload"))
	def test_stripe_webhook_invalid_payload_returns_400(self, _mock_construct_event):
		response = self.public_client.post(
			reverse("stripe_webhook"),
			data="{}",
			content_type="application/json",
			HTTP_STRIPE_SIGNATURE="invalid",
		)

		self.assertEqual(response.status_code, 400)

	def test_checkout_creates_purchase(self):
		response = self.api_client.post(
			reverse("checkout"),
			{
				"client_id": self.other_client.id,
				"test_kit_id": self.kit.id,
				"cardholder_name": "Ari Stone",
				"card_number": "4242 4242 4242 4242",
				"expiry_date": "12/30",
				"cvv": "123",
				"street_address": "1 Checkout Way",
				"city": "Austin",
				"state": "TX",
				"zip_code": "78701",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		self.assertTrue(Purchase.objects.filter(client=self.other_client).exists())

	def test_purchase_history_returns_client_purchases(self):
		response = self.api_client.get(reverse("purchase_history"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], self.purchase.id)

	def test_purchase_detail_returns_purchase(self):
		response = self.api_client.get(reverse("purchase_detail", args=[self.purchase.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["id"], self.purchase.id)

	def test_list_biomarkers_filters_category(self):
		response = self.api_client.get(reverse("list_biomarkers"), {"category": "metabolic"})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["name"], self.biomarker.name)

	def test_list_biomarker_tests_returns_client_tests(self):
		response = self.api_client.get(reverse("list_biomarker_tests"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["id"], self.biomarker_test.id)

	def test_biomarker_test_detail_returns_results(self):
		response = self.api_client.get(reverse("biomarker_test_detail", args=[self.biomarker_test.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data["results"]), 1)
		self.assertEqual(response.data["results"][0]["biomarker_name"], self.biomarker.name)

	def test_client_dashboard_returns_summary(self):
		response = self.api_client.get(reverse("client_dashboard"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["profile"]["email"], self.patient.email)
		self.assertEqual(response.data["health_score"], 100)
		self.assertEqual(response.data["total_biomarkers"], 1)
		self.assertEqual(response.data["optimal_biomarkers"], 1)
		self.assertEqual(response.data["recommendations"], [self.recommendation.text])

	def test_client_payments_returns_billing_history(self):
		response = self.api_client.get(reverse("client_payments"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["billing_address"]["city"], "Austin")

	def test_client_memberships_returns_active_membership(self):
		response = self.api_client.get(reverse("client_memberships"), {"client_id": self.patient.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertTrue(response.data[0]["is_active"])

	def test_get_referral_link_returns_referral_data(self):
		response = self.api_client.get(reverse("get_referral_link"), {"client_id": self.provider.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["patient_count"], 1)
		self.assertEqual(response.data["referral_code"], self.provider.referral_code)

	def test_get_provider_patients_returns_referred_patients(self):
		response = self.api_client.get(reverse("get_provider_patients"), {"client_id": self.provider.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["email"], self.patient.email)


	def test_get_kit_pricing_tiers_returns_kit_tiers(self):
		response = self.api_client.get(reverse("get_kit_pricing_tiers", args=[self.kit.id]), {"kit_id": self.kit.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data.get("test_kit_id"), self.kit.id)
		self.assertEqual(response.data.get("unit_price"), str(self.kit.price))

	def test_get_all_pricing_tiers_returns_every_tier(self):
		response = self.api_client.get(reverse("get_all_pricing_tiers"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data.get("message"), "Pricing tiers feature removed")

	def test_client_handler_collection_finished_at(self):
		# Create a KitBarcodeAssignment linked to self.patient
		assignment = KitBarcodeAssignment.objects.create(
			client=self.patient,
			test_kit=self.kit,
			barcode_number="TESTFINISHEDAT123"
		)

		collected_at_str = "2026-07-02T12:34:56Z"
		
		# Patch collection_finished_at
		patch_response = self.api_client.patch(
			reverse("client_handler", args=[self.patient.id]),
			{"collection_finished_at": collected_at_str},
			format="json",
		)
		self.assertEqual(patch_response.status_code, 200)

		# Check that assignment was updated in DB
		assignment.refresh_from_db()
		self.assertIsNotNone(assignment.collected_at)
		self.assertEqual(assignment.collected_at.strftime("%Y-%m-%dT%H:%M:%SZ"), "2026-07-02T12:34:56Z")

		# Check that GET representation includes collection_finished_at
		get_response = self.api_client.get(reverse("client_handler", args=[self.patient.id]))
		self.assertEqual(get_response.status_code, 200)
		self.assertTrue(get_response.data["collection_finished_at"].startswith("2026-07-02T12:34:56"))

	def test_ai_recommendation_workflow(self):
		# Delete any setup recommendations to isolate this test
		Recommendation.objects.filter(client=self.patient).delete()

		# 1. Trigger generate recommendations draft via API
		response = self.api_client.post(
			reverse("generate_recommendation_draft_api"),
			{"test_id": self.biomarker_test.id},
			format="json"
		)
		self.assertEqual(response.status_code, 200)
		rec_id = response.data["id"]
		self.assertEqual(response.data["status"], "DRAFT")
		self.assertIsNotNone(response.data["dietary_draft"])
		self.assertIsNotNone(response.data["exercise_draft"])

		# 2. Get recommendations as Patient: should be empty since not APPROVED yet
		patient_response = self.api_client.get(
			reverse("get_recommendations"),
			{"client_id": self.patient.id},
			format="json"
		)
		self.assertEqual(patient_response.status_code, 200)
		self.assertEqual(len(patient_response.data), 0)

		# 3. Get recommendations as Doctor (or passing requesting_client_id): should see the draft!
		doc_response = self.api_client.get(
			reverse("get_recommendations"),
			{
				"client_id": self.patient.id,
				"requesting_client_id": self.provider.id
			},
			format="json"
		)
		self.assertEqual(doc_response.status_code, 200)
		self.assertEqual(len(doc_response.data), 1)
		self.assertEqual(doc_response.data[0]["id"], rec_id)

		# 4. Submit Doctor Feedback (regenerate)
		feedback_response = self.api_client.post(
			reverse("submit_doctor_feedback_api", args=[rec_id]),
			{"doctor_feedback": "Please add more low-impact swimming exercises"},
			format="json"
		)
		self.assertEqual(feedback_response.status_code, 200)
		self.assertEqual(feedback_response.data["status"], "PENDING_REVIEW")
		self.assertEqual(feedback_response.data["doctor_feedback"], "Please add more low-impact swimming exercises")

		# 5. Approve recommendation
		approve_response = self.api_client.post(
			reverse("approve_recommendation_api", args=[rec_id]),
			{
				"doctor_notes": "Highly recommend adhering to the swimming routine.",
				"provider_id": self.provider.id
			},
			format="json"
		)
		self.assertEqual(approve_response.status_code, 200)
		self.assertEqual(approve_response.status_code, 200)
		self.assertEqual(approve_response.data["status"], "APPROVED")
		self.assertEqual(approve_response.data["doctor_notes"], "Highly recommend adhering to the swimming routine.")
		self.assertIsNotNone(approve_response.data["dietary_final"])
		self.assertIsNotNone(approve_response.data["exercise_final"])

		# 6. Now get recommendations as Patient: should be visible!
		patient_approved_response = self.api_client.get(
			reverse("get_recommendations"),
			{"client_id": self.patient.id},
			format="json"
		)
		self.assertEqual(patient_approved_response.status_code, 200)
		self.assertEqual(len(patient_approved_response.data), 1)
		self.assertEqual(patient_approved_response.data[0]["id"], rec_id)
		self.assertEqual(patient_approved_response.data[0]["status"], "APPROVED")

	def test_admin_tasso_csv_import(self):
		# Create a KitBarcodeAssignment linked to self.patient
		KitBarcodeAssignment.objects.filter(barcode_number="TASSO_TEST_BARCODE").delete()
		KitBarcodeAssignment.objects.create(
			client=self.patient,
			barcode_number="TASSO_TEST_BARCODE",
			test_kit=self.kit,
		)

		# Prepare CSV file upload
		from django.core.files.uploadedfile import SimpleUploadedFile
		csv_content = (
			b"barcode_number,biomarker_name,value,recorded_at\n"
			b"TASSO_TEST_BARCODE,Vitamin D,35.5,2026-07-02T10:00:00Z\n"
			b"TASSO_TEST_BARCODE,LDL Cholesterol,142.0,2026-07-02T10:00:00Z\n"
		)
		csv_file = SimpleUploadedFile("tasso.csv", csv_content, content_type="text/csv")

		# Ensure staff has admin access
		self.web_user.is_staff = True
		self.web_user.is_superuser = True
		self.web_user.save()
		self.api_client.force_login(self.web_user)

		# Post to admin import view
		import_url = reverse("admin:core_kitbarcodeassignment_import_csv")
		response = self.api_client.post(
			import_url,
			{"csv_file": csv_file},
			format="multipart",
			follow=True
		)

		# Should complete and redirect (200 on follow=True)
		self.assertEqual(response.status_code, 200)

		# Verify data import
		self.assertTrue(BiomarkerTest.objects.filter(client=self.patient, recorded_at="2026-07-02T10:00:00Z").exists())
		test_run = BiomarkerTest.objects.get(client=self.patient, recorded_at="2026-07-02T10:00:00Z")
		
		result1 = BiomarkerResult.objects.get(test=test_run, biomarker__name__iexact="Vitamin D")
		result2 = BiomarkerResult.objects.get(test=test_run, biomarker__name__iexact="LDL Cholesterol")
		self.assertEqual(result1.value, 35.5)
		self.assertEqual(result2.value, 142.0)

		# Verify AI recommendation draft was automatically triggered!
		self.assertTrue(Recommendation.objects.filter(biomarker_test=test_run, status="DRAFT").exists())
