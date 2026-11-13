import config
import pandas as pd
import streamlit as st
import ui

import data

ui.page_header(
    "Pipeline · Freshness check",
    "Data freshness",
    "When each source was last loaded into BigQuery and what dates it covers. The thresholds match "
    f"dbt's source freshness check: behind after {config.FRESH_WARN_DAYS} days without a load, "
    f"stale after {config.FRESH_ERROR_DAYS}.",
)

status = data.data_status()
summary = data.freshness_summary()

if summary:
    through = summary["inspections_through"]
    ui.stat_row([
        ("Last load", f"{summary['latest_load']:%b %d, %Y}", f"{summary['age_days']} days ago"),
        ("Inspections through", f"{through:%b %d, %Y}" if through else "n/a",
         "latest inspection date in staging" if through else "inspection pages are on stub data"),
        ("Sources up to date", f"{summary['n_sources'] - summary['n_not_fresh']} of {summary['n_sources']}",
         f"loaded within {config.FRESH_WARN_DAYS} days"),
    ])

ui.section("Sources", "from the staging views this app reads")


def _date(d) -> str:
    return f"{d:%b %d, %Y}" if pd.notna(d) else "—"


# Loaded sources first (least fresh on top), the static seed last. Dates are shown as text
# so a source without one reads as a dash rather than "None".
ordered = status.sort_values(["age_days", "source"], ascending=[False, True], na_position="last")
table = pd.DataFrame({
    "Source": ordered["source"],
    "Staging view": ordered["view_name"],
    "Status": ordered["status"],
    "Last load": ordered["latest_load"].map(_date),
    "Days since load": ordered["age_days"].map(lambda n: str(n) if pd.notna(n) else "—"),
    "Rows": ordered["n_rows"],
    "Covers from": ordered["first_date"].map(_date),
    "Covers to": ordered["last_date"].map(_date),
})
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={"Rows": st.column_config.NumberColumn("Rows", format="localized")},
)
st.caption(
    "Loads come from the raw_api_ingest Airflow DAG. Neighborhood boundaries are a static dbt seed, "
    "so they have no load date. For licenses, the dates are when each active license was added."
)
if config.use_stub_inspections():
    st.caption("Food inspections aren't listed because the inspection pages are using stub data.")

built = data.built_tables()
if not built.empty:
    ui.section("dbt intermediate tables", f"in {config.intermediate_dataset()}")
    st.dataframe(
        pd.DataFrame({
            "Table": built["table_name"],
            "Rows": built["n_rows"],
            "Last built": built["built_at"].map(lambda t: f"{t:%b %d, %Y %H:%M} UTC"),
        }),
        hide_index=True,
        width="stretch",
        column_config={"Rows": st.column_config.NumberColumn("Rows", format="localized")},
    )
    st.caption(
        "The inspection pages read int_inspections and int_establishment_geo. These are tables, not "
        "views, so a new raw load only reaches them when dbt is run again."
    )
