"""Portfolio view: every program on one screen, with the AI's read next to the owner's."""

import html

import altair as alt
import pandas as pd
import streamlit as st

from pulse import data, ui
from pulse.drift import all_flags
from pulse.models import AIStatus, SelfStatus

ss = st.session_state
week = data.reporting_week(ss.updates)
latest = data.latest_update_per_program(ss.updates)
flags = all_flags(list(ss.programs.values()), ss.updates, ss.analyses, week)
flags_by_program: dict[str, list] = {}
for f in flags:
    flags_by_program.setdefault(f.program_id, []).append(f)

st.title("Program Pulse")
st.markdown(
    f"Weekly status for **{ss.company['name']}**, a fictional indoor air quality startup. "
    f"Week ending **{week:%d %B %Y}**. The AI reads each owner's free-text update and says what it "
    "really shows; plain rules watch the history for drift; a person approves what goes to the board."
)
if not ss.live:
    st.info("Demo mode. AI results are saved outputs, so you can click around at no cost.", icon="💾")

counts = ui.status_counts()
decisions = sum(len(ss.analyses[u.id].decisions) for u in latest.values() if u.id in ss.analyses)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Programs", len(ss.programs))
c2.metric("● On track", counts[AIStatus.on_track])
c3.metric("▲ At risk", counts[AIStatus.at_risk])
c4.metric("■ Off track", counts[AIStatus.off_track])
c5.metric("Decisions needed", decisions)

mismatches = [f for f in flags if f.kind == "status_mismatch"]
if mismatches:
    names = ", ".join(ss.programs[f.program_id].name for f in mismatches)
    st.warning(f"**Owner says green, the update says otherwise:** {names}.", icon="🍉")

st.subheader("Programs this week")
rows = []
for pid, program in ss.programs.items():
    upd = latest.get(pid)
    a = ss.analyses.get(upd.id) if upd else None
    flag_html = "".join(f'<div class="muted">⚑ {html.escape(f.label)}</div>' for f in flags_by_program.get(pid, []))
    rows.append(
        "<tr>"
        f"<td><b>{html.escape(program.name)}</b><div class='muted'>{html.escape(program.owner)}</div></td>"
        f"<td>{ui.self_pill(upd.self_status) if upd else '-'}</td>"
        f"<td>{ui.ai_pill(a.status) if a else '-'}</td>"
        f"<td>{html.escape(a.reason) if a else ''}</td>"
        f"<td style='text-align:right'>{upd.percent_complete if upd else 0}%</td>"
        f"<td>{program.target_date:%d %b}</td>"
        f"<td>{flag_html}</td>"
        "</tr>"
    )
st.markdown(
    "<table style='width:100%; border-collapse:collapse'>"
    "<thead><tr style='text-align:left'><th>Program</th><th>Owner says</th><th>AI reads</th>"
    "<th>Why</th><th>Done</th><th>Target</th><th>Drift flags</th></tr></thead>"
    f"<tbody>{''.join(rows)}</tbody></table>",
    unsafe_allow_html=True,
)
st.caption("Open **Program detail** to see the exact quotes behind each AI call.")

st.subheader("What owners reported, week by week")
st.caption("Self-reported status only. Compare with the AI column above: green weeks can hide trouble.")
hist = pd.DataFrame(
    [
        {
            "Program": ss.programs[u.program_id].name,
            "Week ending": u.week_ending.strftime("%d %b"),
            "Status": u.self_status.value.title(),
            "Icon": ui.SELF_STYLE[u.self_status][0],
            "Done": f"{u.percent_complete}%",
            "Update": u.text[:140] + ("..." if len(u.text) > 140 else ""),
        }
        for u in ss.updates
    ]
)
order = [s.value.title() for s in SelfStatus]
colors = [ui.SELF_STYLE[s][2] for s in SelfStatus]
week_order = sorted(hist["Week ending"].unique(), key=lambda w: pd.to_datetime(w + " 2026"))
base = alt.Chart(hist).encode(
    x=alt.X("Week ending:O", sort=week_order, title=None),
    y=alt.Y("Program:N", sort=[p.name for p in ss.programs.values()], title=None),
)
heat = base.mark_rect(cornerRadius=4, stroke="white", strokeWidth=2).encode(
    color=alt.Color("Status:N", scale=alt.Scale(domain=order, range=colors), legend=alt.Legend(orient="top")),
    tooltip=["Program", "Week ending", "Status", "Done", "Update"],
)
labels = base.mark_text(color="white", fontWeight="bold").encode(text="Done:N")
st.altair_chart((heat + labels).properties(height=300), width="stretch")

st.subheader("Drift flags")
st.caption("Plain rules on the update history. No AI involved, so every flag can be explained.")
if not flags:
    st.success("No drift flags this week.")
for pid, fl in flags_by_program.items():
    st.markdown(f"**{ss.programs[pid].name}**")
    for f in fl:
        st.markdown(
            f'<div class="flag {f.severity}"><b>{html.escape(f.label)}.</b> {html.escape(f.detail)}</div>',
            unsafe_allow_html=True,
        )
