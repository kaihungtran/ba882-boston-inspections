"""BigQuery access and Streamlit caching. Credentials come from a service-account key in
Streamlit secrets when deployed, otherwise from application default credentials."""

import config
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

CACHE_TTL_SECONDS = 60 * 60  # staging refreshes daily; an hour keeps clicks free


def _credentials():
    try:
        info = st.secrets.get("gcp_service_account")
    except Exception:  # noqa: BLE001 - no secrets file locally
        info = None
    if info:
        return service_account.Credentials.from_service_account_info(dict(info))
    return None  # ADC: `gcloud auth application-default login` locally


@st.cache_resource
def client() -> bigquery.Client:
    return bigquery.Client(project=config.project_id(), credentials=_credentials())


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Querying BigQuery…")
def run_query(sql: str) -> pd.DataFrame:
    return client().query(sql).to_dataframe()
