from __future__ import annotations

import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from job_search_mcp.cli import run_demo, run_info
from job_search_mcp.mcp_server import create_context, run_mcp_server
from job_search_mcp.models import JobCreateRequest, JobSearchRequest
from job_search_mcp.llm import CoverLetterGenerator
from job_search_mcp.settings import AppSettings
from job_search_mcp.services.jobs import JobRepository, analyze_resume_text, parse_resume_bytes
from job_search_mcp.services.ingestion import JobIngestionService
from job_search_mcp.services.mcp_tools import JobSearchTools


class JobRepositoryTests(unittest.TestCase):
    def test_seed_demo_jobs_and_search(self) -> None:
        repository = JobRepository()
        repository.seed_demo_jobs()

        results = repository.search(
            JobSearchRequest(query="remote AI engineer with RAG and FastAPI", limit=5)
        )

        self.assertGreaterEqual(len(results.items), 1)
        self.assertEqual(results.items[0].job.company, "Northstar Labs")
        self.assertGreater(results.items[0].score, 0)

    def test_search_deduplicates_repeated_postings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            settings = AppSettings(database_url=f"sqlite:///{db_path.as_posix()}")
            repository = JobRepository(settings=settings)

            duplicate_job = JobCreateRequest(
                title="Machine Learning Engineer",
                company="Acme AI",
                location="Remote",
                description="Build Python pipelines for model serving and retrieval systems.",
                remote=True,
                visa_sponsorship=False,
                tags=["python", "fastapi", "rag"],
            )

            repository.add_job(duplicate_job)
            repository.add_job(duplicate_job)
            repository.add_job(
                JobCreateRequest(
                    title="Backend Engineer",
                    company="Acme AI",
                    location="Remote",
                    description="Build job search APIs and internal tooling.",
                    remote=True,
                    visa_sponsorship=False,
                    tags=["python", "fastapi", "search"],
                )
            )

            results = repository.search(
                JobSearchRequest(query="Python FastAPI RAG engineer", limit=10)
            )

            duplicate_hits = [
                result
                for result in results.items
                if result.job.company == "Acme AI"
                and result.job.title == "Machine Learning Engineer"
            ]

            self.assertEqual(len(duplicate_hits), 1)

    def test_add_job_and_match(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            settings = AppSettings(database_url=f"sqlite:///{db_path.as_posix()}")
            repository = JobRepository(settings=settings)
            repository.add_job(
                JobCreateRequest(
                    title="Machine Learning Engineer",
                    company="Acme AI",
                    description="Build Python pipelines for model serving and retrieval systems.",
                    remote=True,
                    visa_sponsorship=False,
                )
            )

            results = repository.match_resume("Python FastAPI RAG engineer")

            self.assertTrue(any(result.job.company == "Acme AI" for result in results.items))


class ResumeAnalysisTests(unittest.TestCase):
    def test_analyze_resume_extracts_skills(self) -> None:
        analysis = analyze_resume_text(
            "Python engineer with FastAPI, OpenAI, RAG, Docker, and PostgreSQL experience."
        )

        self.assertIn("python", analysis.extracted_skills)
        self.assertIn("fastapi", analysis.extracted_skills)
        self.assertIn("rag", analysis.extracted_skills)
        self.assertTrue(analysis.summary)


class CliSmokeTests(unittest.TestCase):
    def test_run_info_prints_summary(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            run_info()

        output = buffer.getvalue()
        self.assertIn("Job Search MCP", output)

    def test_run_demo_prints_jobs(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            run_demo()

        output = buffer.getvalue()
        self.assertIn("Seeded demo jobs:", output)
        self.assertIn("Northstar Labs", output)


class IntegrationStyleTests(unittest.TestCase):
    def test_repository_persists_jobs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            settings = AppSettings(database_url=f"sqlite:///{db_path.as_posix()}")

            first = JobRepository(settings=settings)
            first.add_job(
                JobCreateRequest(
                    title="Data Engineer",
                    company="Persist Co",
                    location="Remote",
                    description="Build pipelines and search tooling.",
                )
            )

            second = JobRepository(settings=settings)
            jobs = second.list_jobs()

            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].company, "Persist Co")

    def test_cover_letter_helper(self) -> None:
        repository = JobRepository()
        tools = JobSearchTools(
            repository=repository,
            ingestion=JobIngestionService.with_default_sources(repository),
            cover_letter_generator=CoverLetterGenerator.from_settings(None, "gpt-4o-mini"),
        )

        cover_letter = tools.generate_cover_letter(
            resume_text="Python FastAPI engineer with RAG experience.",
            job_title="AI Engineer",
            company="Northstar Labs",
        )

        self.assertIn("Northstar Labs", cover_letter)
        self.assertIn("AI Engineer", cover_letter)

    def test_parse_docx_resume(self) -> None:
        try:
            from docx import Document
        except Exception as exc:  # pragma: no cover - defensive skip
            self.skipTest(f"python-docx unavailable: {exc}")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "resume.docx"
            document = Document()
            document.add_paragraph("Python engineer with FastAPI and RAG experience.")
            document.save(path)

            extracted = parse_resume_bytes(path.name, path.read_bytes())

        self.assertIn("FastAPI", extracted)

    def test_mcp_context_builds_tools(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            settings = AppSettings(database_url=f"sqlite:///{db_path.as_posix()}")

            context = create_context(settings=settings)

            self.assertTrue(hasattr(context.tools, "search_jobs"))
            self.assertTrue(hasattr(context.tools, "generate_cover_letter"))

    def test_run_mcp_server_registers_tools(self) -> None:
        registered: list[str] = []

        class FakeFastMCP:
            def __init__(self, name: str) -> None:
                self.name = name

            def tool(self):
                def decorator(func):
                    registered.append(func.__name__)
                    return func

                return decorator

            def run(self) -> None:
                registered.append("run")

        fake_fastmcp = types.ModuleType("mcp.server.fastmcp")
        fake_fastmcp.FastMCP = FakeFastMCP
        fake_server = types.ModuleType("mcp.server")
        fake_server.fastmcp = fake_fastmcp
        fake_mcp = types.ModuleType("mcp")
        fake_mcp.server = fake_server

        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jobs.db"
            settings = AppSettings(database_url=f"sqlite:///{db_path.as_posix()}")

            with patch.dict(
                sys.modules,
                {
                    "mcp": fake_mcp,
                    "mcp.server": fake_server,
                    "mcp.server.fastmcp": fake_fastmcp,
                },
            ):
                run_mcp_server(settings=settings)

        self.assertIn("search_jobs", registered)
        self.assertIn("match_resume_to_job", registered)
        self.assertIn("generate_cover_letter", registered)
        self.assertIn("run", registered)


if __name__ == "__main__":
    unittest.main()
