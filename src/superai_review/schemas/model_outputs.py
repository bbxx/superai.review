from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReviewVerdict(StrEnum):
    APPROVE = "APPROVE"
    CHANGES = "CHANGES"
    BLOCKED = "BLOCKED"


class ProposalOutput(StrictOutput):
    schema_version: Literal["proposal-output/v1"]
    proposal_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    summary: str
    recommended_solution: str
    reasoning_summary: str
    key_claims: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ReviewIssue(StrictOutput):
    severity: Severity
    message: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class CrossReviewOutput(StrictOutput):
    schema_version: Literal["cross-review/v1"]
    review_id: str = Field(min_length=1)
    reviewer_role: str = Field(min_length=1)
    target_proposal_id: str = Field(min_length=1)
    verdict: ReviewVerdict
    strengths: list[str] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    evidence_disagreements: list[str] = Field(default_factory=list)
    recommended_changes: list[str] = Field(default_factory=list)
    severity_summary: Severity


class DebateResponseOutput(StrictOutput):
    schema_version: Literal["debate-response/v1"]
    topic_id: str = Field(min_length=1)
    participant_role: str = Field(min_length=1)
    position: str
    reasoning_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    changed_position: bool
    unresolved_points: list[str] = Field(default_factory=list)


class FinalSynthesisOutput(StrictOutput):
    schema_version: Literal["final-synthesis/v1"]
    final_answer: str
    executive_summary: str
    why_this_answer: list[str] = Field(default_factory=list)
    key_evidence: list[str] = Field(default_factory=list)
    rejected_or_avoided_points: list[str] = Field(default_factory=list)
    remaining_uncertainties: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    consensus_summary: str
    quality_flags: list[str] = Field(default_factory=list)
