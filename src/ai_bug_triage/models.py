from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Severity(str, Enum):
    blocker = "blocker"
    critical = "critical"
    major = "major"
    minor = "minor"
    cosmetic = "cosmetic"
    unknown = "unknown"


class Priority(str, Enum):
    p0 = "P0"
    p1 = "P1"
    p2 = "P2"
    p3 = "P3"
    unknown = "unknown"


class DataSensitivity(str, Enum):
    public = "public"
    internal = "internal"
    personal = "personal"
    secret = "secret"
    unknown = "unknown"


class RecommendedAction(str, Enum):
    request_information = "request_information"
    investigate = "investigate"
    security_review = "security_review"
    compare_duplicate = "compare_duplicate"
    defer = "defer"


class BugReport(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=20_000)
    steps_to_reproduce: list[str] = Field(default_factory=list, max_length=30)
    expected_behavior: str = Field(default="", max_length=5_000)
    actual_behavior: str = Field(default="", max_length=5_000)
    environment: str = Field(default="", max_length=2_000)


class TriageResult(StrictModel):
    summary: str = Field(min_length=1, max_length=800)
    category: str = Field(min_length=1, max_length=80)
    severity: Severity
    priority: Priority
    recommended_action: RecommendedAction
    suggested_labels: list[str] = Field(max_length=10)
    missing_information: list[str] = Field(max_length=12)
    follow_up_questions: list[str] = Field(max_length=8)
    duplicate_likelihood: float = Field(ge=0, le=1)
    possible_duplicate_ids: list[str] = Field(max_length=10)
    data_sensitivity: DataSensitivity
    prompt_injection_detected: bool
    secret_exposure_suspected: bool
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=1_500)
    human_review_required: Literal[True]


class LedgerEntry(StrictModel):
    run_id: str
    created_at: str
    bug_id: str
    input_sha256: str
    model: str
    prompt_version: str
    api_response_id: str | None = None
    result: TriageResult
    human_verdict: Literal["accepted", "edited", "rejected"] | None = None
    human_notes: str | None = None
