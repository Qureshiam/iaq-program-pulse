"""Only approved lines reach the brief, and every action is logged."""

from datetime import date

import pytest

from pulse import data
from pulse.audit import AuditLog
from pulse.brief import Review, is_locked, lab_claim_issue, render_markdown


def test_only_approved_or_edited_lines_are_exported():
    brief = data.load_demo_brief()
    first, second, third = brief.items[:3]
    reviews = {
        first.id: Review("approved", first.text),
        second.id: Review("edited", "Edited line."),
        third.id: Review("rejected", third.text),
    }
    md = render_markdown(brief, reviews, "Clearwell Air", date(2026, 10, 15), "Tester")
    assert first.text in md and "Edited line." in md
    assert third.text not in md
    assert f"{len(brief.items) - 3} drafted item(s) were not reviewed" in md
    assert "Reviewed and approved by Tester" in md


def test_lines_tied_to_unchecked_analysis_are_locked():
    brief = data.load_demo_brief()
    locked = [i.id for i in brief.items if is_locked(i, {"INV"})]
    assert "B8" in locked and "B11" in locked and "B2" not in locked


def test_audit_rejects_unknown_actions():
    with pytest.raises(ValueError):
        AuditLog().record(action="deleted_evidence", item_id="x", actor="y")


def test_audit_summary_and_export():
    log = AuditLog()
    log.record(action="ai_suggested", item_id="B1", actor="AI")
    log.record(action="approved", item_id="B1", actor="Reviewer")
    assert log.summary() == {"ai_suggested": 1, "approved": 1}
    assert log.has("approved", "B1")
    assert log.to_jsonl().count("\n") == 1


@pytest.mark.parametrize(
    "line",
    [
        "Our units remove 99.99% of mold at customer sites.",
        "Kills 99.9 % of bacteria in homes.",
        "A 4-log reduction in spores across the school.",
        "Cuts viruses within 3 minutes in every office.",
    ],
)
def test_lab_style_figures_are_flagged(line):
    assert lab_claim_issue(line)


@pytest.mark.parametrize(
    "line",
    [
        "Field assessments show a median 77% cut in airborne mold across 9 sites.",
        "Lab results report 99.99% in a sealed chamber; our field median is 77%.",
        "Report turnaround is down to 4 days from 9.",
    ],
)
def test_field_results_and_labelled_lab_figures_pass(line):
    assert lab_claim_issue(line) is None


def test_demo_brief_has_exactly_one_lab_claim():
    brief = data.load_demo_brief()
    assert [i.id for i in brief.items if lab_claim_issue(i.text)] == ["B4"]
