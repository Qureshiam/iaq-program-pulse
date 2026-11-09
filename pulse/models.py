"""Data shapes used across the app.

Pydantic checks every record when it is loaded, so a bad row in the data
files (or a malformed AI response) fails loudly instead of quietly showing
wrong numbers on screen.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class SelfStatus(StrEnum):
    """What the program owner reported (the traditional RAG status)."""

    green = "green"
    amber = "amber"
    red = "red"


class AIStatus(StrEnum):
    """What the AI read from the text of the update."""

    on_track = "on_track"
    at_risk = "at_risk"
    off_track = "off_track"


class Severity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class Program(BaseModel):
    id: str
    name: str
    owner: str
    goal: str
    start_date: date
    target_date: date


class Update(BaseModel):
    id: str
    program_id: str
    week_ending: date
    author: str
    self_status: SelfStatus
    percent_complete: int = Field(ge=0, le=100)
    text: str


class Risk(BaseModel):
    description: str
    severity: Severity
    owner: str | None = None
    evidence: str = Field(description="Exact quote from the update that supports this risk")


class Decision(BaseModel):
    description: str
    needed_by: str | None = None
    evidence: str = Field(description="Exact quote from the update that supports this decision")


class Analysis(BaseModel):
    """The AI's reading of one weekly update."""

    update_id: str
    status: AIStatus
    reason: str
    status_evidence: str
    risks: list[Risk] = []
    decisions: list[Decision] = []
    confidence: Severity = Severity.medium
    model: str = "demo"
    prompt_version: str = "v1"


class BriefItem(BaseModel):
    id: str
    section: str  # "headline", "program", "ask"
    text: str
    program_ids: list[str] = []


class Brief(BaseModel):
    week_ending: date
    items: list[BriefItem]
    model: str = "demo"
    prompt_version: str = "v1"
