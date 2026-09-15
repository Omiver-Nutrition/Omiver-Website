"""
Authorization / tenancy regression tests.

Every test in this module is a *replay of an exploit that actually worked*
against this codebase. They are written adversarially: each one performs the
attack and asserts it fails, rather than asserting that the happy path works.

Run with:
    ENCRYPTION_KEY=test-key .venv/bin/python manage.py test api.test_authz -v2

If one of these starts failing, a tenancy boundary has been reopened. Do not
"fix" the test — fix the view.
"""

from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.models import Client, Order, PaymentInfo, TestKit


# Throttling is enabled in production settings (anon 100/day). Several tests
# below loop over many endpoints, which would trip it and produce 429s that
# masquerade as passes. Disable throttling so a 403 means authorization.
NO_THROTTLE = override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.SessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        # Views that opt into a ScopedRateThrottle still look their scope up
        # here and raise ImproperlyConfigured if it is missing. A rate of None
        # means "declared, but unlimited".
        "DEFAULT_THROTTLE_RATES": {
            "anon": None,
            "user": None,
            "password_recovery": None,
            "complimentary_order": None,
        },
    }
)


# The checkout views now refuse to talk to Stripe unless STRIPE_SECRET_KEY is
# set (otherwise the SDK raises a confusing "No API key provided"). Tests that
# mock the Stripe SDK still have to clear that gate.
STRIPE_CONFIGURED = override_settings(STRIPE_SECRET_KEY="sk_test_dummy")


class AuthzTestBase(APITestCase):
    """Three tenants: a victim, an unrelated attacker, and a provider."""

    @classmethod
    def setUpTestData(cls):
        def make(username, email, ctype="INDIVIDUAL", **extra):
            user = User.objects.create_user(username=username, password="Sup3r!Secret!pw")
            client = Client.objects.create(user=user, email=email, type=ctype, **extra)
            token, _ = Token.objects.get_or_create(user=user)
            return user, client, token.key

        cls.victim_user, cls.victim, cls.victim_token = make(
            "victim", "victim@example.com",
            first_name="Vic", last_name="Tim", health_conditions="HIV positive",
        )
        cls.attacker_user, cls.attacker, cls.attacker_token = make(
            "attacker", "attacker@example.com",
        )
        cls.provider_user, cls.provider, cls.provider_token = make(
            "provider", "provider@example.com", ctype="PROVIDER",
        )
        cls.other_provider_user, cls.other_provider, cls.other_provider_token = make(
            "provider2", "provider2@example.com", ctype="PROVIDER",
        )

        # The victim is a patient of `provider`, not of `other_provider`.
        cls.victim.referred_by = cls.provider
        cls.victim.save()

        cls.kit = TestKit.objects.create(name="Panel", price="199.00")

    def setUp(self):
        cache.clear()

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def anon(self):
        self.client.credentials()


@NO_THROTTLE
@STRIPE_CONFIGURED
class FreeOrderBypassTests(AuthzTestBase):
    """P0-1: `payment_intent_id == "free_order"` skipped all Stripe verification."""

    def test_free_order_sentinel_creates_no_order(self):
        self.auth(self.attacker_token)
        # Real Stripe raises on a non-existent intent id; emulate that faithfully
        # so we are testing our control flow, not a mock that is too forgiving.
        with mock.patch(
            "api.views.stripe.PaymentIntent.retrieve",
            side_effect=Exception("No such payment_intent: 'free_order'"),
        ):
            resp = self.client.post(
                "/api/confirm-payment",
                {
                    "payment_intent_id": "free_order",
                    "test_kit_id": self.kit.id,
                    "quantity": 100,
                    "street_address": "1 St", "city": "X", "state": "CA", "zip_code": "90001",
                },
                format="json",
            )
        self.assertGreaterEqual(resp.status_code, 400, "free_order must not be accepted")
        self.assertEqual(Order.objects.count(), 0, "no Order may be created without payment")
        self.assertEqual(PaymentInfo.objects.count(), 0, "no PaymentInfo may be created")

    def test_sentinel_string_is_absent_from_source(self):
        """Belt and braces: the literal must not reappear via a future merge."""
        from pathlib import Path
        src = Path(__file__).resolve().parent / "views.py"
        self.assertNotIn("free_order", src.read_text(), "payment bypass sentinel reintroduced")


