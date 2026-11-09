"""Program Pulse: AI status reporting with human sign-off.

Run locally with:  streamlit run streamlit_app.py
"""

import streamlit as st

from pulse import ui

ui.setup_page()

nav = st.navigation(
    [
        st.Page("views/portfolio.py", title="Portfolio", icon=":material/dashboard:", default=True),
        st.Page("views/program_detail.py", title="Program detail", icon=":material/search:"),
        st.Page("views/risks_decisions.py", title="Risks and decisions", icon=":material/flag:"),
        st.Page("views/weekly_brief.py", title="Weekly brief", icon=":material/fact_check:"),
        st.Page("views/impact.py", title="Customer impact", icon=":material/air:"),
        st.Page("views/audit_log.py", title="AI audit log", icon=":material/history:"),
    ]
)
nav.run()
