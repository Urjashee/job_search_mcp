from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from io import BytesIO
import re
from pathlib import Path

from ..embeddings import TextEmbedder, cosine_similarity
from ..models import (
    AnalysisConfig,
    JobCreateRequest,
    JobPosting,
    JobSearchRequest,
    PaginatedJobs,
    PaginatedMatchedJobs,
    MatchedJob,
    ResumeAnalysis,
)
from ..settings import AppSettings
from ..storage import SQLiteJobStore
from ..vector_index import VectorIndex, QdrantVectorIndex

_SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "job",
    "jobs",
    "looking",
    "of",
    "on",
    "or",
    "seeking",
    "the",
    "to",
    "with",
}

_TITLE_NOISE = {
    "backend",
    "frontend",
    "full",
    "junior",
    "lead",
    "mid",
    "principal",
    "senior",
    "stack",
    "staff",
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if token}


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if token not in _SEARCH_STOPWORDS}


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    normalized = _normalize(text)
    return any(phrase in normalized for phrase in phrases)


def _job_text(job: JobPosting) -> str:
    return " ".join(
        [
            job.title,
            job.company,
            job.location,
            job.description,
            " ".join(job.tags),
        ]
    )


def _job_signature(job: JobPosting) -> str:
    normalized_description = " ".join(_normalize(job.description).split()[:20])
    normalized_tags = " ".join(sorted(_tokens(" ".join(job.tags))))
    return " | ".join(
        [
            _normalize(job.title),
            _normalize(job.company),
            _normalize(job.location),
            normalized_tags,
            normalized_description,
        ]
    )


def _title_family(job: JobPosting) -> str:
    title_tokens = [token for token in _meaningful_tokens(job.title) if token not in _TITLE_NOISE]
    if title_tokens:
        return " ".join(sorted(title_tokens))
    return _normalize(job.title)


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int, int]:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(max(page, 1), total_pages)
    start = (safe_page - 1) * page_size
    end = start + page_size
    return items[start:end], total, total_pages


