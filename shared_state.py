"""Shared state models used by all agents in the research pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Source & Evidence ────────────────────────────────────────────────────────

class Source(BaseModel):
    """A single retrieved source."""
    title: str
    url: str
    accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    credibility_notes: str = ""
    snippet: str = ""  # raw text extracted from the page


class Evidence(BaseModel):
    """An evidence fragment extracted from a source."""
    claim: str
    source_index: int  # index into SharedState.sources
    quote: str = ""  # supporting quote from the source
    relevance: str = ""  # short note on why this matters


# ── Synthesis models ─────────────────────────────────────────────────────────

class Theme(BaseModel):
    """A thematic grouping produced by the SynthesisAgent."""
    name: str
    summary: str
    evidence_indices: list[int] = Field(default_factory=list)  # indices into SharedState.evidence
    confidence: Confidence = Confidence.MEDIUM


class Contradiction(BaseModel):
    """A disagreement identified across sources."""
    description: str
    evidence_indices: list[int] = Field(default_factory=list)
    resolution: str = ""  # how the system chose to handle it


# ── Evaluation ───────────────────────────────────────────────────────────────

class EvaluationScores(BaseModel):
    coverage: float = Field(0.0, ge=0, le=1, description="Did the report address key parts of the question?")
    faithfulness: float = Field(0.0, ge=0, le=1, description="Are claims supported by evidence?")
    hallucination_rate: float = Field(0.0, ge=0, le=1, description="Proportion of unsupported/overstated claims.")
    usefulness: float = Field(0.0, ge=0, le=1, description="Is the output clear, relevant, decision-supportive?")
    reasoning: str = ""


# ── Shared State ─────────────────────────────────────────────────────────────

class SharedState(BaseModel):
    """Central state object shared across all agents."""

    # Input
    research_question: str = ""

    # SearchAgent outputs
    search_queries: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    # SynthesisAgent outputs
    themes: list[Theme] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)

    # ReportAgent outputs
    report_outline: list[str] = Field(default_factory=list)
    final_report: str = ""

    # Evaluation
    evaluation: Optional[EvaluationScores] = None

    # Metadata
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""

    def summary(self) -> str:
        """Human-readable summary of the current state."""
        lines = [
            f"Research Question: {self.research_question}",
            f"Search Queries:    {len(self.search_queries)}",
            f"Sources:           {len(self.sources)}",
            f"Evidence:          {len(self.evidence)}",
            f"Themes:            {len(self.themes)}",
            f"Contradictions:    {len(self.contradictions)}",
            f"Report length:     {len(self.final_report)} chars",
            f"Evaluated:         {self.evaluation is not None}",
        ]
        return "\n".join(lines)
