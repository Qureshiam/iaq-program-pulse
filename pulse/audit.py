"""Audit trail of what the AI suggested and what a person did with it.

Each entry records who acted, on what, the before and after text, and which
model and prompt version produced the suggestion. In the hosted demo the log
lives for the length of your browser session and can be downloaded as JSON
lines. A real deployment would write the same entries to a database.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

ACTIONS = {"ai_suggested", "approved", "edited", "rejected", "grounding_failed", "lab_claim_flagged", "exported"}


@dataclass
class AuditEntry:
    action: str
    item_id: str
    actor: str
    detail: str = ""
    before: str | None = None
    after: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    def __post_init__(self):
        if self.action not in ACTIONS:
            raise ValueError(f"Unknown audit action: {self.action}")


class AuditLog:
    def __init__(self, entries: list[AuditEntry] | None = None):
        self.entries: list[AuditEntry] = entries if entries is not None else []

    def record(self, **kwargs) -> AuditEntry:
        entry = AuditEntry(**kwargs)
        self.entries.append(entry)
        return entry

    def has(self, action: str, item_id: str) -> bool:
        return any(e.action == action and e.item_id == item_id for e in self.entries)

    def to_rows(self) -> list[dict]:
        return [asdict(e) for e in self.entries]

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(row) for row in self.to_rows())

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.entries:
            counts[e.action] = counts.get(e.action, 0) + 1
        return counts
