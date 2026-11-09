"""Weekly founder and board brief. The AI drafts, a person approves line by line."""

import html

import streamlit as st

from pulse import ai, data, ui
from pulse.brief import SECTION_TITLES, Review, is_locked, lab_claim_issue, render_markdown

ss = st.session_state
week = data.reporting_week(ss.updates)
locked_programs = ui.ungrounded_programs()

st.title("Weekly brief")
st.markdown(
    "The AI drafts one page for the founder and board. **Nothing goes out until a person approves "
    "it.** Lines that rely on an analysis with an unchecked quote stay locked until that analysis "
    "is reviewed on the Program detail page. Lines that use lab test figures as customer results "
    "must be rewritten before they can be approved."
)

if ss.live and st.button("Redraft brief with AI", icon=":material/refresh:"):
    latest = data.latest_update_per_program(ss.updates)
    pairs = [(ss.programs[pid], ss.analyses[u.id]) for pid, u in latest.items() if u.id in ss.analyses]
    with st.spinner("Asking Claude..."):
        ss.brief = ai.draft_brief(pairs, week, ui.get_api_key())
    ss.reviews = {i.id: Review("pending", i.text) for i in ss.brief.items}
    for i in ss.brief.items:
        ss.audit.record(
            action="ai_suggested",
            item_id=i.id,
            actor="AI",
            after=i.text,
            detail="Brief item drafted",
            model=ss.brief.model,
            prompt_version=ss.brief.prompt_version,
        )
        ui.log_lab_claim(i)
    st.rerun()

reviews = ss.reviews
done = sum(1 for r in reviews.values() if r.state != "pending")
st.progress(done / max(len(reviews), 1), text=f"{done} of {len(reviews)} lines reviewed")


def act(item, state: str, text: str | None = None) -> None:
    before = reviews[item.id].text
    reviews[item.id] = Review(state, text if text is not None else before)
    ss.audit.record(
        action=state,
        item_id=item.id,
        actor=ss.reviewer,
        before=before,
        after=reviews[item.id].text if state != "rejected" else None,
        model=ss.brief.model,
        prompt_version=ss.brief.prompt_version,
    )


if st.button("Approve all lines with no open checks"):
    for item in ss.brief.items:
        review = reviews[item.id]
        if review.state == "pending" and not is_locked(item, locked_programs) and not lab_claim_issue(review.text):
            act(item, "approved")
    st.rerun()

STATE_LABEL = {
    "pending": "⏳ Waiting for review",
    "approved": "✅ Approved",
    "edited": "✏️ Edited and approved",
    "rejected": "❌ Rejected",
}

for section, title in SECTION_TITLES.items():
    st.subheader(title)
    for item in (i for i in ss.brief.items if i.section == section):
        review = reviews[item.id]
        locked = is_locked(item, locked_programs)
        with st.container(border=True):
            st.markdown(html.escape(review.text) if review.state != "rejected" else f"~~{html.escape(review.text)}~~")
            sources = ", ".join(ss.programs[p].name for p in item.program_ids if p in ss.programs)
            st.caption(f"{STATE_LABEL[review.state]} · based on: {sources}")
            if locked:
                st.warning(
                    "Locked: the analysis behind this line quotes text that is not in the update. "
                    "Review it on Program detail first.",
                    icon="🔒",
                )
                continue
            lab_issue = lab_claim_issue(review.text) if review.state != "rejected" else None
            if lab_issue:
                st.warning(lab_issue, icon="🧪")
            editing = ss.get("editing") == item.id
            if editing:
                new_text = st.text_area("Edit line", value=review.text, key=f"edit_{item.id}")
                if st.button("Save and approve", key=f"save_{item.id}", type="primary"):
                    if lab_claim_issue(new_text):
                        st.error("Still reads as a lab figure presented as a customer result. Use field results.")
                    else:
                        act(item, "edited", new_text)
                        ss.editing = None
                        st.rerun()
            else:
                with st.container(horizontal=True):
                    if st.button(
                        "Approve", key=f"ok_{item.id}", disabled=review.state == "approved" or bool(lab_issue)
                    ):
                        act(item, "approved")
                        st.rerun()
                    if st.button("Edit", key=f"ed_{item.id}"):
                        ss.editing = item.id
                        st.rerun()
                    if st.button("Reject", key=f"no_{item.id}", disabled=review.state == "rejected"):
                        act(item, "rejected")
                        st.rerun()

st.divider()
st.subheader("Final brief")
final = render_markdown(ss.brief, reviews, ss.company["name"], week, ss.reviewer)
with st.container(border=True):
    st.markdown(final)
if st.download_button("Download brief (Markdown)", final, f"weekly_brief_{week}.md", "text/markdown", type="primary"):
    ss.audit.record(
        action="exported",
        item_id="brief",
        actor=ss.reviewer,
        detail=f"Exported brief with {sum(r.state in ('approved', 'edited') for r in reviews.values())} lines",
    )
