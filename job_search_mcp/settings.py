from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class AppSettings:
    database_url: str = "sqlite:///./job_search_mcp.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "job_search_mcp_jobs"
    rapidapi_key: str | None = None
    rapidapi_host: str = "jsearch.p.rapidapi.com"
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    greenhouse_boards: list[str] = field(default_factory=list)
    lever_companies: list[str] = field(default_factory=list)
    cors_origins: list[str] = field(default_factory=list)
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    background_sync_enabled: bool = False
    background_sync_interval_seconds: int = 3600

    @classmethod
    def from_env(cls) -> "AppSettings":
        load_dotenv()
        cors_origins = _split_csv(os.getenv("CORS_ORIGINS"))
        if not cors_origins:
            cors_origins = [
                os.getenv("FRONTEND_URL", "http://localhost:5173"),
                "http://localhost:3000",
            ]

        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./job_search_mcp.db"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            qdrant_url=os.getenv("QDRANT_URL") or None,
            qdrant_api_key=os.getenv("QDRANT_API_KEY") or None,
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "job_search_mcp_jobs"),
            rapidapi_key=os.getenv("RAPIDAPI_KEY") or None,
            rapidapi_host=os.getenv("JSEARCH_RAPIDAPI_HOST", "jsearch.p.rapidapi.com"),
            adzuna_app_id=os.getenv("ADZUNA_APP_ID") or None,
            adzuna_app_key=os.getenv("ADZUNA_APP_KEY") or None,
            greenhouse_boards=_split_csv(os.getenv("GREENHOUSE_BOARDS")),
            lever_companies=_split_csv(os.getenv("LEVER_COMPANIES")),
            cors_origins=cors_origins,
            frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            background_sync_enabled=os.getenv("BACKGROUND_SYNC_ENABLED", "false").lower()
            in {"1", "true", "yes", "on"},
            background_sync_interval_seconds=int(
                os.getenv("BACKGROUND_SYNC_INTERVAL_SECONDS", "3600")
            ),
        )

    @property
    def sqlite_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.removeprefix("sqlite:///"))
        return Path("./job_search_mcp.db")
