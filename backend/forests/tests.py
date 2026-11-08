from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from forests.models import BiomassHistory, Project, UserRole, VerificationReport


class AuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login(self):
        res = self.client.post(
            "/api/auth/register/",
            {"email": "test@example.com", "password": "secret123", "full_name": "Test User"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res = self.client.post(
            "/api/auth/login/",
            {"email": "test@example.com", "password": "secret123"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)


class ProjectAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="owner@test.com", email="owner@test.com", password="pass1234")
        self.other = User.objects.create_user(username="other@test.com", email="other@test.com", password="pass1234")
        UserRole.objects.get_or_create(user=self.user, role=UserRole.Role.USER)
        login = self.client.post("/api/auth/login/", {"email": "owner@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_create_and_list_projects(self):
        res = self.client.post(
            "/api/projects/",
            {"name": "Shivapuri", "latitude": 27.8, "longitude": 85.4, "area_hectares": 100},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Shivapuri")

        res = self.client.get("/api/projects/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_owner_cannot_see_other_projects(self):
        Project.objects.create(name="Private", latitude=1, longitude=1, owner=self.other)
        Project.objects.create(name="Mine", latitude=2, longitude=2, owner=self.user)

        res = self.client.get("/api/projects/")
        names = [p["name"] for p in res.data["results"]]
        self.assertEqual(names, ["Mine"])


class BiomassAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u@test.com", email="u@test.com", password="pass1234")
        self.project = Project.objects.create(name="Forest", latitude=27.5, longitude=85.3, owner=self.user)
        login = self.client.post("/api/auth/login/", {"email": "u@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_create_biomass_with_valid_health_score(self):
        res = self.client.post(
            "/api/biomass-history/",
            {"project_id": str(self.project.id), "carbon_density": 45.2, "health_score": 0.72},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BiomassHistory.objects.count(), 1)


class VerificationFeedTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="v@test.com", email="v@test.com", password="pass1234")
        self.project = Project.objects.create(name="Community Forest", latitude=27.5, longitude=85.3, owner=self.user)
        VerificationReport.objects.create(project=self.project, status=VerificationReport.Status.PENDING)
        login = self.client.post("/api/auth/login/", {"email": "v@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_feed_returns_project_name(self):
        res = self.client.get("/api/verification-reports/feed/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["project_name"], "Community Forest")


class MRVAnalyzeTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="mrv@test.com", email="mrv@test.com", password="pass1234")
        login = self.client.post("/api/auth/login/", {"email": "mrv@test.com", "password": "pass1234"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_analyze_returns_carbon_estimate(self):
        res = self.client.post(
            "/api/analyze/?sync=1",
            {
                "lat": 27.5,
                "lon": 85.3,
                "buf_km": 5,
                "year1": 2022,
                "year2": 2024,
                "start_month": 1,
                "end_month": 3,
                "forest_type": "tropical_moist",
                "run_multiyear": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data.get("result") or res.data
        self.assertIn("carbon_estimate", data)
        self.assertIn("trend_data", data)

    @patch("mrv.views.call_groq")
    def test_generate_report(self, mock_groq):
        mock_groq.return_value = ({"executive_summary": "Test summary", "confidence_level": "High"}, None)
        res = self.client.post(
            "/api/report/generate/",
            {"location": "Kathmandu", "change_pct": 2.5, "ndvi_year2": 0.65, "carbon_estimate": {"total_co2": 1000}},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("executive_summary", res.data)

    def test_export_pdf(self):
        res = self.client.post(
            "/api/export/pdf/",
            {"location": "Kathmandu", "report_data": {"executive_summary": "Test summary"}},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))
