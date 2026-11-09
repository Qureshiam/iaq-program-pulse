"""End-to-end smoke tests of the Streamlit app in demo mode."""

import pytest
from streamlit.testing.v1 import AppTest

PAGES = [
    "views/portfolio.py",
    "views/program_detail.py",
    "views/risks_decisions.py",
    "views/weekly_brief.py",
    "views/impact.py",
    "views/audit_log.py",
]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return AppTest.from_file("../streamlit_app.py", default_timeout=30).run()


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_errors(app, page):
    app.switch_page(page).run()
    assert not app.exception


def test_review_unlocks_brief_lines(app):
    app.switch_page("views/program_detail.py").run()
    app.selectbox[0].select("Investor update pack (Q3)").run()
    assert app.error, "expected the grounding warning on the investor update analysis"
    next(b for b in app.button if b.label == "Remove unsupported items").click().run()
    assert "INV" in app.session_state.reviewed_programs
    assert app.session_state.audit.has("edited", "INV-2026-10-15")

    app.switch_page("views/weekly_brief.py").run()
    next(b for b in app.button if b.label.startswith("Approve all")).click().run()
    states = {k: r.state for k, r in app.session_state.reviews.items()}
    assert states.pop("B4") == "pending", "the lab-figure line must not be bulk approved"
    assert all(s == "approved" for s in states.values())


def test_lab_figure_line_needs_a_rewrite(app):
    app.switch_page("views/weekly_brief.py").run()
    assert app.session_state.audit.has("lab_claim_flagged", "B4")
    assert next(b for b in app.button if b.key == "ok_B4").disabled
    next(b for b in app.button if b.key == "ed_B4").click().run()
    app.text_area(key="edit_B4").input("Assessment service v2: live; field results show a 77% median mold cut.").run()
    next(b for b in app.button if b.key == "save_B4").click().run()
    assert app.session_state.reviews["B4"].state == "edited"