@NO_THROTTLE
class ComplimentaryOrderTests(AuthzTestBase):
    """The $0 checkout must never become a way to get a paid kit for nothing."""

    ADDRESS = {"street_address": "1 St", "city": "X", "state": "CA", "zip_code": "90001"}

    def setUp(self):
        super().setUp()
        self.free_kit = TestKit.objects.create(name="Beta Test", price="0.00")

    def post(self, **extra):
        return self.client.post("/api/complimentary-order", {**self.ADDRESS, **extra}, format="json")

    def test_paid_kit_cannot_be_claimed_for_free(self):
        """The server prices the kit; `self.kit` costs $199."""
        self.auth(self.attacker_token)
        resp = self.post(test_kit_id=self.kit.id)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(PaymentInfo.objects.count(), 0)

    def test_body_supplied_price_fields_are_ignored(self):
        """A caller must not be able to talk a paid kit down to zero."""
        self.auth(self.attacker_token)
        resp = self.post(test_kit_id=self.kit.id, price=0, amount=0, total_price="0.00")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_anonymous_cannot_claim(self):
        self.anon()
        resp = self.post(test_kit_id=self.free_kit.id)
        self.assertIn(resp.status_code, (401, 403))
        self.assertEqual(Order.objects.count(), 0)

    def test_order_is_attributed_to_session_not_body(self):
        self.auth(self.attacker_token)
        resp = self.post(test_kit_id=self.free_kit.id, client_id=self.victim.id)
        self.assertEqual(resp.status_code, 201, resp.data)
        order = Order.objects.get()
        self.assertEqual(order.client_id, self.attacker.id, "order attributed to the wrong client")

    def test_kit_can_only_be_claimed_once(self):
        self.auth(self.attacker_token)
        self.assertEqual(self.post(test_kit_id=self.free_kit.id).status_code, 201)
        second = self.post(test_kit_id=self.free_kit.id)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(Order.objects.count(), 1, "free kit farmed by repeat claims")

    def test_quantity_is_capped(self):
        self.auth(self.attacker_token)
        resp = self.post(test_kit_id=self.free_kit.id, quantity=500)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_free_claim_records_no_stripe_payment(self):
        self.auth(self.attacker_token)
        self.assertEqual(self.post(test_kit_id=self.free_kit.id).status_code, 201)
        payment = PaymentInfo.objects.get()
        self.assertIsNone(payment.stripe_payment_intent_id)
        self.assertEqual(payment.amount, 0)


