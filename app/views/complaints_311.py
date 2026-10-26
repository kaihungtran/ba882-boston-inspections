import charts
import streamlit as st
import ui

import data

ui.page_header(
    "311 service requests · Phase 1",
    "Food-safety complaints",
    "Real data from stg_311_requests, which unions the legacy and new 311 systems. A case counts as "
    "food safety when its category is flagged in seeds/food_safety_311_categories.csv, which is still a draft.",
)

summary = data.food_safety_311_summary()
monthly = data.food_safety_311_monthly()
by_hood = data.food_safety_311_by_neighborhood()
shapes = data.neighborhood_shapes()

ui.stat_row([
    ("Food-safety cases", f"{int(summary['n_food_safety']):,}", f"since {min(monthly['month']):%b %Y}"),
    ("Share of all 311 cases", f"{summary['n_food_safety'] / summary['n_cases']:.1%}",
     f"of {int(summary['n_cases']):,} cases in staging"),
    ("Latest case opened", f"{summary['last_opened']:%b %d, %Y}", f"loaded {summary['last_load_date']:%b %d}"),
])
st.caption(
    f"311 cases in staging were opened {summary['first_opened']:%b %d, %Y} to {summary['last_opened']:%b %d, %Y}. "
    "Older 311 history hasn't been backfilled yet."
)

themes_present = [t for t in charts.THEMES if t in set(monthly["theme"])]
selected = st.multiselect("Themes", themes_present, default=themes_present)
theme_colors = dict(zip(charts.THEMES, charts.categorical()))  # color follows the theme, not its rank

ui.section("Cases by month", "the latest month is partial")
m = monthly[monthly["theme"].isin(selected)]
st.altair_chart(
    charts.stacked_bars(m, "month", "n_cases", "theme", selected,
                        [theme_colors[t] for t in selected], "Cases", "Theme"),
    width="stretch",
    theme=None,
)

ui.section("Cases by neighborhood", "placed by the case's coordinates")
h = by_hood[by_hood["theme"].isin(selected)]
totals = h.groupby("neighborhood", as_index=False)["n_cases"].sum()
on_map = totals[totals["neighborhood"] != "Unmatched"].merge(shapes[["neighborhood", "sqmiles"]], on="neighborhood")
on_map["per_sqmile"] = on_map["n_cases"] / on_map["sqmiles"]

measure = st.radio("Color by", ["Cases", "Cases per square mile"], horizontal=True)
value_col = "n_cases" if measure == "Cases" else "per_sqmile"
charts.choropleth(
    shapes, on_map[["neighborhood", "n_cases", "per_sqmile"]], value_col,
    lambda r: f"{int(r['n_cases']):,} cases · {r['per_sqmile']:,.0f} per sq mi",
)
unmatched = totals.loc[totals["neighborhood"] == "Unmatched", "n_cases"].sum()
if unmatched:
    st.caption(f"{int(unmatched):,} cases have no usable location and aren't on the map.")

table = (
    h.pivot_table(index="neighborhood", columns="theme", values="n_cases", aggfunc="sum", fill_value=0)
    .reindex(columns=[t for t in selected if t in set(h["theme"])])
)
table.insert(0, "total", table.sum(axis=1))
st.dataframe(table.sort_values("total", ascending=False), width="stretch")
