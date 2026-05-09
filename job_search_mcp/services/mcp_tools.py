from __future__ import annotations

from dataclasses import dataclass

from ..llm import CoverLetterGenerator
from ..models import AppInfo
from .ingestion import JobIngestionService
from .jobs import JobRepository, analyze_resume_text


@dataclass(slots=True)
class JobSearchTools:
    repository: JobRepository
    ingestion: JobIngestionService
    cover_letter_generator: CoverLetterGenerator

    def search_jobs(self, query: str, page_size: int = 10, page: int = 1):
        from ..models import JobSearchRequest

        return self.repository.search(
            JobSearchRequest(query=query, limit=page_size, page=page, page_size=page_size)
        )

    def analyze_resume(self, resume_text: str):
        return analyze_resume_text(resume_text)

    def match_resume_to_job(self, resume_text: str):
        return self.repository.match_resume(resume_text)

    def find_sponsorship_jobs(self, query: str = "visa sponsorship", limit: int = 10):
        results = self.search_jobs(query=query, page_size=limit, page=1)
        return [result for result in results.items if result.job.visa_sponsorship]

    def generate_cover_letter(self, resume_text: str, job_title: str, company: str) -> str:
        return self.cover_letter_generator.generate(
            resume_text=resume_text,
            job_title=job_title,
            company=company,
        )

    def app_info(self) -> AppInfo:
        return AppInfo()
