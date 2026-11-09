"""Build the final founder and board brief from the items a person approved.

Nothing the AI drafted reaches the exported brief unless a reviewer approved
it (as written or edited). Items that lean on an analysis which failed the
grounding check are locked until that analysis has been reviewed. Lines that
present lab test figures as customer results must be edited before approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from pulse.models import Brief, BriefItem

SECTION_TITLES = {"headline": "This week", "program": "Programs", "ask": "Decisions needed"}


@dataclass
class Review:
    state: str  # "pending" | "approved" | "edited" | "rejected"
    text: str


def is_locked(item: BriefItem, ungrounded_program_ids: set[str]) -> bool:
    return bool(set(item.program_ids) & ungrounded_program_ids)


# Lab results (sealed test chambers, single pathogens, fixed times) look like
# "99.99%", "4-log" or "in 60 minutes". Field results in occupied rooms are
# lower. A board or investor line that uses lab-style figures must be
# rewritten or clearly labelled before it can be approved.
LAB_CLAIM = re.compile(
    r"\b99(\.9+)?\s?%|\b\d-log\b|\blog reduction\b|\b(lab|laboratory)\b|\bwithin \d+ minutes\b",
    re.I,
)
LAB_LABEL = re.compile(r"\b(lab|laboratory) (result|test|figure)s?\b", re.I)


def lab_claim_issue(text: str) -> str | None:
    """Return a warning when a line looks like a lab figure presented as a customer result."""
    if LAB_CLAIM.search(text) and not LAB_LABEL.search(text):
        return (
            "This line uses a lab-style figure. Customer results must come from our own field "
            "assessments, or the figure must be labelled as a lab result."
        )
    return None


def render_markdown(
    brief: Brief, reviews: dict[str, Review], company_name: str, week_ending: date, reviewer: str
) -> str:
    lines = [f"# {company_name}: weekly brief", f"Week ending {week_ending:%d %B %Y}", ""]
    pending = 0
    for section, title in SECTION_TITLES.items():
        approved = []
        for item in (i for i in brief.items if i.section == section):
            review = reviews.get(item.id, Review("pending", item.text))
            if review.state in ("approved", "edited"):
                approved.append(review.text)
            elif review.state == "pending":
                pending += 1
        if approved:
            lines.append(f"## {title}")
            lines += [f"- {t}" for t in approved]
            lines.append("")
    lines.append("---")
    lines.append(
        f"Drafted with AI ({brief.model}, prompt {brief.prompt_version}). Reviewed and approved by {reviewer}."
    )
    if pending:
        lines.append(f"{pending} drafted item(s) were not reviewed and are not included.")
    return "\n".join(lines)
