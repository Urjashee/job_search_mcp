from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class JobSource(str, Enum):
    jsearch = "jsearch"
    greenhouse = "greenhouse"
    lever = "lever"
    adzuna = "adzuna"
    remoteok = "remoteok"
    manual = "manual"


class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    company: str
    location: str = "Remote"
    description: str = ""
    source: JobSource = JobSource.manual
    url: str | None = None
    remote: bool = False
    visa_sponsorship: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    title: str
    company: str
    location: str = "Remote"
    description: str = ""
    source: JobSource = JobSource.manual
    url: str | None = None
    remote: bool = False
    visa_sponsorship: bool = False
    tags: list[str] = Field(default_factory=list)


class JobSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)


class ResumeAnalyzeRequest(BaseModel):
    resume_text: str


class ResumeUploadResponse(BaseModel):
    filename: str
    content_type: str | None = None
    extracted_text: str
    analysis: ResumeAnalysis


class CoverLetterRequest(BaseModel):
    resume_text: str
    job_title: str
    company: str


class IngestionSummary(BaseModel):
    source: JobSource
    ingested: int


class JobImportRequest(BaseModel):
    source: JobSource
    reference: str
    company: str | None = None
    query: str | None = None


class MatchRequest(BaseModel):
    resume_text: str


class MatchedJob(BaseModel):
    job: JobPosting
    score: float
    reasons: list[str] = Field(default_factory=list)


class PaginatedMatchedJobs(BaseModel):
    items: list[MatchedJob]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedJobs(BaseModel):
    items: list[JobPosting]
    total: int
    page: int
    page_size: int
    total_pages: int


class ResumeAnalysis(BaseModel):
    extracted_skills: list[str] = Field(default_factory=list)
    summary: str
    match_notes: list[str] = Field(default_factory=list)


class AppInfo(BaseModel):
    name: str = "Job Search MCP"
    version: str = "0.1.0"
    description: str = (
        "Agentic job intelligence platform with MCP, RAG, and multi-source job retrieval."
    )
    capabilities: list[str] = Field(
        default_factory=lambda: [
            "job ingestion",
            "resume analysis",
            "semantic search",
            "agent workflows",
            "MCP tools",
        ]
    )

    def summary(self) -> str:
        capabilities = ", ".join(self.capabilities)
        return f"{self.name} v{self.version}\n{self.description}\nCapabilities: {capabilities}"


@dataclass(slots=True)
class AnalysisConfig:
    skill_keywords: tuple[str, ...] = (
        "python",
        "fastapi",
        "sql",
        "postgresql",
        "pandas",
        "numpy",
        "llm",
        "openai",
        "rag",
        "mcp",
        "langgraph",
        "vector",
        "qdrant",
        "pgvector",
        "docker",
        "kubernetes",
        "react",
        "next.js",
        "typescript",
        "javascript",
        "aws",
        "gcp",
        "azure",
        "ml",
        "machine learning",
    )
    visa_keywords: tuple[str, ...] = (
        "visa sponsorship",
        "sponsorship",
        "work permit",
        "h1b",
        "relocation",
    )
    remote_keywords: tuple[str, ...] = ("remote", "distributed", "work from home")
