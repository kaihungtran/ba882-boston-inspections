import altair as alt
import charts
import streamlit as st

import data

LEVELS = ["*", "**", "***"]
# Ordinal blue steps: more stars (more serious) = darker.
LEVEL_COLORS = [charts.SEQUENTIAL[2], charts.SEQUENTIAL[4], charts.SEQUENTIAL[6]]

st.title("Top violation types")
charts.stub_banner()
st.caption("Counts violation rows. Severity: * minor, ** major, *** critical.")

viol = data.violations_by_type()

years = sorted(viol["year"].dropna().astype(int).unique())
c1, c2, c3 = st.columns([2, 2, 1])
start, end = c1.select_slider("Years", options=years, value=(years[0], years[-1]))
levels = c2.multiselect("Severity", LEVELS, default=LEVELS)
top_n = c3.number_input("Show top", 5, 50, 15, step=5)

df = viol[viol["year"].between(start, end) & viol["violation_level"].isin(levels)]
top = (
    df.groupby(["violation_description", "violation_level"], as_index=False)["n_violations"].sum()
    .sort_values("n_violations", ascending=False)
    .head(int(top_n))
)
if top.empty:
    st.info("No violations match these filters.")
    st.stop()

chart = (
    alt.Chart(top)
    .mark_bar(cornerRadiusEnd=4, height={"band": 0.7})
    .encode(
        x=alt.X("n_violations:Q", title="Violations"),
        y=alt.Y("violation_description:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("violation_level:N", title="Severity",
                        scale=alt.Scale(domain=LEVELS, range=LEVEL_COLORS),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("violation_description:N", title="Violation"),
                 alt.Tooltip("violation_level:N", title="Severity"),
                 alt.Tooltip("n_violations:Q", title="Violations", format=",")],
    )
)
# Streamlit overrides the chart's own height, so set it here: one 26px row per violation type.
st.altair_chart(chart, width="stretch", height=max(240, 26 * top["violation_description"].nunique() + 60))

with st.expander("Table"):
    st.dataframe(
        top, hide_index=True, width="stretch",
        column_config={
            "violation_description": "Violation",
            "violation_level": "Severity",
            "n_violations": st.column_config.NumberColumn("Violations", format="%d"),
        },
    )
