from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Client, TestKit, Order, KitCollection, KitBarcodeAssignment


class CollectionStepsApiTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()

        # These endpoints now require authentication AND ownership of the
        # client_id in the payload, so act as the patient who owns the order.
        self.user = User.objects.create_user(
            username="samplepatient@example.com",
            password="OmiverSecure2026!",
        )
        self.patient = Client.objects.create(
            user=self.user,
            email="samplepatient@example.com",
            first_name="Alex",
            last_name="Rivers",
        )
        self.client_api.force_authenticate(user=self.user)

        self.test_kit = TestKit.objects.create(
            name="Metabolic Advanced Test",
            biomarker_count=150,
            price=299.00
        )

        self.order = Order.objects.create(
            client=self.patient,
            order_number="ORD-COLLECT-101",
            quantity=1,
        )

        self.assignment = KitBarcodeAssignment.objects.create(
            client=self.patient,
            order=self.order,
            test_kit=self.test_kit,
            barcode_number="TASSO-X101"
        )

    def test_step1_link_api(self):
        """Test step 1 link endpoint returns success and saves step_progress."""
        url = "/api/collection/step1-link"
        payload = {
            "client_id": self.patient.id,
            "barcode_number": "TASSO-X101",
            "order_id": self.order.id,
        }
        response = self.client_api.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["step"], 1)
        self.assertEqual(response.data["barcode"], "TASSO-X101")
        self.assertIn("Step 1 saved", response.data["message"])

        kc = KitCollection.objects.get(user=self.patient)
        self.assertTrue(kc.step_progress["step1"]["completed"])

    def test_step2_collect_api(self):
        """Test step 2 collect endpoint records timestamp and updates status."""
        url = "/api/collection/step2-collect"
        payload = {
            "client_id": self.patient.id,
            "barcode_number": "TASSO-X101",
            "order_id": self.order.id,
            "notes": "Left arm deltoid site used"
        }
        response = self.client_api.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["step"], 2)
        self.assertIn("Step 2 saved", response.data["message"])

        kc = KitCollection.objects.get(user=self.patient)
        self.assertEqual(kc.status, "COLLECTED")
        self.assertIsNotNone(kc.collected_at)

    def test_step3_prepare_api(self):
        """Test step 3 preparation endpoint."""
        url = "/api/collection/step3-prepare"
        payload = {
            "client_id": self.patient.id,
            "order_id": self.order.id,
        }
        response = self.client_api.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["step"], 3)

    def test_collection_progress_api(self):
        """Test retrieving full collection progress."""
        url = f"/api/collection/progress?client_id={self.patient.id}&order_id={self.order.id}"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("step_progress", response.data)
