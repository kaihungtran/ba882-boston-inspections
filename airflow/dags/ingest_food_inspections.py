"""Daily ingestion of Boston food establishment inspections.

Flow: CKAN datastore API -> NDJSON pages in GCS -> BigQuery raw table.

Resource ID and field names confirmed 2026-10-13 (see docs/data_sources.md).
The dataset has ~905k rows, so each page of PAGE_SIZE rows is written to GCS
as soon as it arrives instead of holding everything in memory.
"""

import json
import os
from datetime import datetime, timedelta, timezone

try:  # Airflow 3 (current Astro Runtime)
    from airflow.sdk import dag, task
except ImportError:  # Airflow 2
    from airflow.decorators import dag, task

CKAN_URL = "https://data.boston.gov/api/3/action/datastore_search"
RESOURCE_ID = os.getenv("CKAN_INSPECTIONS_RESOURCE_ID", "4582bec6-2b4f-4f9e-bc55-cbaa73117f4c")
BUCKET = os.getenv("GCS_LANDING_BUCKET", "ba882-team10-inspections-landing")
PROJECT = os.getenv("GCP_PROJECT_ID", "ba882-team10-inspections")
RAW_TABLE = f"{PROJECT}.raw.food_inspections"
PAGE_SIZE = 10_000


def _session():
    """HTTP session that retries transient API errors (timeouts, 5xx, 429)."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


@dag(
    schedule="@daily",
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,  # never run two full downloads at once
    dagrun_timeout=timedelta(hours=1),
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ingestion", "inspections"],
)
def ingest_food_inspections():
    @task
    def extract_to_gcs(ds=None, ts=None) -> dict:
        """Page through the CKAN API, writing each page to GCS as its own NDJSON file."""
        from google.cloud import storage

        bucket = storage.Client(project=PROJECT).bucket(BUCKET)
        prefix = f"raw/food_inspections/load_date={ds}"

        # Clear files from an earlier attempt of this same run so retries don't duplicate rows
        for old in bucket.list_blobs(prefix=prefix + "/"):
            old.delete()

        http = _session()
        offset, page, total, fields = 0, 0, 0, None
        while True:
            resp = http.get(
                CKAN_URL,
                params={
                    "resource_id": RESOURCE_ID,
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "sort": "_id",  # stable order so pages don't overlap
                },
                timeout=180,
            )
            resp.raise_for_status()
            result = resp.json()["result"]
            records = result["records"]
            if not records:
                break
            if fields is None:
                fields = [f["id"] for f in result["fields"]]

            lines = "\n".join(json.dumps({**r, "_loaded_at": ts}) for r in records)
            bucket.blob(f"{prefix}/part-{page:05d}.json").upload_from_string(
                lines, content_type="application/x-ndjson"
            )
            total += len(records)
            print(f"page {page}: {len(records)} rows (running total {total})")
            offset += PAGE_SIZE
            page += 1

        if total == 0:
            raise ValueError("CKAN returned no records; check the resource ID")
        return {"uri": f"gs://{BUCKET}/{prefix}/part-*.json", "fields": fields, "rows": total}

    @task
    def load_to_bigquery(extract: dict) -> None:
        from google.cloud import bigquery

        # Every CKAN column arrives as text; keep raw as STRING and cast in dbt staging.
        schema = [
            bigquery.SchemaField(name, "INTEGER" if name == "_id" else "STRING")
            for name in extract["fields"]
        ] + [bigquery.SchemaField("_loaded_at", "TIMESTAMP")]

        client = bigquery.Client(project=PROJECT)
        job = client.load_table_from_uri(
            extract["uri"],
            RAW_TABLE,
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=schema,
                write_disposition="WRITE_TRUNCATE",  # full refresh for now; incremental is issue #7
            ),
        )
        job.result()
        loaded = client.get_table(RAW_TABLE).num_rows
        print(f"Loaded {loaded} rows into {RAW_TABLE} (extracted {extract['rows']})")
        if loaded != extract["rows"]:
            raise ValueError(f"Row count mismatch: extracted {extract['rows']}, loaded {loaded}")

    load_to_bigquery(extract_to_gcs())


ingest_food_inspections()
