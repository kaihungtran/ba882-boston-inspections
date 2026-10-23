import charts
import streamlit as st

import data

st.title("Inspection pass/fail trends")
charts.stub_banner()
st.caption("One inspection = one license on one date. An inspection fails if any of its rows has a failing result.")

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
m1, m2, m3 = st.columns(3)
m1.metric("Inspections", f"{total:,}")
m2.metric("Failed", f"{failed:,}")
m3.metric("Fail rate", f"{failed / total:.1%}")

st.subheader("Fail rate by month")
st.altair_chart(charts.rate_line(by_month, "month", "fail_rate", "Fail rate"), width="stretch")

st.subheader("Inspections by month")
long = by_month.assign(Passed=by_month["n_inspections"] - by_month["n_failed"], Failed=by_month["n_failed"])
long = long.melt(id_vars="month", value_vars=["Passed", "Failed"], var_name="result", value_name="n")
st.altair_chart(
    charts.stacked_bars(long, "month", "n", "result", ["Passed", "Failed"],
                        [charts.STATUS_GOOD, charts.STATUS_CRITICAL], "Inspections", "Result"),
    width="stretch",
)

with st.expander("Table"):
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
