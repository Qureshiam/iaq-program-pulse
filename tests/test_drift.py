"""Each drift rule fires when it should and stays quiet when it should not."""

from datetime import date

from pulse import data
from pulse.drift import all_flags, missing_update, past_target, stalled_progress, status_mismatch, stuck_language
from pulse.models import AIStatus, Analysis, Program, Update

PROGRAM = Program(id="X", name="Test", owner="A", goal="g", start_date=date(2026, 9, 1), target_date=date(2026, 10, 1))


def upd(week: int, pct: int, text: str = "Progress made.", status: str = "green") -> Update:
    return Update(
        id=f"X-{week}",
        program_id="X",
        week_ending=date(2026, 9, week),
        author="A",
        self_status=status,
        percent_complete=pct,
        text=text,
    )


def test_stalled_fires_on_three_flat_weeks():
    assert stalled_progress(PROGRAM, [upd(3, 50), upd(10, 50), upd(17, 50)])


def test_stalled_quiet_when_moving_or_finished():
    assert not stalled_progress(PROGRAM, [upd(3, 50), upd(10, 55), upd(17, 60)])
    assert not stalled_progress(PROGRAM, [upd(3, 100), upd(10, 100), upd(17, 100)])


def test_almost_done_loop():
    ups = [upd(3, 80, "Almost done."), upd(10, 85, "Final stages now."), upd(17, 85, "nearly complete")]
    assert stuck_language(PROGRAM, ups)
    assert not stuck_language(PROGRAM, ups[:2] + [upd(17, 85, "Live in production.")])


def test_past_target():
    assert past_target(PROGRAM, [upd(17, 60)], today=date(2026, 10, 15))
    assert not past_target(PROGRAM, [upd(17, 60)], today=date(2026, 9, 20))


def test_missing_update():
    assert missing_update(PROGRAM, [upd(10, 60)], today=date(2026, 9, 17))
    assert not missing_update(PROGRAM, [upd(17, 60)], today=date(2026, 9, 17))


def test_watermelon_green_report_with_risky_text():
    a = Analysis(update_id="X-17", status=AIStatus.at_risk, reason="r", status_evidence="e")
    assert status_mismatch(PROGRAM, a, upd(17, 60, status="green"))
    assert not status_mismatch(PROGRAM, a, upd(17, 60, status="amber"))


def test_demo_data_flags(programs, updates, analyses):
    flags = all_flags(list(programs.values()), updates, analyses, data.reporting_week(updates))
    kinds = {(f.program_id, f.kind) for f in flags}
    assert ("ERP", "stalled") in kinds
    assert ("ERP", "stuck_language") in kinds
    assert ("SCHL", "status_mismatch") in kinds
    assert ("HIRE", "missing_update") in kinds
    assert not any(pid == "ASMT" for pid, _ in kinds)
