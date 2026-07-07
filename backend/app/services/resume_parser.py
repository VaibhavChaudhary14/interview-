import re
import logging
import pdfplumber
import spacy
from typing import IO

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "fastapi", "django", "flask", "spring", "express", "next.js", "react",
    "git", "ci/cd", "pytest", "jest",
}

TECHNOLOGY_KEYWORDS = {
    "rest api", "graphql", "grpc", "message queue", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "computer vision",
    "agile", "scrum", "microservices", "serverless",
}

DOMAIN_KEYWORDS = {
    "backend", "frontend", "full stack", "data science", "devops",
    "distributed systems", "system design", "cloud computing",
    "cybersecurity", "mobile development",
}


class ResumeParserService:
    def parse(self, file: IO[bytes]) -> dict:
        raw_text = self._extract_text(file)
        if not raw_text.strip():
            raise ValueError("Empty or unparsable resume text")

        skills = self._extract_skills(raw_text)
        technologies = self._extract_technologies(raw_text)
        domains = self._extract_domains(raw_text)
        years = self._estimate_years(raw_text)

        return {
            "raw_text": raw_text,
            "extracted_skills": skills,
            "extracted_technologies": technologies,
            "extracted_domains": domains,
            "years_experience_estimate": years,
        }

    def _extract_text(self, file: IO[bytes]) -> str:
        content = file.read()
        if isinstance(content, bytes):
            try:
                import pdfplumber
                import io
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    return " ".join(page.extract_text() or "" for page in pdf.pages)
            except Exception:
                pass
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1")
        return str(content)

    def _extract_skills(self, text: str) -> list[str]:
        lower = text.lower()
        found = set()
        for skill in SKILL_KEYWORDS:
            if skill in lower:
                found.add(skill)
        return sorted(found)

    def _extract_technologies(self, text: str) -> list[str]:
        lower = text.lower()
        found = set()
        for tech in TECHNOLOGY_KEYWORDS:
            if tech in lower:
                found.add(tech)
        return sorted(found)

    def _extract_domains(self, text: str) -> list[str]:
        lower = text.lower()
        found = set()
        for domain in DOMAIN_KEYWORDS:
            if domain in lower:
                found.add(domain)
        return sorted(found)

    def _estimate_years(self, text: str) -> int:
        patterns = [
            r"(\d+)\+?\s*years?\s*(?:of)?\s*experience",
            r"experience\s*(?:of\s*)?(\d+)\+?\s*years?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0
