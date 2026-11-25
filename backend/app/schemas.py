"""Request and response models: the REST API contract published as OpenAPI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["queued", "running", "completed", "partial", "failed"]


class AnalysisRequest(BaseModel):
    repo_url: str = Field(..., max_length=200, examples=["https://github.com/pallets/itsdangerous"])


class AnalysisCreated(BaseModel):
    id: str
    status: Status


class CharacteristicScore(BaseModel):
    value: float | None
    details: dict[str, float]


class ToolRun(BaseModel):
    tool: str
    version: str
    ok: bool
    error: str | None = None
    findings: int


class Analysis(BaseModel):
    id: str
    repo_url: str
    status: Status
    commit_sha: str | None = None
    grade: str | None = None
    overall: float | None = None
    scores: dict[str, CharacteristicScore] | None = None
    tools: list[ToolRun] | None = None
    stats: dict[str, int] | None = None
    error: str | None = None
    created_at: str
    finished_at: str | None = None


class FindingOut(BaseModel):
    tool: str
    rule_id: str
    characteristic: Literal["maintainability", "security", "reliability"]
    severity: Literal["low", "medium", "high"]
    file: str
    line: int
    message: str
    snippet: str


class ErrorOut(BaseModel):
    detail: str
