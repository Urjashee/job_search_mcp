from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import closing

from .embeddings import text_to_vector, vector_to_text
from .models import JobPosting


class SQLiteJobStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT,
                    remote INTEGER NOT NULL,
                    visa_sponsorship INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS job_embeddings (
                    job_id TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );
                """
            )

    def upsert_job(self, job: JobPosting, embedding: list[float]) -> JobPosting:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, title, company, location, description, source, url,
                    remote, visa_sponsorship, created_at, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    company=excluded.company,
                    location=excluded.location,
                    description=excluded.description,
                    source=excluded.source,
                    url=excluded.url,
                    remote=excluded.remote,
                    visa_sponsorship=excluded.visa_sponsorship,
                    created_at=excluded.created_at,
                    tags_json=excluded.tags_json
                """,
                (
                    job.id,
                    job.title,
                    job.company,
                    job.location,
                    job.description,
                    job.source.value,
                    job.url,
                    int(job.remote),
                    int(job.visa_sponsorship),
                    job.created_at.isoformat(),
                    ",".join(job.tags),
                ),
            )
            connection.execute(
                """
                INSERT INTO job_embeddings (job_id, embedding)
                VALUES (?, ?)
                ON CONFLICT(job_id) DO UPDATE SET embedding=excluded.embedding
                """,
                (job.id, vector_to_text(embedding)),
            )
            connection.commit()
        return job

    def list_jobs(self) -> list[JobPosting]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_job(self, job_id: str) -> JobPosting | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_embeddings(self) -> dict[str, list[float]]:
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT job_id, embedding FROM job_embeddings").fetchall()
        return {row["job_id"]: text_to_vector(row["embedding"]) for row in rows}

    def count_jobs(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()
        return int(row["count"] if row else 0)

    def _row_to_job(self, row: sqlite3.Row) -> JobPosting:
        tags = [tag for tag in row["tags_json"].split(",") if tag]
        return JobPosting(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            description=row["description"],
            source=row["source"],
            url=row["url"],
            remote=bool(row["remote"]),
            visa_sponsorship=bool(row["visa_sponsorship"]),
            created_at=row["created_at"],
            tags=tags,
        )
