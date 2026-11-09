"""Customer impact: before-and-after results from our own field assessments."""

import altair as alt
import streamlit as st

from pulse import data

df = data.load_assessments()
done = df.dropna(subset=["mold_after"])
pending = df[df["mold_after"].isna()]
induct = done[done["solution"] == "In-duct"]
portable = done[done["solution"] == "Portable"]

st.title("Customer impact")
st.markdown(
    "Results from the before-and-after assessment service: 72 hours of logging before install, 72 hours after, "
    "same rooms, plus air samples for mold spores. These field numbers, not the manufacturer's lab figures, are "
    "what the investor update and sales material may quote."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sites with before and after", len(done))
c2.metric("Median airborne mold change", f"{done['mold_change_pct'].median():.0f}%")
c3.metric("Median VOC change", f"{done['tvoc_change_pct'].median():.0f}%")
c4.metric("Median PM2.5 change (portables)", f"{portable['pm25_change_pct'].median():.0f}%")

st.info(
    f"**Lab versus field.** Manufacturer lab tests run in sealed chambers against one organism at a time and "
    f"typically report 99.9% or more. In occupied rooms, with doors opening and people moving, our assessments "
    f"show a median mold cut of {abs(done['mold_change_pct'].median()):.0f}%. Still large, and it is the number "
    "we can defend in front of a customer or an investor.",
    icon="🧪",
)

st.subheader("Airborne mold before and after, by site")
long = done.melt(
    id_vars=["site_id", "site_type", "solution"],
    value_vars=["mold_before", "mold_after"],
    var_name="When",
    value_name="mold",
)
long["When"] = long["When"].map({"mold_before": "Before", "mold_after": "After"})
bars = (
    alt.Chart(long)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("site_id:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("When:N", sort=["Before", "After"]),
        y=alt.Y("mold:Q", title="Mold spores (CFU/m³)"),
        color=alt.Color(
            "When:N",
            sort=["Before", "After"],
            scale=alt.Scale(range=["#a3a29d", "#2a78d6"]),
            legend=alt.Legend(orient="top", title=None),
        ),
        tooltip=["site_id", "site_type", "solution", "When", alt.Tooltip("mold:Q", title="CFU/m³", format=",.0f")],
    )
)
st.altair_chart(bars.properties(height=320), width="stretch")
st.caption("CFU/m³: colony-forming units per cubic meter of air. Hover a bar for site details.")

st.subheader("Which solution moves which number")
change = done.melt(
    id_vars=["site_id", "solution"],
    value_vars=["mold_change_pct", "tvoc_change_pct", "pm25_change_pct", "co2_change_pct"],
    var_name="Metric",
    value_name="change",
)
labels = {"mold_change_pct": "Mold", "tvoc_change_pct": "VOCs", "pm25_change_pct": "PM2.5", "co2_change_pct": "CO2"}
change["Metric"] = change["Metric"].map(labels)
dots = (
    alt.Chart(change)
    .mark_circle(size=110, opacity=0.9, stroke="white", strokeWidth=2)
    .encode(
        y=alt.Y("Metric:N", sort=list(labels.values()), title=None),
        x=alt.X("change:Q", title="Change after install (%)", scale=alt.Scale(domain=[-100, 10])),
        color=alt.Color(
            "solution:N",
            title=None,
            scale=alt.Scale(domain=["In-duct", "Portable"], range=["#2a78d6", "#eb6834"]),
            legend=alt.Legend(orient="top"),
        ),
        yOffset=alt.YOffset("solution:N"),
        tooltip=["site_id", "solution", "Metric", alt.Tooltip("change:Q", title="Change (%)", format=".0f")],
    )
)
zero = alt.Chart().mark_rule(color="gray").encode(x=alt.datum(0))
st.altair_chart((zero + dots).properties(height=260), width="stretch")
st.markdown(
    f"Both solutions cut mold and VOCs. Only the portable unit, which has a HEPA filter, also cuts fine particles "
    f"(median {portable['pm25_change_pct'].median():.0f}% vs {induct['pm25_change_pct'].median():.0f}% for in-duct). "
    "Neither moves CO2, because neither brings in fresh air. Sales should not promise particle gains from in-duct "
    "units or CO2 gains from either product."
)

if not pending.empty:
    st.subheader("Waiting for post-install results")
    for _, r in pending.iterrows():
        st.info(
            f"**{r.site_id}** ({r.site_type}): baseline mold {r.mold_before:,.0f} CFU/m³, CO2 {r.co2_before:,.0f} ppm. "
            "Post-install assessment depends on the school pilot install finishing.",
            icon="⏳",
        )

with st.expander("Data table"):
    st.dataframe(df, hide_index=True, width="stretch")
st.caption("All sites and readings are synthetic. Mold in CFU/m³, VOCs and PM2.5 in µg/m³, CO2 in ppm.")
