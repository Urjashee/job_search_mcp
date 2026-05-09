from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from ..models import JobCreateRequest, JobSource
from ..settings import AppSettings


@dataclass(slots=True)
class IngestedJob:
    title: str
    company: str
    location: str = "Remote"
    description: str = ""
    remote: bool = False
    visa_sponsorship: bool = False
    tags: list[str] | None = None
    url: str | None = None

    def to_request(self, source: JobSource) -> JobCreateRequest:
        return JobCreateRequest(
            title=self.title,
            company=self.company,
            location=self.location,
            description=self.description,
            source=source,
            remote=self.remote,
            visa_sponsorship=self.visa_sponsorship,
            tags=list(self.tags or []),
            url=self.url,
        )


class JobSourceAdapter(Protocol):
    name: JobSource

    def fetch(self) -> list[IngestedJob]:
        """Return jobs for the adapter's source."""


@dataclass(slots=True)
class StaticJobSourceAdapter:
    name: JobSource
    jobs: list[IngestedJob]

    def fetch(self) -> list[IngestedJob]:
        return list(self.jobs)


@dataclass(slots=True)
class GreenhouseBoardAdapter:
    board: str
    company: str | None = None
    name: JobSource = JobSource.greenhouse

    def fetch(self) -> list[IngestedJob]:
        url = self.board
        if not url.startswith("http"):
            url = f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs?content=true"

        with httpx.Client(timeout=20.0) as client:
            response = client.get(url)
            response.raise_for_status()

        payload = response.json()
        jobs: list[IngestedJob] = []
        for item in payload.get("jobs", []):
            jobs.append(
                IngestedJob(
                    title=item.get("title", "Untitled"),
                    company=self.company or self.board,
                    location=(item.get("location") or {}).get("name", "Remote"),
                    description=item.get("content", ""),
                    remote="remote" in ((item.get("location") or {}).get("name", "").lower()),
                    visa_sponsorship=True,
                    tags=["greenhouse"],
                    url=item.get("absolute_url"),
                )
            )
        return jobs


@dataclass(slots=True)
class LeverCompanyAdapter:
    company: str
    name: JobSource = JobSource.lever

    def fetch(self) -> list[IngestedJob]:
        url = self.company
        if not url.startswith("http"):
            url = f"https://api.lever.co/v0/postings/{self.company}?mode=json"

        with httpx.Client(timeout=20.0) as client:
            response = client.get(url)
            response.raise_for_status()

        payload = response.json()
        jobs: list[IngestedJob] = []
        for item in payload:
            location = (item.get("categories") or {}).get("location", "Remote")
            tags = [
                tag
                for tag in [
                    (item.get("categories") or {}).get("commitment"),
                    (item.get("categories") or {}).get("team"),
                ]
                if tag
            ]
            jobs.append(
                IngestedJob(
                    title=item.get("text", "Untitled"),
                    company=self.company,
                    location=location,
                    description=item.get("descriptionPlain", ""),
                    remote="remote" in location.lower(),
                    visa_sponsorship=False,
                    tags=tags or ["lever"],
                    url=item.get("hostedUrl"),
                )
            )
        return jobs


