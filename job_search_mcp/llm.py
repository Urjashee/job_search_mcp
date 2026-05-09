from __future__ import annotations

from dataclasses import dataclass

from .models import AppInfo


@dataclass(slots=True)
class CoverLetterGenerator:
    api_key: str | None = None
    model: str = "gpt-4o-mini"

    @classmethod
    def from_settings(cls, api_key: str | None, model: str) -> "CoverLetterGenerator":
        return cls(api_key=api_key, model=model)

    def generate(self, resume_text: str, job_title: str, company: str) -> str:
        if not self.api_key:
            return self._fallback(resume_text=resume_text, job_title=job_title, company=company)

        try:
            from openai import OpenAI  # type: ignore[import-not-found]
        except Exception:
            return self._fallback(resume_text=resume_text, job_title=job_title, company=company)

        client = OpenAI(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Write a concise, professional cover letter using the supplied resume "
                            "signals and target job details."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Resume:\n{resume_text}\n\n"
                            f"Target job: {job_title} at {company}\n"
                            "Draft a short cover letter."
                        ),
                    },
                ],
                temperature=0.4,
            )
        except Exception:
            return self._fallback(resume_text=resume_text, job_title=job_title, company=company)

        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else self._fallback(resume_text, job_title, company)

    def _fallback(self, resume_text: str, job_title: str, company: str) -> str:
        lower = resume_text.lower()
        skills = [
            keyword
            for keyword in ("python", "fastapi", "rag", "mcp", "openai", "sql", "docker")
            if keyword in lower
        ]
        skill_text = ", ".join(skills[:4]) if skills else "relevant experience"
        return (
            f"Dear hiring team at {company},\n\n"
            f"I am excited to apply for the {job_title} role. "
            f"My background includes {skill_text}, and I would welcome the opportunity to "
            f"contribute to your team.\n\nSincerely,\nA candidate"
        )
