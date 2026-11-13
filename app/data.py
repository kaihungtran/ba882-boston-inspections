"""Data access for the pages. Inspection functions switch between BigQuery and stub data
on USE_STUB_INSPECTIONS; everything else always reads BigQuery."""

from datetime import datetime, timezone

import config
import pandas as pd
import queries
import streamlit as st
import stub_data
from bq import run_query


@st.cache_data(show_spinner="Generating stub inspections…")
def _stub_rows() -> pd.DataFrame:
    return stub_data.make_inspections()


def inspections_monthly() -> pd.DataFrame:
    if config.use_stub_inspections():
        return stub_data.inspections_monthly(_stub_rows())
    return run_query(queries.inspections_monthly())


def inspections_by_neighborhood() -> pd.DataFrame:
    if config.use_stub_inspections():
        return stub_data.inspections_by_neighborhood(_stub_rows())
    return run_query(queries.inspections_by_neighborhood())


def violations_by_type() -> pd.DataFrame:
    if config.use_stub_inspections():
        return stub_data.violations_by_type(_stub_rows())
    return run_query(queries.violations_by_type())


def neighborhood_shapes() -> pd.DataFrame:
    return run_query(queries.neighborhood_shapes())


def food_safety_311_monthly() -> pd.DataFrame:
    return run_query(queries.food_safety_311_monthly())


def food_safety_311_by_neighborhood() -> pd.DataFrame:
    return run_query(queries.food_safety_311_by_neighborhood())


def food_safety_311_summary() -> pd.Series:
    return run_query(queries.food_safety_311_summary()).iloc[0]


def _freshness(age_days) -> str:
    if pd.isna(age_days):
        return "Static"  # seeds have no load date
    if age_days > config.FRESH_ERROR_DAYS:
        return "Stale"
    if age_days > config.FRESH_WARN_DAYS:
        return "Behind"
    return "Fresh"


def data_status() -> pd.DataFrame:
    """One row per source, with days since its last load and a Fresh / Behind / Stale status."""
    df = run_query(queries.data_status(include_inspections=not config.use_stub_inspections())).copy()
    today = datetime.now(timezone.utc).date()
    df["age_days"] = pd.array(
        [(today - d).days if pd.notna(d) else None for d in df["latest_load"]], dtype="Int64"
    )
    df["status"] = df["age_days"].map(_freshness)
    return df


def built_tables() -> pd.DataFrame:
    """Intermediate tables with their last rebuild time, or an empty frame when on stub data."""
    if config.use_stub_inspections():
        return pd.DataFrame(columns=["table_name", "n_rows", "built_at"])
    return run_query(queries.built_tables())


def freshness_summary() -> dict | None:
    """The least fresh loaded source, for the banner and sidebar. None if nothing has a load date."""
    status = data_status()
    dated = status.dropna(subset=["latest_load"])
    if dated.empty:
        return None
    worst = dated.sort_values("age_days", ascending=False).iloc[0]
    inspections = status.loc[status["source"] == "Food inspections", "last_date"]
    return {
        "status": worst["status"],
        "age_days": int(worst["age_days"]),
        "latest_load": dated["latest_load"].max(),
        "n_sources": len(dated),
        "n_not_fresh": int((dated["status"] != "Fresh").sum()),
        "inspections_through": inspections.iloc[0] if len(inspections) and pd.notna(inspections.iloc[0]) else None,
    }
