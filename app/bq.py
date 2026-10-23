"""BigQuery access with application default credentials and Streamlit caching."""

import config
import pandas as pd
import streamlit as st
from google.cloud import bigquery

CACHE_TTL_SECONDS = 60 * 60  # staging refreshes daily; an hour keeps clicks free


@st.cache_resource
def client() -> bigquery.Client:
    # No key file: uses `gcloud auth application-default login` locally and the
    # service account on Cloud Run.
    return bigquery.Client(project=config.project_id())


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Querying BigQuery…")
def run_query(sql: str) -> pd.DataFrame:
    return client().query(sql).to_dataframe()
