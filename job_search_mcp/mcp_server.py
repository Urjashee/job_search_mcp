from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .llm import CoverLetterGenerator
from .models import AppInfo, JobSource
from .settings import AppSettings
from .services.ingestion import JobIngestionService
from .services.jobs import JobRepository
from .services.mcp_tools import JobSearchTools
from .services.sources import build_import_adapter


@dataclass(slots=True)
class MCPContext:
    settings: AppSettings
    repository: JobRepository
    ingestion: JobIngestionService
    tools: JobSearchTools


def create_context(settings: AppSettings | None = None) -> MCPContext:
    resolved_settings = settings or AppSettings.from_env()
    repository = JobRepository(settings=resolved_settings)
    ingestion = JobIngestionService.with_default_sources(
        repository=repository,
        settings=resolved_settings,
    )
    cover_letter_generator = CoverLetterGenerator.from_settings(
        api_key=resolved_settings.openai_api_key,
        model=resolved_settings.openai_model,
    )
    tools = JobSearchTools(
        repository=repository,
        ingestion=ingestion,
        cover_letter_generator=cover_letter_generator,
    )
    return MCPContext(
        settings=resolved_settings,
        repository=repository,
        ingestion=ingestion,
        tools=tools,
    )


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def run_mcp_server(settings: AppSettings | None = None) -> None:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The MCP server requires the 'mcp' package. Install dependencies and rerun."
        ) from exc

    context = create_context(settings=settings)
    mcp = FastMCP("Job Search MCP")

    @mcp.tool()
    def app_info() -> dict[str, Any]:
        return _serialize(AppInfo())

    @mcp.tool()
    def search_jobs(query: str, page_size: int = 10, page: int = 1) -> dict[str, Any]:
        return _serialize(context.tools.search_jobs(query=query, page_size=page_size, page=page))

    @mcp.tool()
    def match_resume_to_job(resume_text: str) -> dict[str, Any]:
        return _serialize(context.tools.match_resume_to_job(resume_text))

    @mcp.tool()
    def analyze_resume(resume_text: str) -> dict[str, Any]:
        return _serialize(context.tools.analyze_resume(resume_text))

    @mcp.tool()
    def find_sponsorship_jobs(query: str = "visa sponsorship", limit: int = 10) -> list[dict[str, Any]]:
        return _serialize(context.tools.find_sponsorship_jobs(query=query, limit=limit))

    @mcp.tool()
    def generate_cover_letter(resume_text: str, job_title: str, company: str) -> str:
        return context.tools.generate_cover_letter(
            resume_text=resume_text,
            job_title=job_title,
            company=company,
        )

    @mcp.tool()
    def list_jobs(page: int = 1, page_size: int = 10) -> dict[str, Any]:
        return _serialize(context.repository.list_jobs_page(page=page, page_size=page_size))

    @mcp.tool()
    def ingest_source(source: str) -> dict[str, Any]:
        parsed_source = JobSource(source)
        return _serialize(context.ingestion.ingest(parsed_source))

    @mcp.tool()
    def ingest_all_sources() -> list[dict[str, Any]]:
        return _serialize(context.ingestion.ingest_all())

    @mcp.tool()
    def import_jobs(
        source: str,
        reference: str,
        company: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        parsed_source = JobSource(source)
        adapter = build_import_adapter(
            source=parsed_source,
            reference=reference,
            settings=context.settings,
            company=company,
            query=query,
        )
        count = 0
        for item in adapter.fetch():
            context.repository.add_job(item.to_request(parsed_source))
            count += 1
        return _serialize({"source": parsed_source, "ingested": count})

    mcp.run()
