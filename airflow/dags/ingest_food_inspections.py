"""Daily ingestion of Boston food establishment inspections.

Starter skeleton: confirm the CKAN resource ID and field names first
(see the issue "Confirm inspection data recency and API access").

Flow: CKAN datastore API -> newline-delimited JSON in GCS -> BigQuery raw table.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import requests

try:  # Airflow 3 (current Astro Runtime)
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2
    from airflow.decorators import dag, task

CKAN_URL = "https://data.boston.gov/api/3/action/datastore_search"
RESOURCE_ID = os.getenv("CKAN_INSPECTIONS_RESOURCE_ID", "TODO-confirm-resource-id")
BUCKET = os.getenv("GCS_LANDING_BUCKET", "TODO-bucket")
PROJECT = os.getenv("GCP_PROJECT_ID", "TODO-project")
RAW_TABLE = f"{PROJECT}.raw.food_inspections"
PAGE_SIZE = 10_000


@dag(
    schedule="@daily",
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["ingestion", "inspections"],
)
def ingest_food_inspections():
    @task
    def extract_to_gcs(ds=None) -> str:
        """Page through the CKAN API and write records to GCS as NDJSON."""
        from google.cloud import storage

        records, offset = [], 0
        while True:
            resp = requests.get(
                CKAN_URL,
                params={"resource_id": RESOURCE_ID, "limit": PAGE_SIZE, "offset": offset},
                timeout=60,
            )
            resp.raise_for_status()
            batch = resp.json()["result"]["records"]
            if not batch:
                break
            records.extend(batch)
            offset += PAGE_SIZE

        # TODO: switch to an incremental pull (filter on result date > last loaded date)
        path = f"raw/food_inspections/load_date={ds}/inspections.json"
        blob = storage.Client().bucket(BUCKET).blob(path)
        blob.upload_from_string("\n".join(json.dumps(r) for r in records))
        return f"gs://{BUCKET}/{path}"

    @task
    def load_to_bigquery(gcs_uri: str) -> None:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT)
        job = client.load_table_from_uri(
            gcs_uri,
            RAW_TABLE,
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                autodetect=True,
                write_disposition="WRITE_TRUNCATE",  # TODO: WRITE_APPEND once incremental
            ),
        )
        job.result()

    load_to_bigquery(extract_to_gcs())


ingest_food_inspections()
