from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


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


@dataclass(frozen=True)
class ResearchAnswerPoint:
    claim: str
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""
    reason: str = ""


@dataclass(frozen=True)
class ResearchAnswer:
    path: Path
    question: str
    research_artifact_path: Path
    title: str
    channel: str
    topic: str
    summary_answer: str = ""
    direct_mentions: list[ResearchAnswerPoint] = field(default_factory=list)
    inferred_points: list[ResearchAnswerPoint] = field(default_factory=list)
    needs_validation: list[ResearchAnswerPoint] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    notes: str = ""


OpportunityRoute = Literal["prediction_market", "us_equity", "tw_equity", "macro_only", "no_trade"]


@dataclass(frozen=True)
class OpportunityRoutingResult:
    research_answer_path: Path
    route: OpportunityRoute
    rationale: str
    supporting_claims: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
