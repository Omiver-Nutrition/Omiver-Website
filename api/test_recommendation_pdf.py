from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from core.models import (
    Client, Biomarker, BiomarkerTest, BiomarkerResult, Recommendation, BiomarkerReport
)


class RecommendationPdfTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()

        # These PDFs contain PHI and are now gated on the owning client, so the
        # test must authenticate as the patient the documents belong to.
        self.user = User.objects.create_user(
            username="patient@example.com",
            password="OmiverSecure2026!",
        )
        self.patient = Client.objects.create(
            user=self.user,
            email="patient@example.com",
            first_name="Jane",
            last_name="Doe",
            gender="Female",
            height=168.0,
            weight=62.0,
            fitness_goal="Cardiovascular Endurance",
            nutritional_goal="Anti-inflammatory diet",
            health_conditions="Mild asthma",
            dietary_preferences="Mediterranean",
        )
        self.client_api.force_authenticate(user=self.user)

        self.provider = Client.objects.create(
            email="doctor@example.com",
            first_name="Marcus",
            last_name="Welby",
            type="PROVIDER",
        )

        self.bm1 = Biomarker.objects.create(
            name="hs-CRP",
            category="INFLAMMATION",
            range_min=0.0,
            range_max=3.0,
            optimal_min=0.0,
            optimal_max=1.0,
            unit="mg/L"
        )

        self.test_run = BiomarkerTest.objects.create(
            client=self.patient,
            recorded_at=timezone.now()
        )

        self.bm_res = BiomarkerResult.objects.create(
            test=self.test_run,
            biomarker=self.bm1,
            value=0.6,
            status="OPTIMAL"
        )

        self.recommendation = Recommendation.objects.create(
            client=self.patient,
            biomarker_test=self.test_run,
            text="Personalized Mediterranean anti-inflammatory protocol.",
            dietary_draft={
                "summary": "Focus on omega-3 fatty acids and polyphenols.",
                "dos": ["Extra virgin olive oil", "Wild salmon", "Blueberries"],
                "donts": ["Refined carbohydrates", "Seed oils"],
                "sample_meal_plan": [
                    {"meal": "Breakfast", "suggestion": "Overnight chia pudding with berries"},
                    {"meal": "Lunch", "suggestion": "Grilled salmon over wild arugula and quinoa"},
                    {"meal": "Dinner", "suggestion": "Baked chicken breast with roasted vegetables"}
                ]
            },
            exercise_draft={
                "summary": "Zone 2 aerobic base conditioning.",
                "frequency": "4 sessions per week",
                "activities": ["30-min cycling", "Brisk incline walk"],
                "precautions": ["Stay hydrated", "Gradual warm-up"]
            },
            doctor_notes="Keep up the great aerobic consistency.",
            status="APPROVED",
            approved_by=self.provider,
            approved_at=timezone.now()
        )

        self.report = BiomarkerReport.objects.create(
            client=self.patient,
            report="<h1>Delta Analysis</h1><p>Metabolic biomarkers improved over baseline.</p>",
            test_ids=[self.test_run.id]
        )

    def test_download_recommendation_pdf_success(self):
        """Test downloading approved recommendation PDF."""
        url = f"/api/recommendations/{self.recommendation.id}/pdf"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(f"omiver-recommendation-{self.recommendation.id}.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertTrue(response.content.endswith(b"%%EOF\n"))

    def test_download_recommendation_pdf_inline(self):
        """Test downloading with inline preview parameter."""
        url = f"/api/recommendations/{self.recommendation.id}/pdf?inline=true"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("inline;", response["Content-Disposition"])

    def test_download_recommendation_pdf_not_found(self):
        """Test 404 for invalid recommendation ID."""
        url = "/api/recommendations/99999/pdf"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_biomarker_report_pdf_success(self):
        """Test downloading biomarker report PDF."""
        url = f"/api/biomarker-reports/{self.report.primary_id}/pdf"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-1.4"))
        self.assertTrue(response.content.endswith(b"%%EOF\n"))

    def test_download_biomarker_report_pdf_not_found(self):
        """Test 404 for non-existent report."""
        url = "/api/biomarker-reports/99999/pdf"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
