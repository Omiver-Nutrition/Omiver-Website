from django.test import TestCase
from django.utils import timezone
from core.models import Client, BiomarkerTest, BiomarkerReport

class BiomarkerModelTests(TestCase):
    def setUp(self):
        # Create a client if we need one
        self.client_user = Client.objects.create(
            email="testclient@example.com",
            first_name="Test",
            last_name="User",
            type="CLIENT"
        )

    def test_biomarker_test_with_client(self):
        """Verify BiomarkerTest can be created with a valid client."""
        test_run = BiomarkerTest.objects.create(
            client=self.client_user,
            recorded_at=timezone.now()
        )
        self.assertEqual(test_run.client, self.client_user)
        self.assertIn(str(self.client_user), str(test_run))

    def test_biomarker_test_without_client_optional(self):
        """Verify client is optional on BiomarkerTest (null=True)."""
        test_run = BiomarkerTest.objects.create(
            client=None,
            recorded_at=timezone.now()
        )
        self.assertIsNone(test_run.client)
        self.assertIn("Unknown", str(test_run))

    def test_biomarker_report_creation(self):
        """Verify BiomarkerReport can be created with client and test_ids list."""
        test_run1 = BiomarkerTest.objects.create(
            client=self.client_user,
            recorded_at=timezone.now()
        )
        test_run2 = BiomarkerTest.objects.create(
            client=self.client_user,
            recorded_at=timezone.now()
        )

        report = BiomarkerReport.objects.create(
            client=self.client_user,
            report="Patient has excellent vitamin D levels, but cholesterol is slightly elevated.",
            test_ids=[test_run1.id, test_run2.id]
        )

        self.assertEqual(report.client, self.client_user)
        self.assertEqual(report.test_ids, [test_run1.id, test_run2.id])
        self.assertIn("excellent vitamin D", report.report)
        self.assertIn(f"Report {report.primary_id}", str(report))
