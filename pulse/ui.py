"""Shared Streamlit setup: page config, sidebar, session state, small widgets."""

from __future__ import annotations

import html
import os

import streamlit as st

from pulse import data
from pulse.audit import AuditLog
from pulse.brief import Review, lab_claim_issue
from pulse.grounding import all_grounded
from pulse.models import AIStatus, Analysis, SelfStatus

# Change this to your own repository address after you upload the code.
REPO_URL = "https://github.com/Qureshiam/iaq-program-pulse"

# Status colors are reserved for status only, and always shown with an icon and a word.
STATUS_STYLE = {
    AIStatus.on_track: ("●", "On track", "#0ca30c"),
    AIStatus.at_risk: ("▲", "At risk", "#c98500"),
    AIStatus.off_track: ("■", "Off track", "#d03b3b"),
}
SELF_STYLE = {
    SelfStatus.green: ("●", "Green", "#0ca30c"),
    SelfStatus.amber: ("▲", "Amber", "#c98500"),
    SelfStatus.red: ("■", "Red", "#d03b3b"),
}

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
table {font-size: .92rem;}
td, th {vertical-align: top; padding: 8px 10px !important;}
.pill {display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.85rem;
       font-weight:600; border:1.5px solid currentColor; white-space:nowrap;}
.card {border:1px solid rgba(128,128,128,.25); border-radius:10px; padding:14px 16px; margin-bottom:10px;}
.muted {opacity:.7; font-size:.88rem;}
.quote {border-left:3px solid rgba(128,128,128,.5); padding:2px 10px; margin:6px 0; font-style:italic;}
mark {background: rgba(250,178,25,.35); padding:0 2px; border-radius:3px; color: inherit;}
.flag {font-size:.85rem; padding:6px 10px; border-radius:8px; margin:4px 0;
       background: rgba(208,59,59,.08); border-left:3px solid #d03b3b;}
.flag.medium {background: rgba(201,133,0,.08); border-left-color:#c98500;}
</style>
"""


def pill(icon: str, label: str, color: str) -> str:
    return f'<span class="pill" style="color:{color}">{icon} {html.escape(label)}</span>'


def ai_pill(status: AIStatus) -> str:
    return pill(*STATUS_STYLE[status])


def self_pill(status: SelfStatus) -> str:
    return pill(*SELF_STYLE[status])


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file is fine
        key = None
    return key or os.getenv("ANTHROPIC_API_KEY")


def init_state() -> None:
    """Load data once per browser session and seed the audit log."""
    if "ready" in st.session_state:
        return
    ss = st.session_state
    ss.company = data.load_company()
    ss.programs = {p.id: p for p in data.load_programs()}
    ss.updates = data.load_updates()
    ss.updates_by_id = {u.id: u for u in ss.updates}
    ss.analyses = data.load_demo_analyses()
    ss.brief = data.load_demo_brief()
    ss.reviews = {item.id: Review("pending", item.text) for item in ss.brief.items}
    ss.reviewed_programs = set()
    ss.audit = AuditLog()
    for a in ss.analyses.values():
        _log_new_analysis(a)
    for item in ss.brief.items:
        ss.audit.record(
            action="ai_suggested",
            item_id=item.id,
            actor="AI",
            after=item.text,
            detail="Brief item drafted",
            model=ss.brief.model,
            prompt_version=ss.brief.prompt_version,
        )
        log_lab_claim(item)
    ss.ready = True


def log_lab_claim(item) -> None:
    if lab_claim_issue(item.text):
        st.session_state.audit.record(
            action="lab_claim_flagged",
            item_id=item.id,
            actor="System",
            detail="Brief line uses a lab-style figure as a customer result",
        )


def _log_new_analysis(a: Analysis) -> None:
    ss = st.session_state
    update = ss.updates_by_id.get(a.update_id)
    ss.audit.record(
        action="ai_suggested",
        item_id=a.update_id,
        actor="AI",
        after=f"{a.status.value}: {a.reason}",
        detail="Update analyzed",
        model=a.model,
        prompt_version=a.prompt_version,
    )
    if update and not all_grounded(a, update.text):
        ss.audit.record(
            action="grounding_failed",
            item_id=a.update_id,
            actor="System",
            detail="At least one quote was not found in the source update",
            model=a.model,
            prompt_version=a.prompt_version,
        )


def store_analysis(a: Analysis) -> None:
    """Save a fresh (live) analysis and reset its review state."""
    ss = st.session_state
    ss.analyses[a.update_id] = a
    program_id = ss.updates_by_id[a.update_id].program_id
    ss.reviewed_programs.discard(program_id)
    _log_new_analysis(a)


def ungrounded_programs() -> set[str]:
    """Programs whose latest analysis has an unsupported quote and nobody has reviewed it yet."""
    ss = st.session_state
    out = set()
    for pid, upd in data.latest_update_per_program(ss.updates).items():
        a = ss.analyses.get(upd.id)
        if a and not all_grounded(a, upd.text) and pid not in ss.reviewed_programs:
            out.add(pid)
    return out


def setup_page() -> None:
    st.set_page_config(page_title="Program Pulse", page_icon="🌬️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    ss = st.session_state
    with st.sidebar:
        st.markdown(f"### {ss.company['name']}")
        st.caption("Fictional company. All data is synthetic.")
        ss.reviewer = st.text_input(
            "Reviewer name",
            value=ss.get("reviewer", "Program lead"),
            help="Recorded in the audit log when you approve or edit AI output.",
        )
        has_key = bool(get_api_key())
        live = st.toggle(
            "Live AI",
            value=ss.get("live", False),
            disabled=not has_key,
            help="Call the Claude API instead of using saved demo outputs.",
        )
        ss.live = live and has_key
        if not has_key:
            st.caption("Demo mode: showing saved AI outputs. Add an API key to turn on live AI.")
        st.divider()
        flagged = ungrounded_programs()
        if flagged:
            st.warning(f"{len(flagged)} AI analysis needs review before it can reach the brief.", icon="⚠️")
        st.caption(f"Built by Mateen Qureshi · [Source code]({REPO_URL})")


def status_counts() -> dict[AIStatus, int]:
    ss = st.session_state
    counts = {s: 0 for s in AIStatus}
    for upd in data.latest_update_per_program(ss.updates).values():
        a = ss.analyses.get(upd.id)
        if a:
            counts[a.status] += 1
    return counts