@dataclass(slots=True)
class JobRepository:
    settings: AppSettings
    store: SQLiteJobStore
    embedder: TextEmbedder
    vector_index: VectorIndex

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.from_env()
        self.store = SQLiteJobStore(self.settings.sqlite_path)
        self.embedder = TextEmbedder()
        self.vector_index = QdrantVectorIndex.from_settings(self.settings, dimensions=self.embedder.dimensions)

    def add_job(self, job: JobCreateRequest) -> JobPosting:
        posting = JobPosting(**job.model_dump())
        embedding = self.embedder.embed(_job_text(posting))
        stored = self.store.upsert_job(posting, embedding)
        self.vector_index.upsert(
            stored.id,
            embedding,
            payload={"job_id": stored.id, "source": stored.source.value},
        )
        return stored

    def list_jobs(self) -> list[JobPosting]:
        return self.store.list_jobs()

    def list_jobs_page(self, page: int = 1, page_size: int = 10) -> PaginatedJobs:
        jobs = self.list_jobs()
        page_items, total, total_pages = _paginate(jobs, page, page_size)
        safe_page = min(max(page, 1), total_pages)
        return PaginatedJobs(
            items=page_items,
            total=total,
            page=safe_page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_job(self, job_id: str) -> JobPosting | None:
        return self.store.get_job(job_id)

    def count_jobs(self) -> int:
        return self.store.count_jobs()

    def seed_demo_jobs(self) -> list[JobPosting]:
        demo_jobs = [
            JobCreateRequest(
                title="AI Engineer",
                company="Northstar Labs",
                location="Remote",
                description="Build agentic workflows, RAG pipelines, and API tooling for internal search.",
                remote=True,
                visa_sponsorship=True,
                tags=["python", "rag", "agents", "fastapi"],
            ),
            JobCreateRequest(
                title="Full Stack AI Engineer",
                company="Northstar Labs",
                location="Remote",
                description="Ship dashboards, prompt tooling, and job workflow automations for recruiting teams.",
                remote=True,
                visa_sponsorship=True,
                tags=["react", "typescript", "python", "llm"],
            ),
            JobCreateRequest(
                title="Applied LLM Engineer",
                company="Orbit Harbor",
                location="New York, NY",
                description="Build evaluation pipelines, retrieval agents, and enterprise copilots.",
                remote=False,
                visa_sponsorship=False,
                tags=["llm", "evaluation", "search", "python"],
            ),
            JobCreateRequest(
                title="Backend Engineer",
                company="VectorWorks",
                location="Berlin, Germany",
                description="Design job search APIs, indexing pipelines, and observability for hiring products.",
                remote=False,
                visa_sponsorship=True,
                tags=["python", "fastapi", "postgresql", "search"],
            ),
            JobCreateRequest(
                title="Data Platform Engineer",
                company="Atlas Metrics",
                location="Amsterdam, Netherlands",
                description="Own data ingestion, search indexing, and internal analytics tooling.",
                remote=False,
                visa_sponsorship=True,
                tags=["sql", "airflow", "postgresql", "analytics"],
            ),
            JobCreateRequest(
                title="Backend Product Engineer",
                company="Northwind AI",
                location="Remote",
                description="Build APIs for matching, notifications, and user workflows.",
                remote=True,
                visa_sponsorship=False,
                tags=["fastapi", "apis", "product", "python"],
            ),
            JobCreateRequest(
                title="Machine Learning Engineer",
                company="Signal Forge",
                location="Remote",
                description="Create ranking systems, embeddings workflows, and evaluation pipelines.",
                remote=True,
                visa_sponsorship=False,
                tags=["ml", "embeddings", "search", "python"],
            ),
            JobCreateRequest(
                title="Machine Learning Platform Engineer",
                company="Signal Forge",
                location="Remote",
                description="Maintain model serving, experiment tracking, and ranking infrastructure.",
                remote=True,
                visa_sponsorship=False,
                tags=["mlops", "docker", "kubernetes", "python"],
            ),
            JobCreateRequest(
                title="Developer Experience Engineer",
                company="Pulse Grid",
                location="Toronto, Canada",
                description="Improve internal tooling, SDKs, and developer workflows.",
                remote=False,
                visa_sponsorship=True,
                tags=["sdk", "tooling", "typescript", "docs"],
            ),
        ]

        for job in demo_jobs:
            self.add_job(job)

        return self.list_jobs()

    def search(self, request: JobSearchRequest) -> PaginatedMatchedJobs:
        query_embedding = self.embedder.embed(request.query)
        query_terms = _meaningful_tokens(request.query)
        query_norm = _normalize(request.query)
        jobs_by_id = {job.id: job for job in self.list_jobs()}
        candidate_ids = [hit.job_id for hit in self.vector_index.search(query_embedding, limit=max(request.limit * 5, 20))]
        if not candidate_ids:
            candidate_ids = list(jobs_by_id)
        scored: list[MatchedJob] = []

        for job_id in candidate_ids:
            job = jobs_by_id.get(job_id)
            if job is None:
                continue
            score, reasons = self._score_job(
                job=job,
                query_terms=query_terms,
                query_text=request.query,
                query_embedding=query_embedding,
                job_embedding=self.embedder.embed(_job_text(job)),
                query_norm=query_norm,
            )
            if score > 0:
                scored.append(MatchedJob(job=job, score=round(score, 3), reasons=reasons))

        scored.sort(key=lambda item: item.score, reverse=True)
        diversified: list[MatchedJob] = []
        seen_signatures: set[str] = set()
        company_counts: dict[str, int] = {}
        title_family_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}

        for item in scored:
            signature = _job_signature(item.job)
            if signature in seen_signatures:
                continue

            company_key = item.job.company.lower()
            title_key = f"{company_key}|{_title_family(item.job)}"
            source_key = item.job.source.value

            if company_counts.get(company_key, 0) >= 2:
                continue
            if title_family_counts.get(title_key, 0) >= 1:
                continue
            if source_counts.get(source_key, 0) >= 3:
                continue

            diversified.append(item)
            seen_signatures.add(signature)
            company_counts[company_key] = company_counts.get(company_key, 0) + 1
            title_family_counts[title_key] = title_family_counts.get(title_key, 0) + 1
            source_counts[source_key] = source_counts.get(source_key, 0) + 1

            if len(diversified) >= request.limit:
                break

        final_items = diversified if diversified else scored
        page_items, total, total_pages = _paginate(final_items, request.page, request.page_size)
        safe_page = min(max(request.page, 1), total_pages)
        return PaginatedMatchedJobs(
            items=page_items,
            total=total,
            page=safe_page,
            page_size=request.page_size,
            total_pages=total_pages,
        )

    def match_resume(self, resume_text: str, limit: int = 10) -> PaginatedMatchedJobs:
        return self.search(JobSearchRequest(query=resume_text, limit=limit, page=1, page_size=limit))

    def _score_job(
        self,
        job: JobPosting,
        query_terms: set[str],
        query_text: str,
        query_embedding: list[float],
        job_embedding: list[float],
        query_norm: str,
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        title_terms = _meaningful_tokens(job.title)
        tag_terms = _meaningful_tokens(" ".join(job.tags))
        company_terms = _meaningful_tokens(job.company)
        location_terms = _meaningful_tokens(job.location)
        description_terms = _meaningful_tokens(job.description)

        title_overlap = query_terms & title_terms
        tag_overlap = query_terms & tag_terms
        company_overlap = query_terms & company_terms
        location_overlap = query_terms & location_terms
        description_overlap = query_terms & description_terms

        score = 0.0
        if title_overlap:
            title_score = len(title_overlap) * 2.0
            score += title_score
            reasons.append(f"title match: {', '.join(sorted(title_overlap))}")

        if tag_overlap:
            tag_score = len(tag_overlap) * 1.5
            score += tag_score
            reasons.append(f"tag match: {', '.join(sorted(tag_overlap))}")

        if company_overlap:
            company_score = len(company_overlap) * 0.75
            score += company_score
            reasons.append(f"company match: {', '.join(sorted(company_overlap))}")

        if location_overlap:
            location_score = len(location_overlap)
            score += location_score
            reasons.append(f"location match: {', '.join(sorted(location_overlap))}")

        if description_overlap:
            description_score = len(description_overlap) * 0.5
            score += description_score
            reasons.append(f"description match: {', '.join(sorted(description_overlap))}")

        all_terms = title_terms | tag_terms | company_terms | location_terms | description_terms
        coverage = len(query_terms & all_terms) / max(len(query_terms), 1)
        if coverage > 0:
            score += coverage
            reasons.append("query coverage")

        text_norm = _normalize(_job_text(job))
        similarity = SequenceMatcher(None, query_norm, text_norm).ratio()
        if similarity > 0.25:
            score += similarity * 0.75
            reasons.append("text similarity")

        vector_similarity = cosine_similarity(query_embedding, job_embedding)
        if vector_similarity > 0.15:
            score += vector_similarity * 1.5
            reasons.append("vector similarity")

        if job.remote and {"remote", "distributed", "hybrid"} & query_terms:
            score += 1.0
            reasons.append("remote match")

        if job.visa_sponsorship and _contains_any(query_text, AnalysisConfig().visa_keywords):
            score += 1.0
            reasons.append("visa sponsorship match")

        if _normalize(job.title) and _normalize(job.title) in query_norm:
            score += 1.0
            reasons.append("title match")

        return score, reasons


def analyze_resume_text(resume_text: str) -> ResumeAnalysis:
    config = AnalysisConfig()
    normalized = _normalize(resume_text)

    skills = [skill for skill in config.skill_keywords if skill in normalized]
    notes: list[str] = []

    if _contains_any(resume_text, config.remote_keywords):
        notes.append("mentions remote work preference")
    if _contains_any(resume_text, config.visa_keywords):
        notes.append("mentions visa or relocation support")
    if not skills:
        notes.append("no obvious skills extracted from the current keyword set")

    summary = (
        f"Detected {len(skills)} skill signals"
        if skills
        else "No clear technical skill signals detected"
    )

    return ResumeAnalysis(extracted_skills=skills, summary=summary, match_notes=notes)


def parse_resume_bytes(filename: str, content: bytes) -> str:
    """
    Convert an uploaded resume into text.

    Supports text, PDF, and DOCX uploads. If no specialized parser is available
    or the file is not one of those formats, falls back to best-effort decoding.
    """

    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz  # type: ignore[import-not-found]
        except Exception:
            pass
        else:
            document = fitz.open(stream=content, filetype="pdf")
            pages = [page.get_text("text") for page in document]
            cleaned = "\n".join(page.strip() for page in pages if page.strip())
            if cleaned:
                return cleaned

    if suffix == ".docx":
        try:
            from docx import Document  # type: ignore[import-not-found]
        except Exception:
            pass
        else:
            document = Document(BytesIO(content))
            paragraphs = [
                paragraph.text.strip()
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            cleaned = "\n".join(paragraphs)
            if cleaned:
                return cleaned

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="ignore")

    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    if not cleaned:
        raise ValueError(f"Could not extract readable text from {filename}")

    return cleaned
