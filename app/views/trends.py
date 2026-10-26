import charts
import streamlit as st
import ui

import data

ui.page_header(
    "Inspections · Phase 1",
    "Pass/fail trends",
    "One inspection is one license on one date. It counts as failed if any of its rows has a failing result.",
)
ui.stub_notice()

monthly = data.inspections_monthly()

categories = sorted(monthly["license_category"].unique())
months = sorted(monthly["month"].unique())
c1, c2 = st.columns([1, 2])
selected_cats = c1.multiselect("License category", categories, default=categories)
start, end = c2.select_slider(
    "Months", options=months, value=(months[0], months[-1]), format_func=lambda m: m.strftime("%b %Y")
)

df = monthly[monthly["license_category"].isin(selected_cats) & monthly["month"].between(start, end)]
if df.empty:
    st.info("No inspections match these filters.")
    st.stop()

by_month = df.groupby("month", as_index=False)[["n_inspections", "n_failed"]].sum()
by_month["fail_rate"] = by_month["n_failed"] / by_month["n_inspections"]

total, failed = int(by_month["n_inspections"].sum()), int(by_month["n_failed"].sum())
span = f"{start:%b %Y} to {end:%b %Y}"
ui.stat_row([
    ("Inspections", f"{total:,}", span),
    ("Failed", f"{failed:,}", "at least one failing result"),
    ("Fail rate", f"{failed / total:.1%}", "share of inspections"),
])

ui.section("Fail rate by month", "share of that month's inspections that failed")
st.altair_chart(charts.rate_line(by_month, "month", "fail_rate", "Fail rate"), width="stretch", theme=None)

ui.section("Inspections by month", "passed and failed")
long = by_month.assign(Passed=by_month["n_inspections"] - by_month["n_failed"], Failed=by_month["n_failed"])
long = long.melt(id_vars="month", value_vars=["Passed", "Failed"], var_name="result", value_name="n")
st.altair_chart(
    charts.stacked_bars(long, "month", "n", "result", ["Passed", "Failed"],
                        [charts.STATUS_GOOD, charts.STATUS_CRITICAL], "Inspections", "Result"),
    width="stretch",
    theme=None,
)

with st.expander("Show as a table"):
    st.dataframe(
        by_month.sort_values("month", ascending=False),
        hide_index=True,
        column_config={
            "month": st.column_config.DateColumn("Month", format="MMM YYYY"),
            "n_inspections": st.column_config.NumberColumn("Inspections", format="%d"),
            "n_failed": st.column_config.NumberColumn("Failed", format="%d"),
            "fail_rate": st.column_config.NumberColumn("Fail rate", format="percent"),
        },
    )