@dataclass(slots=True)
class RapidApiJsearchAdapter:
    api_key: str
    host: str
    query: str = "software engineer"
    location: str = "Remote"
    name: JobSource = JobSource.jsearch

    def fetch(self) -> list[IngestedJob]:
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
        }
        params = {
            "query": self.query,
            "page": "1",
            "num_pages": "1",
            "country": "us",
            "date_posted": "all",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get("https://jsearch.p.rapidapi.com/search", headers=headers, params=params)
            response.raise_for_status()

        payload = response.json()
        jobs: list[IngestedJob] = []
        for item in payload.get("data", []):
            jobs.append(
                IngestedJob(
                    title=item.get("job_title", "Untitled"),
                    company=item.get("employer_name", "Unknown"),
                    location=item.get("job_city") or item.get("job_country") or self.location,
                    description=item.get("job_description", ""),
                    remote=bool(item.get("job_is_remote")),
                    visa_sponsorship=bool(item.get("job_apply_link")),
                    tags=["rapidapi", "jsearch"],
                    url=item.get("job_apply_link"),
                )
            )
        return jobs


@dataclass(slots=True)
class AdzunaAdapter:
    app_id: str
    app_key: str
    country: str = "us"
    query: str = "software engineer"
    name: JobSource = JobSource.adzuna

    def fetch(self) -> list[IngestedJob]:
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": self.query,
            "content-type": "application/json",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1", params=params)
            response.raise_for_status()

        payload = response.json()
        jobs: list[IngestedJob] = []
        for item in payload.get("results", []):
            jobs.append(
                IngestedJob(
                    title=item.get("title", "Untitled"),
                    company=(item.get("company") or {}).get("display_name", "Unknown"),
                    location=(item.get("location") or {}).get("display_name", self.country.upper()),
                    description=item.get("description", ""),
                    remote="remote" in item.get("description", "").lower(),
                    visa_sponsorship=False,
                    tags=["adzuna"],
                    url=item.get("redirect_url"),
                )
            )
        return jobs


def build_import_adapter(
    source: JobSource,
    reference: str,
    settings: AppSettings,
    company: str | None = None,
    query: str | None = None,
) -> JobSourceAdapter:
    normalized_reference = reference.strip()

    if source == JobSource.greenhouse:
        return GreenhouseBoardAdapter(board=normalized_reference, company=company)

    if source == JobSource.lever:
        return LeverCompanyAdapter(company=normalized_reference)

    if source == JobSource.jsearch:
        if not settings.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY is required for Jsearch imports")
        return RapidApiJsearchAdapter(
            api_key=settings.rapidapi_key,
            host=settings.rapidapi_host,
            query=query or normalized_reference or "software engineer",
        )

    if source == JobSource.adzuna:
        if not (settings.adzuna_app_id and settings.adzuna_app_key):
            raise ValueError("ADZUNA_APP_ID and ADZUNA_APP_KEY are required for Adzuna imports")
        return AdzunaAdapter(
            app_id=settings.adzuna_app_id,
            app_key=settings.adzuna_app_key,
            query=query or normalized_reference or "software engineer",
        )

    raise ValueError(f"Unsupported import source: {source}")


def build_default_adapters(settings: AppSettings) -> list[JobSourceAdapter]:
    adapters: list[JobSourceAdapter] = []

    for board in settings.greenhouse_boards:
        adapters.append(GreenhouseBoardAdapter(board=board))

    for company in settings.lever_companies:
        adapters.append(LeverCompanyAdapter(company=company))

    if settings.rapidapi_key:
        adapters.append(
            RapidApiJsearchAdapter(
                api_key=settings.rapidapi_key,
                host=settings.rapidapi_host,
            )
        )

    if settings.adzuna_app_id and settings.adzuna_app_key:
        adapters.append(
            AdzunaAdapter(
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key,
            )
        )

    if not adapters:
        adapters.extend(
            [
                StaticJobSourceAdapter(
                    name=JobSource.jsearch,
                    jobs=[
                        IngestedJob(
                            title="AI Engineer",
                            company="Northstar Labs",
                            location="Remote",
                            description="Build agentic workflows, RAG pipelines, and API tooling for internal search.",
                            remote=True,
                            visa_sponsorship=True,
                            tags=["python", "rag", "agents", "fastapi"],
                        ),
                        IngestedJob(
                            title="Full Stack AI Engineer",
                            company="Northstar Labs",
                            location="Remote",
                            description="Ship dashboards, prompt tooling, and job workflow automations for recruiting teams.",
                            remote=True,
                            visa_sponsorship=True,
                            tags=["react", "typescript", "python", "llm"],
                        ),
                        IngestedJob(
                            title="Applied LLM Engineer",
                            company="Orbit Harbor",
                            location="New York, NY",
                            description="Build evaluation pipelines, retrieval agents, and enterprise copilots.",
                            remote=False,
                            visa_sponsorship=False,
                            tags=["llm", "evaluation", "search", "python"],
                        ),
                    ],
                ),
                StaticJobSourceAdapter(
                    name=JobSource.greenhouse,
                    jobs=[
                        IngestedJob(
                            title="Backend Engineer",
                            company="VectorWorks",
                            location="Berlin, Germany",
                            description="Design job search APIs, indexing pipelines, and observability for hiring products.",
                            remote=False,
                            visa_sponsorship=True,
                            tags=["python", "fastapi", "postgresql", "search"],
                        ),
                        IngestedJob(
                            title="Data Platform Engineer",
                            company="Atlas Metrics",
                            location="Amsterdam, Netherlands",
                            description="Own data ingestion, search indexing, and internal analytics tooling.",
                            remote=False,
                            visa_sponsorship=True,
                            tags=["sql", "airflow", "postgresql", "analytics"],
                        ),
                        IngestedJob(
                            title="Backend Product Engineer",
                            company="Northwind AI",
                            location="Remote",
                            description="Build APIs for matching, notifications, and user workflows.",
                            remote=True,
                            visa_sponsorship=False,
                            tags=["fastapi", "apis", "product", "python"],
                        ),
                    ],
                ),
                StaticJobSourceAdapter(
                    name=JobSource.lever,
                    jobs=[
                        IngestedJob(
                            title="Machine Learning Engineer",
                            company="Signal Forge",
                            location="Remote",
                            description="Create ranking systems, embeddings workflows, and evaluation pipelines.",
                            remote=True,
                            visa_sponsorship=False,
                            tags=["ml", "embeddings", "search", "python"],
                        ),
                        IngestedJob(
                            title="Machine Learning Platform Engineer",
                            company="Signal Forge",
                            location="Remote",
                            description="Maintain model serving, experiment tracking, and ranking infrastructure.",
                            remote=True,
                            visa_sponsorship=False,
                            tags=["mlops", "docker", "kubernetes", "python"],
                        ),
                        IngestedJob(
                            title="Developer Experience Engineer",
                            company="Pulse Grid",
                            location="Toronto, Canada",
                            description="Improve internal tooling, SDKs, and developer workflows.",
                            remote=False,
                            visa_sponsorship=True,
                            tags=["sdk", "tooling", "typescript", "docs"],
                        ),
                    ],
                ),
            ]
        )

    return adapters
