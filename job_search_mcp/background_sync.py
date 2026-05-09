from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

from .models import IngestionSummary
from .services.ingestion import JobIngestionService


@dataclass(slots=True)
class SyncStatus:
    enabled: bool
    interval_seconds: int
    running: bool = False
    last_started_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_results: list[IngestionSummary] = field(default_factory=list)


class BackgroundSyncService:
    def __init__(
        self,
        ingestion: JobIngestionService,
        interval_seconds: int = 3600,
        enabled: bool = False,
    ) -> None:
        self.ingestion = ingestion
        self.interval_seconds = max(60, interval_seconds)
        self.status = SyncStatus(enabled=enabled, interval_seconds=self.interval_seconds)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if not self.status.enabled:
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="job-search-sync",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def run_once(self) -> list[IngestionSummary]:
        with self._lock:
            self.status.running = True
            self.status.last_started_at = datetime.now(timezone.utc)
            try:
                results = self.ingestion.ingest_all()
            finally:
                self.status.running = False
                self.status.last_completed_at = datetime.now(timezone.utc)
                self.status.last_results = results if "results" in locals() else []
            return self.status.last_results

    def snapshot(self) -> SyncStatus:
        with self._lock:
            return SyncStatus(
                enabled=self.status.enabled,
                interval_seconds=self.status.interval_seconds,
                running=self.status.running,
                last_started_at=self.status.last_started_at,
                last_completed_at=self.status.last_completed_at,
                last_results=list(self.status.last_results),
            )

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.run_once()