@NO_THROTTLE
@STRIPE_CONFIGURED
class PaymentIntentOwnershipTests(AuthzTestBase):
    """A leaked/guessed intent id must not be redeemable by another account."""

    def _succeeded_intent(self, client_id, amount=19900):
        intent = mock.MagicMock()
        intent.status = "succeeded"
        intent.amount = amount
        intent.amount_received = amount
        intent.charges = None
        intent.latest_charge = None
        intent.metadata = {
            "test_kit_id": str(self.kit.id),
            "client_id": str(client_id),
            "quantity": "1",
        }
        return intent

    def test_attacker_cannot_redeem_victims_payment_intent(self):
        self.auth(self.attacker_token)
        with mock.patch(
            "api.views.stripe.PaymentIntent.retrieve",
            return_value=self._succeeded_intent(self.victim.id),
        ):
            resp = self.client.post(
                "/api/confirm-payment",
                {
                    "payment_intent_id": "pi_victim_123",
                    "street_address": "1 St", "city": "X", "state": "CA", "zip_code": "90001",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Order.objects.count(), 0)

    def test_intent_metadata_client_id_ignores_request_body(self):
        """create_payment_intent must stamp the *session* client, not the body."""
        self.auth(self.attacker_token)
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            obj = mock.MagicMock()
            obj.client_secret = "cs_test"
            obj.id = "pi_test"
            return obj

        with mock.patch("api.views.stripe.PaymentIntent.create", side_effect=fake_create):
            self.client.post(
                "/api/create-payment-intent",
                {"test_kit_id": self.kit.id, "quantity": 1, "client_id": self.victim.id},
                format="json",
            )

        self.assertIn("metadata", captured, "create_payment_intent did not reach Stripe")
        self.assertEqual(
            str(captured["metadata"]["client_id"]), str(self.attacker.id),
            "client_id was taken from the request body instead of the session",
        )


@NO_THROTTLE
class ProviderPatientDisclosureTests(AuthzTestBase):
    """P0-2: get_provider_patients never referenced request.user."""

    def test_individual_cannot_enumerate_provider_rosters(self):
        self.auth(self.attacker_token)
        resp = self.client.get(f"/api/provider/patients?client_id={self.provider.id}")
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("HIV", resp.content.decode())

    def test_anonymous_cannot_read_rosters(self):
        self.anon()
        resp = self.client.get(f"/api/provider/patients?client_id={self.provider.id}")
        self.assertIn(resp.status_code, (401, 403))

    def test_provider_sees_only_own_patients(self):
        self.auth(self.other_provider_token)
        resp = self.client.get(f"/api/provider/patients?client_id={self.provider.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [], "provider2 must not see provider1's roster")

    def test_provider_does_see_own_patients(self):
        """Negative tests are worthless if the feature is simply broken."""
        self.auth(self.provider_token)
        resp = self.client.get("/api/provider/patients")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


@NO_THROTTLE
class PrivilegeEscalationTests(AuthzTestBase):
    """P0-3: `type` was writable, so anyone could self-promote to PROVIDER."""

    def test_cannot_self_promote_to_provider(self):
        self.auth(self.attacker_token)
        resp = self.client.patch(
            f"/api/client/{self.attacker.id}", {"type": "PROVIDER"}, format="json",
        )
        self.attacker.refresh_from_db()
        self.assertEqual(
            self.attacker.type, "INDIVIDUAL",
            f"privilege escalation succeeded (HTTP {resp.status_code})",
        )

    def test_cannot_reassign_own_referred_by(self):
        """Claiming a provider as your referrer would leak you into their roster."""
        self.auth(self.attacker_token)
        self.client.patch(
            f"/api/client/{self.attacker.id}",
            {"referred_by": self.provider.id},
            format="json",
        )
        self.attacker.refresh_from_db()
        self.auth(self.provider_token)
        roster = self.client.get("/api/provider/patients").json()
        self.assertEqual(len(roster), 1, "attacker inserted themselves into a provider roster")


@NO_THROTTLE
class CrossTenantReadTests(AuthzTestBase):
    """require_self_or_provider must 404 (not 403) for non-owners."""

    def test_attacker_cannot_read_victim_client_record(self):
        self.auth(self.attacker_token)
        resp = self.client.get(f"/api/client/{self.victim.id}")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn("HIV", resp.content.decode())

    def test_owner_can_read_own_record(self):
        self.auth(self.victim_token)
        resp = self.client.get(f"/api/client/{self.victim.id}")
        self.assertEqual(resp.status_code, 200)

    def test_referring_provider_can_read_patient(self):
        self.auth(self.provider_token)
        resp = self.client.get(f"/api/client/{self.victim.id}")
        self.assertEqual(resp.status_code, 200)

    def test_unrelated_provider_cannot_read_patient(self):
        self.auth(self.other_provider_token)
        resp = self.client.get(f"/api/client/{self.victim.id}")
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_and_forbidden_are_indistinguishable(self):
        """Anti-enumeration: a real-but-forbidden id must look like a missing one."""
        self.auth(self.attacker_token)
        forbidden = self.client.get(f"/api/client/{self.victim.id}")
        missing = self.client.get("/api/client/99999")
        self.assertEqual(forbidden.status_code, missing.status_code)


@NO_THROTTLE
class OrderExportTests(AuthzTestBase):
    """Omitting client_id used to dump every order in the system."""

    def test_export_requires_client_id(self):
        self.auth(self.attacker_token)
        resp = self.client.get("/api/orders/export/csv")
        self.assertEqual(resp.status_code, 400)

    def test_export_rejects_foreign_client_id(self):
        self.auth(self.attacker_token)
        resp = self.client.get(f"/api/orders/export/csv?client_id={self.victim.id}")
        self.assertEqual(resp.status_code, 404)


@NO_THROTTLE
class AnonymousAccessTests(AuthzTestBase):
    """P0-4: ~30 PHI views were AllowAny + authentication_classes([])."""

    PHI_GET_ENDPOINTS = [
        "/api/dashboard",
        "/api/orders",
        "/api/recommendations",
        "/api/biomarker-tests",
        "/api/biomarker-reports",
        "/api/payments",
        "/api/memberships",
        "/api/purchases",
        "/api/collection/progress",
        "/api/shipping-addresses",
        "/api/provider/patients",
        "/api/provider/referral-link",
    ]

    def test_all_phi_endpoints_reject_anonymous(self):
        self.anon()
        leaked = []
        for url in self.PHI_GET_ENDPOINTS:
            resp = self.client.get(url)
            if resp.status_code not in (401, 403, 404):
                leaked.append(f"{url} -> {resp.status_code}")
        self.assertEqual(leaked, [], f"endpoints reachable anonymously: {leaked}")

    def test_public_endpoints_are_still_public(self):
        """Guard against over-correcting and breaking signup/login."""
        self.anon()
        for url in ["/api/kits", "/api/check_email?email=nobody@example.com"]:
            resp = self.client.get(url)
            self.assertNotIn(resp.status_code, (401, 403), f"{url} became unreachable")


@NO_THROTTLE
class TokenLifecycleTests(AuthzTestBase):
    """verify_token used to return only {valid: true}, so the SPA trusted
    localStorage for identity. Logout used to leave the token row alive."""

    def test_verify_token_returns_identity_not_just_a_boolean(self):
        self.auth(self.victim_token)
        resp = self.client.get("/api/verify-token")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(str(body.get("client_id")), str(self.victim.id))
        self.assertEqual(body.get("type"), "INDIVIDUAL")

    def test_logout_invalidates_the_token(self):
        self.auth(self.victim_token)
        self.client.post("/api/logout", {}, format="json")
        self.assertFalse(
            Token.objects.filter(key=self.victim_token).exists(),
            "token row survived logout; the bearer token is still valid",
        )
        resp = self.client.get(f"/api/client/{self.victim.id}")
        self.assertIn(resp.status_code, (401, 403, 404))


@NO_THROTTLE
class CallerSuppliedClientIdTests(AuthzTestBase):
    """Horizontal privilege escalation via a client_id parameter.

    These endpoints required authentication but not *authorization*: they
    filtered directly on a client_id taken from the query string or request
    body. Any logged-in user could therefore read another patient's records, or
    drive their kit-collection workflow, just by changing the number.
    """

    READ_ENDPOINTS = [
        "/api/mealPlan",
        "/api/orders",
        "/api/purchases",
        "/api/biomarker-tests",
        "/api/biomarker-reports",
        "/api/payments",
        "/api/collection/progress",
    ]

    WRITE_ENDPOINTS = [
        "/api/collection/step1-link",
        "/api/collection/step2-collect",
        "/api/collection/step2-pouch",
        "/api/collection/step3-prepare",
        "/api/collection/step4-ship",
    ]

    def test_reads_reject_another_clients_id(self):
        self.auth(self.attacker_token)
        leaked = []
        for url in self.READ_ENDPOINTS:
            resp = self.client.get(url, {"client_id": self.victim.id})
            if resp.status_code not in (403, 404):
                leaked.append(f"{url} -> {resp.status_code}")
        self.assertEqual(leaked, [], f"readable with someone else's client_id: {leaked}")

    def test_writes_reject_another_clients_id(self):
        self.auth(self.attacker_token)
        leaked = []
        for url in self.WRITE_ENDPOINTS:
            resp = self.client.post(
                url,
                {
                    "client_id": self.victim.id,
                    "barcode_number": "ATTACKER-1",
                    "order_id": 1,
                },
                format="json",
            )
            if resp.status_code not in (403, 404):
                leaked.append(f"{url} -> {resp.status_code}")
        self.assertEqual(leaked, [], f"writable with someone else's client_id: {leaked}")

    def test_owner_is_still_allowed(self):
        """The gate must not break the legitimate owner's own access."""
        self.auth(self.victim_token)
        blocked = []
        for url in self.READ_ENDPOINTS:
            resp = self.client.get(url, {"client_id": self.victim.id})
            if resp.status_code in (403, 404):
                blocked.append(f"{url} -> {resp.status_code}")
        self.assertEqual(blocked, [], f"owner locked out of their own data: {blocked}")

    def test_referring_provider_is_still_allowed(self):
        self.auth(self.provider_token)
        blocked = []
        for url in self.READ_ENDPOINTS:
            resp = self.client.get(url, {"client_id": self.victim.id})
            if resp.status_code in (403, 404):
                blocked.append(f"{url} -> {resp.status_code}")
        self.assertEqual(blocked, [], f"referring provider blocked from patient: {blocked}")


@NO_THROTTLE
class EncryptionConfigTests(AuthzTestBase):
    """The hardcoded "default-secret-key-123456" fallback must stay gone."""

    def test_no_hardcoded_encryption_fallback(self):
        from pathlib import Path
        src = Path(__file__).resolve().parent.parent / "core" / "encryption.py"
        text = src.read_text()
        self.assertNotIn("default-secret-key", text)
        self.assertIn("ImproperlyConfigured", text)


@NO_THROTTLE
class RegistrationIntegrityTests(AuthzTestBase):
    """Regression guard.

    Locking down `type` and `user` by marking them read_only made DRF *silently
    drop* them, so registration produced Clients with user=None. Such an account
    cannot log in and resolve_client() returns None for it, which locks the user
    out of every endpoint. Hardening must not cost us the ability to create
    accounts at all, so assert the full signup -> login -> identity round trip.
    """

    PW = "Str0ng!Passphrase!2026"

    def _register(self, email, ctype="INDIVIDUAL"):
        self.anon()
        return self.client.post(
            "/api/register",
            {
                "username": email, "password": self.PW, "email": email,
                "first_name": "New", "last_name": "User", "type": ctype,
            },
            format="json",
        )

    def test_registration_links_client_to_auth_user(self):
        resp = self._register("brand-new@example.com")
        self.assertEqual(resp.status_code, 201, resp.content)
        client = Client.objects.get(email="brand-new@example.com")
        self.assertIsNotNone(
            client.user,
            "Client was created orphaned (user=None); this account can never log in",
        )
        self.assertEqual(client.user.username, "brand-new@example.com")

    def test_registered_user_can_log_in_and_is_recognised(self):
        """The end-to-end proof that the account is actually usable."""
        self._register("usable@example.com")
        self.anon()
        login = self.client.post(
            "/api/login",
            {"username": "usable@example.com", "password": self.PW},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.content)
        token = login.json().get("token")
        self.assertTrue(token, "login did not return a token")

        self.auth(token)
        me = self.client.get("/api/verify-token")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(
            str(me.json().get("client_id")),
            str(Client.objects.get(email="usable@example.com").id),
        )

    def test_provider_registration_still_creates_a_provider(self):
        resp = self._register("newdoc@example.com", ctype="PROVIDER")
        self.assertEqual(resp.status_code, 201, resp.content)
        client = Client.objects.get(email="newdoc@example.com")
        self.assertEqual(client.type, "PROVIDER", "PROVIDER signup silently downgraded")
        self.assertTrue(client.referral_code, "provider got no referral code")

    def test_freshly_registered_user_still_cannot_escalate(self):
        """Creation must stay open without reopening the PATCH escalation."""
        self._register("climber@example.com")
        login = self.client.post(
            "/api/login",
            {"username": "climber@example.com", "password": self.PW},
            format="json",
        )
        self.auth(login.json()["token"])
        client_id = login.json()["id"]
        self.client.patch(f"/api/client/{client_id}", {"type": "PROVIDER"}, format="json")
        self.assertEqual(
            Client.objects.get(id=client_id).type, "INDIVIDUAL",
            "escalation reopened while fixing registration",
        )

    def test_registration_cannot_hijack_an_existing_auth_user(self):
        """`user` is writable at create time — ensure that is not abusable."""
        self.anon()
        self.client.post(
            "/api/register",
            {
                "username": "hijacker@example.com", "password": self.PW,
                "email": "hijacker@example.com", "first_name": "H", "last_name": "J",
                "user": self.victim_user.id,
            },
            format="json",
        )
        self.victim.refresh_from_db()
        self.assertEqual(
            self.victim.user_id, self.victim_user.id,
            "an existing client's identity link was reassigned by a registration",
        )

