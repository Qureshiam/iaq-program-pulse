"""Program detail: the raw update, the AI's reading, and the proof behind each line."""

import html
import re

import altair as alt
import pandas as pd
import streamlit as st

from pulse import ai, ui
from pulse.grounding import check_analysis, is_grounded
from pulse.models import SelfStatus, Update

ss = st.session_state
names = {p.name: pid for pid, p in ss.programs.items()}
default = list(names).index(ss.programs[ss.get("selected_program", "SCHL")].name)
choice = st.selectbox("Program", list(names), index=default)
pid = names[choice]
ss.selected_program = pid
program = ss.programs[pid]
history = [u for u in ss.updates if u.program_id == pid]
latest = history[-1]
analysis = ss.analyses.get(latest.id)


def highlight(text: str, quotes: list[str]) -> str:
    """Return HTML of the text with each supported quote marked."""
    spans = []
    for q in quotes:
        pattern = r"\s+".join(re.escape(w) for w in q.strip(" .\"'").split())
        m = re.search(pattern, text, re.I)
        if m:
            spans.append((m.start(), m.end()))
    spans.sort()
    out, pos = [], 0
    for start, end in spans:
        if start < pos:
            continue
        out += [html.escape(text[pos:start]), f"<mark>{html.escape(text[start:end])}</mark>"]
        pos = end
    out.append(html.escape(text[pos:]))
    return "".join(out)


def badge(ok: bool) -> str:
    return "✅ quote found in update" if ok else "⚠️ quote NOT found in update"


st.title(program.name)
st.markdown(f"**Owner:** {program.owner} · **Target:** {program.target_date:%d %b %Y}  \n**Goal:** {program.goal}")

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader(f"Update for week ending {latest.week_ending:%d %b}")
    st.markdown(
        f"Owner reported {ui.self_pill(latest.self_status)} · {latest.percent_complete}% done", unsafe_allow_html=True
    )
    quotes = []
    if analysis:
        checks = check_analysis(analysis, latest.text)
        quotes = [c.evidence for c in checks if c.grounded]
    st.markdown(f'<div class="card">{highlight(latest.text, quotes)}</div>', unsafe_allow_html=True)
    st.caption("Highlighted text is what the AI quoted as evidence.")
    if ss.live and st.button("Re-run AI on this update", icon=":material/refresh:"):
        with st.spinner("Asking Claude..."):
            ui.store_analysis(ai.analyze_update(latest, program, ui.get_api_key()))
        st.rerun()

