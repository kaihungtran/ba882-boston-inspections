import charts
import streamlit as st

import data

st.title("Results by neighborhood")
charts.stub_banner()
st.caption(
    "Inspections are placed in a neighborhood by their coordinates, or by the city field when "
    "coordinates are missing. Boundaries are real (stg_neighborhoods)."
)

by_hood = data.inspections_by_neighborhood()
shapes = data.neighborhood_shapes()

years = sorted(by_hood["year"].dropna().astype(int).unique())
start, end = st.select_slider("Years", options=years, value=(years[0], years[-1]))
min_inspections = st.number_input("Hide neighborhoods with fewer inspections than", 0, 1000, 20, step=10)

df = (
    by_hood[by_hood["year"].between(start, end)]
    .groupby("neighborhood", as_index=False)[["n_inspections", "n_failed", "n_establishments"]]
    .sum()
)
df["fail_rate"] = df["n_failed"] / df["n_inspections"]
# n_establishments summed over years can double count; it's an upper bound across the range.
shown = df[(df["n_inspections"] >= min_inspections) & (df["neighborhood"] != "Unmatched")]

st.subheader("Fail rate")
charts.choropleth(
    shapes, shown[["neighborhood", "fail_rate", "n_inspections"]], "fail_rate",
    lambda r: f"Fail rate {r['fail_rate']:.1%} of {int(r['n_inspections']):,} inspections",
)

unmatched = df.loc[df["neighborhood"] == "Unmatched", "n_inspections"].sum()
if unmatched:
    st.caption(f"{int(unmatched):,} inspections couldn't be placed in a neighborhood and aren't on the map.")

st.subheader("Table")
st.dataframe(
    df.sort_values("fail_rate", ascending=False),
    hide_index=True,
    width="stretch",
    column_config={
        "neighborhood": "Neighborhood",
        "n_inspections": st.column_config.NumberColumn("Inspections", format="%d"),
        "n_failed": st.column_config.NumberColumn("Failed", format="%d"),
        "n_establishments": st.column_config.NumberColumn(
            "Establishments", format="%d", help="Distinct licenses per year, summed across the selected years"),
        "fail_rate": st.column_config.ProgressColumn("Fail rate", format="percent", min_value=0, max_value=1),
    },
)
