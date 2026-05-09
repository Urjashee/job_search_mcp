from __future__ import annotations

from dataclasses import dataclass, field

from ..models import IngestionSummary, JobSource
from ..settings import AppSettings
from .jobs import JobRepository
from .sources import JobSourceAdapter, build_default_adapters


@dataclass(slots=True)
class JobIngestionService:
    repository: JobRepository
    settings: AppSettings
    adapters: dict[JobSource, JobSourceAdapter] = field(default_factory=dict)

    @classmethod
    def with_default_sources(
        cls,
        repository: JobRepository,
        settings: AppSettings | None = None,
    ) -> "JobIngestionService":
        settings = settings or AppSettings.from_env()
        adapters = {adapter.name: adapter for adapter in build_default_adapters(settings)}
        return cls(repository=repository, settings=settings, adapters=adapters)

    def ingest(self, source: JobSource) -> IngestionSummary:
        adapter = self.adapters.get(source)
        if adapter is None:
            return IngestionSummary(source=source, ingested=0)

        count = 0
        try:
            for item in adapter.fetch():
                self.repository.add_job(item.to_request(source))
                count += 1
        except Exception:
            return IngestionSummary(source=source, ingested=0)
        return IngestionSummary(source=source, ingested=count)

    def ingest_all(self) -> list[IngestionSummary]:
        return [self.ingest(source) for source in self.adapters]
