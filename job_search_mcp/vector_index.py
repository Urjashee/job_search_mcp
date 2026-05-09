from __future__ import annotations

from dataclasses import dataclass

from .settings import AppSettings


@dataclass(slots=True)
class VectorSearchHit:
    job_id: str
    score: float


class VectorIndex:
    def upsert(self, job_id: str, vector: list[float], payload: dict[str, object] | None = None) -> None:
        raise NotImplementedError

    def search(self, vector: list[float], limit: int = 10) -> list[VectorSearchHit]:
        raise NotImplementedError


class NullVectorIndex(VectorIndex):
    def upsert(self, job_id: str, vector: list[float], payload: dict[str, object] | None = None) -> None:
        return None

    def search(self, vector: list[float], limit: int = 10) -> list[VectorSearchHit]:
        return []


class QdrantVectorIndex(VectorIndex):
    def __init__(self, settings: AppSettings, dimensions: int = 128) -> None:
        self.settings = settings
        self.dimensions = dimensions
        self.collection_name = settings.qdrant_collection

        try:
            from qdrant_client import QdrantClient  # type: ignore[import-not-found]
            from qdrant_client.http import models as qmodels  # type: ignore[import-not-found]
        except Exception:
            self._client = None
            self._models = None
            return

        if settings.qdrant_url:
            try:
                self._client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key,
                )
            except Exception:
                self._client = None
                self._models = None
                return
        else:
            try:
                self._client = QdrantClient(location=":memory:")
            except Exception:
                self._client = None
                self._models = None
                return

        self._models = qmodels
        try:
            self._ensure_collection()
        except Exception:
            self._client = None
            self._models = None

    @classmethod
    def from_settings(cls, settings: AppSettings, dimensions: int = 128) -> "VectorIndex":
        index = cls(settings=settings, dimensions=dimensions)
        if index._client is None:
            return NullVectorIndex()
        return index

    def _ensure_collection(self) -> None:
        assert self._client is not None
        assert self._models is not None
        collections = self._client.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            return

        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self._models.VectorParams(
                size=self.dimensions,
                distance=self._models.Distance.COSINE,
            ),
        )

    def upsert(self, job_id: str, vector: list[float], payload: dict[str, object] | None = None) -> None:
        assert self._client is not None
        assert self._models is not None
        self._client.upsert(
            collection_name=self.collection_name,
            points=[
                self._models.PointStruct(
                    id=job_id,
                    vector=vector,
                    payload=payload or {"job_id": job_id},
                )
            ],
        )

    def search(self, vector: list[float], limit: int = 10) -> list[VectorSearchHit]:
        assert self._client is not None
        if hasattr(self._client, "search"):
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True,
            )
        else:
            response = self._client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                with_payload=True,
            )
            results = getattr(response, "points", response)

        hits: list[VectorSearchHit] = []
        for result in results:
            payload = result.payload or {}
            job_id = payload.get("job_id") or str(result.id)
            hits.append(VectorSearchHit(job_id=str(job_id), score=float(result.score)))
        return hits
