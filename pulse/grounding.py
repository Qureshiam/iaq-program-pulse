"""Grounding check: every AI claim must point at real words in the source update.

The AI is asked to back each status, risk and decision with an exact quote.
This module checks that the quote actually appears in the update. If it does
not, the item is flagged and kept out of the founder brief until a person
looks at it. This is the main guard against the AI making things up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pulse.models import Analysis

_SMART_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _normalize(text: str) -> str:
    text = text.translate(_SMART_QUOTES).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .\"'")


def is_grounded(evidence: str, source_text: str) -> bool:
    """True when the evidence quote appears in the source (ignoring case, spacing, quote style)."""
    quote = _normalize(evidence)
    if len(quote) < 8:  # very short quotes prove nothing
        return False
    return quote in _normalize(source_text)


@dataclass
class GroundingResult:
    item: str  # "status", "risk 1", "decision 2"...
    evidence: str
    grounded: bool


def check_analysis(analysis: Analysis, source_text: str) -> list[GroundingResult]:
    results = [GroundingResult("status", analysis.status_evidence, is_grounded(analysis.status_evidence, source_text))]
    for i, r in enumerate(analysis.risks, start=1):
        results.append(GroundingResult(f"risk {i}", r.evidence, is_grounded(r.evidence, source_text)))
    for i, d in enumerate(analysis.decisions, start=1):
        results.append(GroundingResult(f"decision {i}", d.evidence, is_grounded(d.evidence, source_text)))
    return results


def all_grounded(analysis: Analysis, source_text: str) -> bool:
    return all(r.grounded for r in check_analysis(analysis, source_text))
