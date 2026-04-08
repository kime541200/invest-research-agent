from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ResearchEvidence:
    title: str
    source: str
    summary: str = ""
    url: str = ""
    published_at: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class ResearchClaim:
    text: str
    keywords: list[str] = field(default_factory=list)
    evidence: list[ResearchEvidence] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FollowUpQuestion:
    question: str
    rationale: str = ""


@dataclass(frozen=True)
class ResearchNoteSections:
    core_conclusion: str = ""
    key_points: list[str] = field(default_factory=list)
    answered_questions: list[str] = field(default_factory=list)
    evidence_points: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedNote:
    path: Path
    title: str
    topic: str = ""
    channel: str = ""
    content: str = ""


@dataclass(frozen=True)
class ResearchEnrichmentResult:
    note_path: Path
    note_title: str
    keywords: list[str] = field(default_factory=list)
    evidence: list[ResearchEvidence] = field(default_factory=list)
