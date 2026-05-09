from __future__ import annotations

from fastapi import File, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import __version__
from .background_sync import BackgroundSyncService
from .frontend import render_index_html
from .llm import CoverLetterGenerator
from .models import (
    AppInfo,
    CoverLetterRequest,
    IngestionSummary,
    JobCreateRequest,
    JobImportRequest,
    JobSource,
    JobSearchRequest,
    PaginatedJobs,
    PaginatedMatchedJobs,
    MatchRequest,
    ResumeAnalyzeRequest,
    ResumeUploadResponse,
)
from .services.ingestion import JobIngestionService
from .services.jobs import JobRepository, analyze_resume_text, parse_resume_bytes
from .services.mcp_tools import JobSearchTools
from .settings import AppSettings
from .services.sources import build_import_adapter

settings = AppSettings.from_env()
app = FastAPI(
    title="Job Search MCP",
    version=__version__,
    description="API for an agentic job intelligence platform.",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

repository = JobRepository(settings=settings)
ingestion = JobIngestionService.with_default_sources(repository=repository, settings=settings)
cover_letter_generator = CoverLetterGenerator.from_settings(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
)
tools = JobSearchTools(
    repository=repository,
    ingestion=ingestion,
    cover_letter_generator=cover_letter_generator,
)
background_sync = BackgroundSyncService(
    ingestion=ingestion,
    interval_seconds=settings.background_sync_interval_seconds,
    enabled=settings.background_sync_enabled,
)


@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url=settings.frontend_url, status_code=307)


@app.on_event("startup")
def start_background_sync() -> None:
    if repository.count_jobs() == 0:
        repository.seed_demo_jobs()
    background_sync.start()


@app.on_event("shutdown")
def stop_background_sync() -> None:
    background_sync.stop()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/info")
def info() -> AppInfo:
    return AppInfo()


@app.get("/jobs")
def list_jobs(page: int = 1, page_size: int = 10) -> PaginatedJobs:
    return repository.list_jobs_page(page=page, page_size=page_size)


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    return {"item": repository.get_job(job_id)}


@app.post("/jobs")
def create_job(payload: JobCreateRequest) -> dict[str, object]:
    return {"item": repository.add_job(payload)}


@app.post("/jobs/search")
def search_jobs(payload: JobSearchRequest) -> PaginatedMatchedJobs:
    return tools.search_jobs(payload.query, payload.page_size, payload.page)


@app.post("/jobs/match")
def match_jobs(payload: MatchRequest) -> PaginatedMatchedJobs:
    return tools.match_resume_to_job(payload.resume_text)


@app.post("/resumes/analyze")
def analyze_resume(payload: ResumeAnalyzeRequest) -> dict[str, object]:
    return {"item": tools.analyze_resume(payload.resume_text)}


@app.post("/resumes/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    content = await file.read()

    try:
        extracted_text = parse_resume_bytes(file.filename or "resume", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    analysis = analyze_resume_text(extracted_text)
    return ResumeUploadResponse(
        filename=file.filename or "resume",
        content_type=file.content_type,
        extracted_text=extracted_text,
        analysis=analysis,
    )


@app.get("/ingestion/sources")
def list_ingestion_sources() -> dict[str, object]:
    return {"items": [source.value for source in ingestion.adapters]}


@app.post("/ingestion/all", response_model=list[IngestionSummary])
def ingest_all_sources() -> list[IngestionSummary]:
    return ingestion.ingest_all()


@app.post("/ingestion/import", response_model=IngestionSummary)
def import_jobs(payload: JobImportRequest) -> IngestionSummary:
    try:
        adapter = build_import_adapter(
            source=payload.source,
            reference=payload.reference,
            settings=settings,
            company=payload.company,
            query=payload.query,
        )
        count = 0
        for item in adapter.fetch():
            repository.add_job(item.to_request(payload.source))
            count += 1
        return IngestionSummary(source=payload.source, ingested=count)
    except Exception:
        return IngestionSummary(source=payload.source, ingested=0)


@app.get("/ingestion/sync/status")
def sync_status() -> dict[str, object]:
    snapshot = background_sync.snapshot()
    return {
        "enabled": snapshot.enabled,
        "interval_seconds": snapshot.interval_seconds,
        "running": snapshot.running,
        "last_started_at": snapshot.last_started_at,
        "last_completed_at": snapshot.last_completed_at,
        "last_results": snapshot.last_results,
    }


@app.post("/ingestion/sync/run")
def run_sync_now() -> list[IngestionSummary]:
    return background_sync.run_once()


@app.post("/ingestion/{source}", response_model=IngestionSummary)
def ingest_source(source: JobSource) -> IngestionSummary:
    return ingestion.ingest(source)


@app.post("/tools/cover-letter")
def generate_cover_letter(payload: CoverLetterRequest) -> dict[str, str]:
    return {
        "item": tools.generate_cover_letter(
            resume_text=payload.resume_text,
            job_title=payload.job_title,
            company=payload.company,
        )
    }
