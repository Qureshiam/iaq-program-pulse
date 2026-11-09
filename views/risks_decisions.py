"""Risk register and decision log, pulled out of this week's updates by the AI."""

import pandas as pd
import streamlit as st

from pulse import data
from pulse.grounding import is_grounded

ss = st.session_state
latest = data.latest_update_per_program(ss.updates)

risk_rows, decision_rows = [], []
for pid, upd in latest.items():
    a = ss.analyses.get(upd.id)
    if not a:
        continue
    name = ss.programs[pid].name
    for r in a.risks:
        risk_rows.append(
            {
                "Program": name,
                "Severity": r.severity.value.title(),
                "Risk": r.description,
                "Owner": r.owner or "Not stated",
                "Evidence": r.evidence,
                "Quote checked": "✅ Found" if is_grounded(r.evidence, upd.text) else "⚠️ Not found",
            }
        )
    for d in a.decisions:
        decision_rows.append(
            {
                "Program": name,
                "Decision": d.description,
                "Needed by": d.needed_by or "Not stated",
                "Evidence": d.evidence,
                "Quote checked": "✅ Found" if is_grounded(d.evidence, upd.text) else "⚠️ Not found",
            }
        )

st.title("Risks and decisions")
st.caption("Extracted by the AI from this week's updates. Every line carries the quote it came from.")

st.subheader("Decisions leadership needs to make")
st.dataframe(pd.DataFrame(decision_rows), hide_index=True, width="stretch")

st.subheader("Risk register")
sev = st.segmented_control(
    "Severity", ["High", "Medium", "Low"], selection_mode="multi", default=["High", "Medium", "Low"]
)
risks = pd.DataFrame(risk_rows)
if not risks.empty:
    risks["sort"] = risks["Severity"].map({"High": 0, "Medium": 1, "Low": 2})
    risks = risks[risks["Severity"].isin(sev or [])].sort_values(["sort", "Program"]).drop(columns="sort")
st.dataframe(risks, hide_index=True, width="stretch")

unowned = sum(1 for r in risk_rows if r["Owner"] == "Not stated" and r["Severity"] == "High")
if unowned:
    st.warning(
        f"{unowned} high risks have no named owner in the updates. Assigning owners is a good first agenda item.",
        icon="👤",
    )

c1, c2 = st.columns(2)
c1.download_button(
    "Download risk register (CSV)", pd.DataFrame(risk_rows).to_csv(index=False), "risk_register.csv", "text/csv"
)
c2.download_button(
    "Download decision log (CSV)", pd.DataFrame(decision_rows).to_csv(index=False), "decision_log.csv", "text/csv"
)
