"""Audit log: every AI suggestion and every human decision about it."""

import pandas as pd
import streamlit as st

ss = st.session_state
log = ss.audit

st.title("AI audit log")
st.markdown(
    "Who did what with each AI output, with the model and prompt version that produced it. "
    "In the demo this log covers your browser session; a production setup would write it to a database."
)

s = log.summary()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("AI suggestions", s.get("ai_suggested", 0))
c2.metric("Approved", s.get("approved", 0))
c3.metric("Edited", s.get("edited", 0))
c4.metric("Rejected", s.get("rejected", 0))
c5.metric("Failed quote check", s.get("grounding_failed", 0))
c6.metric("Lab figure flags", s.get("lab_claim_flagged", 0))

reviewed = s.get("approved", 0) + s.get("edited", 0) + s.get("rejected", 0)
if reviewed:
    changed = s.get("edited", 0) + s.get("rejected", 0)
    st.caption(
        f"Reviewers changed or rejected {changed / reviewed:.0%} of the AI lines they looked at. "
        "Tracking this over time shows whether the prompts are getting better or worse."
    )

df = pd.DataFrame(log.to_rows())
actions = st.multiselect("Show actions", sorted(df["action"].unique()), default=sorted(df["action"].unique()))
st.dataframe(df[df["action"].isin(actions)].iloc[::-1], hide_index=True, width="stretch")
st.download_button("Download log (JSON lines)", log.to_jsonl(), "audit_log.jsonl", "application/json")
