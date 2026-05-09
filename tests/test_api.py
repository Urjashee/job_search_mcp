from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from job_search_mcp.api import app
from job_search_mcp.models import JobSource


class ApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_root_returns_html(self) -> None:
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "http://localhost:5173")

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_jobs_endpoint_returns_seeded_jobs(self) -> None:
        response = self.client.get("/jobs?page=1&page_size=3")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("items", payload)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 3)
        self.assertGreaterEqual(payload["total"], len(payload["items"]))
        self.assertGreaterEqual(payload["total_pages"], 1)
        self.assertLessEqual(len(payload["items"]), 3)

    def test_jobs_endpoint_paginates_second_page(self) -> None:
        response = self.client.get("/jobs?page=2&page_size=3")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 3)
        self.assertLessEqual(len(payload["items"]), 3)
        self.assertGreaterEqual(payload["total_pages"], 1)

    def test_search_endpoint_returns_paginated_results(self) -> None:
        response = self.client.post(
            "/jobs/search",
            json={"query": "engineer", "limit": 5, "page": 1, "page_size": 2},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 2)
        self.assertLessEqual(len(payload["items"]), 2)
        self.assertGreaterEqual(payload["total_pages"], 1)
        self.assertGreaterEqual(payload["total"], len(payload["items"]))

    def test_ingestion_sources_lists_adapters(self) -> None:
        response = self.client.get("/ingestion/sources")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("jsearch", payload["items"])
        self.assertIn("greenhouse", payload["items"])

    def test_ingest_demo_sources(self) -> None:
        response = self.client.post("/ingestion/all")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 3)

    def test_sync_status_endpoint(self) -> None:
        response = self.client.get("/ingestion/sync/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("enabled", payload)
        self.assertIn("interval_seconds", payload)

    def test_import_jobs_endpoint_validates_source(self) -> None:
        class DummyAdapter:
            def fetch(self):
                from job_search_mcp.services.sources import IngestedJob

                return [
                    IngestedJob(
                        title="Platform Engineer",
                        company="Example Company",
                        location="Remote",
                        description="Build internal platforms.",
                    )
                ]

        with patch("job_search_mcp.api.build_import_adapter", return_value=DummyAdapter()):
            response = self.client.post(
                "/ingestion/import",
                json={
                    "source": JobSource.greenhouse.value,
                    "reference": "example-company",
                    "company": "Example Company",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "greenhouse")
        self.assertEqual(payload["ingested"], 1)

    def test_resume_upload_parses_text_file(self) -> None:
        response = self.client.post(
            "/resumes/upload",
            files={
                "file": (
                    "resume.txt",
                    b"Python engineer with FastAPI, OpenAI, and RAG experience.",
                    "text/plain",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["filename"], "resume.txt")
        self.assertIn("python", payload["analysis"]["extracted_skills"])
        self.assertIn("fastapi", payload["analysis"]["extracted_skills"])

    def test_cover_letter_generation(self) -> None:
        response = self.client.post(
            "/tools/cover-letter",
            json={
                "resume_text": "Python FastAPI engineer with RAG experience.",
                "job_title": "AI Engineer",
                "company": "Northstar Labs",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Northstar Labs", payload["item"])
        self.assertIn("AI Engineer", payload["item"])


if __name__ == "__main__":
    unittest.main()
