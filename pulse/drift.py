"""Plain rules that spot programs drifting, no AI involved.

These checks are deliberately simple and explainable. They run on the
history of updates, which the AI does not see as a whole, and they catch
the patterns a PMO lead learns to look for:

* the same percent complete week after week
* "almost done" three updates in a row
* a target date that has passed
* a program that went quiet
* a green self-report that the text does not support (a "watermelon":
  green outside, red inside)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from pulse.models import AIStatus, Analysis, Program, SelfStatus, Update

STUCK_PHRASES = re.compile(r"\b(almost done|nearly (done|there|complete)|final stages?|wrapping up)\b", re.I)
STREAK = 3


@dataclass
class Flag:
    program_id: str
    kind: str
    label: str
    detail: str
    severity: str  # "high" | "medium"


def _program_updates(program_id: str, updates: list[Update]) -> list[Update]:
    return sorted((u for u in updates if u.program_id == program_id), key=lambda u: u.week_ending)


def stalled_progress(program: Program, updates: list[Update]) -> Flag | None:
    hist = _program_updates(program.id, updates)[-STREAK:]
    if len(hist) == STREAK and hist[-1].percent_complete < 100:
        if len({u.percent_complete for u in hist}) == 1:
            return Flag(
                program.id,
                "stalled",
                "Progress stalled",
                f"Reported {hist[-1].percent_complete}% complete for {STREAK} weeks running.",
                "high",
            )
    return None


def stuck_language(program: Program, updates: list[Update]) -> Flag | None:
    hist = _program_updates(program.id, updates)[-STREAK:]
    if len(hist) == STREAK and all(STUCK_PHRASES.search(u.text) for u in hist):
        return Flag(
            program.id,
            "stuck_language",
            '"Almost done" loop',
            f'The last {STREAK} updates all say some version of "almost done".',
            "medium",
        )
    return None


def past_target(program: Program, updates: list[Update], today: date) -> Flag | None:
    hist = _program_updates(program.id, updates)
    if hist and today > program.target_date and hist[-1].percent_complete < 100:
        days = (today - program.target_date).days
        return Flag(
            program.id,
            "past_target",
            "Past target date",
            f"Target was {program.target_date:%d %b}; {days} days late at {hist[-1].percent_complete}%.",
            "high",
        )
    return None


def missing_update(program: Program, updates: list[Update], today: date) -> Flag | None:
    hist = _program_updates(program.id, updates)
    if not hist or hist[-1].week_ending < today:
        last = f"{hist[-1].week_ending:%d %b}" if hist else "never"
        return Flag(program.id, "missing_update", "No update this week", f"Last update: {last}.", "medium")
    return None


def status_mismatch(program: Program, analysis: Analysis | None, latest: Update | None) -> Flag | None:
    if not analysis or not latest:
        return None
    if latest.self_status == SelfStatus.green and analysis.status != AIStatus.on_track:
        return Flag(
            program.id,
            "status_mismatch",
            "Green report, risky text",
            f"Owner reported green, but the update reads as {analysis.status.value.replace('_', ' ')}.",
            "high",
        )
    return None


def all_flags(programs: list[Program], updates: list[Update], analyses: dict[str, Analysis], today: date) -> list[Flag]:
    flags: list[Flag] = []
    for p in programs:
        hist = _program_updates(p.id, updates)
        latest = hist[-1] if hist else None
        analysis = analyses.get(latest.id) if latest else None
        for check in (
            stalled_progress(p, updates),
            stuck_language(p, updates),
            past_target(p, updates, today),
            missing_update(p, updates, today),
            status_mismatch(p, analysis, latest),
        ):
            if check:
                flags.append(check)
    return flags
