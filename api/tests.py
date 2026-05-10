import csv
from decimal import Decimal
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
	Biomarker,
	BiomarkerResult,
	BiomarkerTest,
	BillingAddress,
	Client,
	DietitianCommission,
	DeliveryEvent,
	Membership,
	MealPlan,
	Order,
	PaymentInfo,
	PricingTier,
	Purchase,
	Recommendation,
	TestKit,
)


class ApiSmokeTests(TestCase):
	def setUp(self):
		self.api_client = APIClient()

		self.web_user = User.objects.create_user(
			username="staff@example.com",
			password="secret123",
		)
		self.login_user = User.objects.create_user(
			username="login@example.com",
			password="secret123",
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
			commission_percent=Decimal("10.00"),
		)
		self.premium_kit = TestKit.objects.create(
			name="Premium Kit",
			biomarker_count=240,
			description="Premium",
			price=Decimal("149.00"),
			commission_percent=Decimal("12.50"),
		)

		self.tier = PricingTier.objects.create(
			test_kit=self.kit,
			min_quantity=2,
			max_quantity=4,
			discount_percent=Decimal("10.00"),
		)
		self.tier_high = PricingTier.objects.create(
			test_kit=self.kit,
			min_quantity=5,
			max_quantity=None,
			discount_percent=Decimal("20.00"),
		)
		self.other_tier = PricingTier.objects.create(
			test_kit=self.premium_kit,
			min_quantity=1,
			max_quantity=None,
			discount_percent=Decimal("5.00"),
		)

		self.order = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-1001",
			tracking_number="TRK-1001",
			status="PENDING",
			quantity=1,
		)
		self.order_two = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-1002",
			tracking_number="TRK-1002",
			status="CONFIRMED",
			quantity=2,
		)
		self.provider_order_pending = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-2001",
			tracking_number="TRK-2001",
			status="PENDING",
			quantity=1,
		)
		self.provider_order_approved = Order.objects.create(
			client=self.patient,
			test_kit=self.kit,
			order_number="ORD-2002",
			tracking_number="TRK-2002",
			status="PENDING",
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

		self.pending_commission = DietitianCommission.objects.create(
			provider=self.provider,
			order=self.provider_order_pending,
			kit_quantity=2,
			kit_price=self.kit.price,
			commission_percent=self.kit.commission_percent,
			status="PENDING",
		)
		self.approved_commission = DietitianCommission.objects.create(
			provider=self.provider,
			order=self.provider_order_approved,
			kit_quantity=1,
			kit_price=self.kit.price,
			commission_percent=self.kit.commission_percent,
			status="APPROVED",
		)

	def test_index_returns_welcome_message(self):
		response = self.public_client.get(reverse("index"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.content.decode("utf-8"), "Welcome to the API endpoint!")

	def test_protected_endpoint_requires_authentication(self):
		response = self.public_client.get(reverse("list_kits"))

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

	def test_register_creates_auth_user_and_client(self):
		payload = {
			"username": "new-user@example.com",
			"password": "secret123",
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

	def test_login_handler_returns_client_data(self):
		response = self.public_client.post(
			reverse("login"),
			{"username": self.login_user.username, "password": "secret123"},
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
			"tracking_number": "TRK-3001",
		}
		response = self.api_client.post(reverse("create_order"), payload, format="json")

		self.assertEqual(response.status_code, 201)
		created_order = Order.objects.get(order_number="ORD-3001")
		self.assertEqual(created_order.delivery_events.count(), 1)

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

	def test_track_order_finds_by_tracking_number(self):
		response = self.api_client.get(reverse("track_order"), {"tracking_number": self.order.tracking_number})

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

	def test_get_provider_commissions_returns_commissions(self):
		response = self.api_client.get(reverse("get_provider_commissions"), {"client_id": self.provider.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 2)

	def test_get_commission_summary_aggregates_statuses(self):
		response = self.api_client.get(reverse("get_commission_summary"), {"client_id": self.provider.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data["provider_id"], self.provider.id)
		self.assertEqual(response.data["commission_count"], 2)
		self.assertGreater(response.data["total_earned"], 0)

	def test_approve_commission_updates_status(self):
		response = self.api_client.patch(
			f"{reverse('approve_commission')}?commission_id={self.pending_commission.id}",
			{},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.pending_commission.refresh_from_db()
		self.assertEqual(self.pending_commission.status, "APPROVED")

	@patch("api.views.stripe.Transfer.create")
	def test_process_commission_payout_marks_commission_paid(self, mock_transfer_create):
		mock_transfer_create.return_value = SimpleNamespace(id="tr_123")

		response = self.api_client.post(
			reverse("process_commission_payout"),
			{"commission_id": self.approved_commission.id, "stripe_account_id": "acct_123"},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.approved_commission.refresh_from_db()
		self.assertEqual(self.approved_commission.status, "PAID")
		self.assertEqual(self.approved_commission.stripe_transfer_id, "tr_123")

	def test_get_kit_pricing_tiers_returns_kit_tiers(self):
		response = self.api_client.get(reverse("get_kit_pricing_tiers", args=[self.kit.id]), {"kit_id": self.kit.id})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 2)

	def test_get_all_pricing_tiers_returns_every_tier(self):
		response = self.api_client.get(reverse("get_all_pricing_tiers"))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data), 3)
