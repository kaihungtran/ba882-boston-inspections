"""Data access for the pages. Inspection functions switch between BigQuery and stub data
on USE_STUB_INSPECTIONS; everything else always reads BigQuery."""

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