with right:
    st.subheader("What the AI reads")
    if not analysis:
        st.info("No analysis yet for this update.")
    else:
        checks = check_analysis(analysis, latest.text)
        failed = [c for c in checks if not c.grounded]
        st.markdown(
            f"{ui.ai_pill(analysis.status)} &nbsp; <span class='muted'>confidence: "
            f"{analysis.confidence.value} · {analysis.model} · prompt {analysis.prompt_version}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**{analysis.reason}**")
        st.caption(badge(checks[0].grounded))

        if failed and pid not in ss.reviewed_programs:
            st.error(
                f"{len(failed)} item(s) cite a quote that is not in the update. This analysis is "
                "kept out of the weekly brief until someone reviews it.",
                icon="⚠️",
            )
            c1, c2 = st.columns(2)
            if c1.button("Remove unsupported items", type="primary"):
                cleaned = analysis.model_copy(
                    update={
                        "risks": [r for r in analysis.risks if is_grounded(r.evidence, latest.text)],
                        "decisions": [d for d in analysis.decisions if is_grounded(d.evidence, latest.text)],
                    }
                )
                ss.analyses[latest.id] = cleaned
                ss.reviewed_programs.add(pid)
                ss.audit.record(
                    action="edited",
                    item_id=latest.id,
                    actor=ss.reviewer,
                    before="; ".join(c.evidence for c in failed),
                    after="(removed)",
                    detail="Removed items whose quotes were not in the update",
                    model=analysis.model,
                    prompt_version=analysis.prompt_version,
                )
                st.rerun()
            if c2.button("I checked it, keep as is"):
                ss.reviewed_programs.add(pid)
                ss.audit.record(
                    action="approved",
                    item_id=latest.id,
                    actor=ss.reviewer,
                    detail="Reviewer accepted analysis despite failed grounding check",
                    model=analysis.model,
                    prompt_version=analysis.prompt_version,
                )
                st.rerun()
        elif pid in ss.reviewed_programs:
            st.success(f"Reviewed by {ss.reviewer}. Cleared for the weekly brief.", icon="✅")

        st.markdown("##### Risks")
        if not analysis.risks:
            st.caption("None found.")
        for r in analysis.risks:
            ok = is_grounded(r.evidence, latest.text)
            st.markdown(
                f'<div class="card"><b>{r.severity.value.title()}:</b> {html.escape(r.description)}'
                f'<div class="quote">"{html.escape(r.evidence)}"</div>'
                f'<div class="muted">{badge(ok)} · owner: {html.escape(r.owner or "not stated")}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("##### Decisions asked of leadership")
        if not analysis.decisions:
            st.caption("None asked.")
        for d in analysis.decisions:
            ok = is_grounded(d.evidence, latest.text)
            st.markdown(
                f'<div class="card">{html.escape(d.description)}'
                f'<div class="quote">"{html.escape(d.evidence)}"</div>'
                f'<div class="muted">{badge(ok)} · needed by: {html.escape(d.needed_by or "not stated")}</div></div>',
                unsafe_allow_html=True,
            )

st.divider()
st.subheader("Progress over time")
df = pd.DataFrame(
    [
        {"Week ending": u.week_ending, "Done (%)": u.percent_complete, "Owner status": u.self_status.value.title()}
        for u in history
    ]
)
line = (
    alt.Chart(df)
    .mark_line(point=alt.OverlayMarkDef(size=70, filled=True), strokeWidth=2, color="#2a78d6")
    .encode(
        x=alt.X("Week ending:T", title=None, axis=alt.Axis(format="%d %b")),
        y=alt.Y("Done (%):Q", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("Week ending:T", format="%d %b"), "Done (%)", "Owner status"],
    )
)
target = (
    alt.Chart(pd.DataFrame({"t": [pd.Timestamp(program.target_date)]}))
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(x="t:T")
)
st.altair_chart((line + target).properties(height=240), width="stretch")
st.caption("Dashed line: target date.")

with st.expander("All updates for this program"):
    for u in reversed(history):
        st.markdown(
            f"**{u.week_ending:%d %b}** {ui.self_pill(u.self_status)} {u.percent_complete}%  \n{html.escape(u.text)}",
            unsafe_allow_html=True,
        )

st.divider()
st.subheader("Try it on your own update")
if not ss.live:
    st.caption("Turn on Live AI in the sidebar (needs an API key) to analyze text you paste here.")
text = st.text_area(
    "Paste a status update",
    height=120,
    disabled=not ss.live,
    placeholder="e.g. Install crew finished 5 rooms. Still waiting on the landlord permit...",
)
self_status = st.radio(
    "Owner's self-reported status", [s.value for s in SelfStatus], horizontal=True, disabled=not ss.live
)
if ss.live and st.button("Analyze", disabled=not text.strip()):
    trial = Update(
        id=f"{pid}-trial",
        program_id=pid,
        week_ending=latest.week_ending,
        author=ss.reviewer,
        self_status=SelfStatus(self_status),
        percent_complete=latest.percent_complete,
        text=text,
    )
    with st.spinner("Asking Claude..."):
        result = ai.analyze_update(trial, program, ui.get_api_key())
    ss.audit.record(
        action="ai_suggested",
        item_id=trial.id,
        actor="AI",
        after=f"{result.status.value}: {result.reason}",
        detail="Ad hoc analysis of pasted text",
        model=result.model,
        prompt_version=result.prompt_version,
    )
    st.markdown(f"{ui.ai_pill(result.status)} **{result.reason}**", unsafe_allow_html=True)
    for c in check_analysis(result, text):
        st.markdown(f'- {c.item}: "{c.evidence}" · {badge(c.grounded)}')
