"""Daily raw ingestion: Analyze Boston API -> Cloud Storage -> BigQuery (raw).

All Analyze Boston API sources for the project.
One extract -> load pair per source. Each API page (10,000 rows) becomes one file:

  gs://<bucket>/raw/<source>/load_date=YYYY-MM-DD/part-00000.json, part-00001.json, ...   (NDJSON)

then all parts load into BigQuery raw.<source>, partitioned by _load_date.
Each run replaces that day's files and partition, so reruns are safe.

Output tables: raw.food_inspections, raw.requests_311_legacy, raw.requests_311_new, raw.food_licenses
Neighborhood boundaries and Census ACS are static, so they live in dbt seeds instead.

The first run of an incremental source (table missing) or a manual run with
full_refresh=true pulls the entire history.
Raw: values are kept exactly as the API returns them (as text); only _load_date is added.
"""
import json
import logging
import re
from dataclasses import dataclass
from datetime import timedelta

import pendulum
import requests
from airflow.sdk import Param, dag, get_current_context, task

log = logging.getLogger(__name__)

# ---- Settings ----
PROJECT = "ba882-team10-inspections"
BUCKET = "ba882-team10-inspections-landing"
RAW_DATASET = "raw"
GCS_PREFIX = "raw"
# ------------------

LOCAL_TZ = pendulum.timezone("America/New_York")
CKAN_API = "https://data.boston.gov/api/3/action"
PAGE_SIZE = 10_000          # one page = one part file
TIMEOUT = 300
VALID_COLUMN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Source:
    name: str
    mode: str                          # "incremental", "full" or "file"
    resource_id: str | None = None
    date_column: str | None = None
    lookback_days: int = 30
    resource_name: str | None = None   # yearly files whose ID changes every January


SOURCES = [
    # Food Establishment Inspections: ~905k rows; first run pulls all, then the last 30 days daily.
    Source("food_inspections", "incremental", date_column="resultdttm",
           resource_id="4582bec6-2b4f-4f9e-bc55-cbaa73117f4c"),
    # 311, old system: one file per year; rodent and food-establishment complaints are here.
    Source("requests_311_legacy", "incremental", date_column="open_dt",
           resource_name="311 Service Requests - {year}"),
    # 311, new system (since Aug 2025), different columns from the old one.
    Source("requests_311_new", "incremental", date_column="open_date",
           resource_id="254adca6-64ab-4c5c-9fc0-a6da622be185"),
    # Active Food Establishment Licenses: small, statuses change, so pull it all each day.
    Source("food_licenses", "full", resource_id="f1e13724-284d-478c-b8bc-ef042aa5b70b"),
]


# ---------- Analyze Boston API ----------

def _ckan(action: str, **params) -> dict:
    r = requests.get(f"{CKAN_API}/{action}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    body = r.json()
    if not body.get("success"):
        raise RuntimeError(f"Analyze Boston {action} failed: {body.get('error')}")
    return body["result"]


def _resource_ids(source: Source, since: str | None, load_date: str) -> list[str]:
    """Fixed ID, or the yearly 311 files covering the window (looked up by name, case-insensitive)."""
    if source.resource_id:
        return [source.resource_id]
    last_year = pendulum.parse(load_date).year
    first_year = pendulum.parse(since).year if since else last_year
    by_name = {(r.get("name") or "").strip().lower(): r["id"]
               for r in _ckan("package_show", id="311-service-requests")["resources"]}
    ids = [by_name.get(source.resource_name.format(year=y).lower())
           for y in range(first_year, last_year + 1)]
    ids = [i for i in ids if i]
    if not ids:
        raise RuntimeError(f"{source.name}: no resource named like {source.resource_name!r}")
    return ids


def fetch_pages(resource_id: str, date_column: str | None, since: str | None):
    """Yield pages of PAGE_SIZE rows from the API, ordered by _id."""
    if since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        raise ValueError(f"since must be YYYY-MM-DD, got {since!r}")
    where = f"\"{date_column}\" >= '{since}' AND " if since and date_column else ""
    last_id = 0
    while True:
        sql = (f'SELECT * FROM "{resource_id}" WHERE {where}"_id" > {last_id} '
               f'ORDER BY "_id" LIMIT {PAGE_SIZE}')
        rows = _ckan("datastore_search_sql", sql=sql)["records"]
        if rows:
            yield rows
        if len(rows) < PAGE_SIZE:
            return
        last_id = rows[-1]["_id"]


def _raw(value):
    """The API's value as text, unchanged. None stays null."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value) if isinstance(value, (dict, list)) else str(value)


# ---------- Google Cloud ----------

def _credentials():
    """The Airflow Google connection if usable, else default credentials."""
    try:
        from airflow.providers.google.common.hooks.base_google import GoogleBaseHook

        return GoogleBaseHook(gcp_conn_id="google_cloud_default").get_credentials_and_project_id()[0]
    except Exception as exc:
        import google.auth

        log.info("Airflow connection google_cloud_default not usable (%s); using default credentials", exc)
        return google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])[0]


def _bucket():
    from google.cloud import storage

    return storage.Client(project=PROJECT, credentials=_credentials()).bucket(BUCKET)


def _bigquery():
    from google.cloud import bigquery

    return bigquery.Client(project=PROJECT, credentials=_credentials())


def table_exists(name: str) -> bool:
    from google.api_core.exceptions import NotFound

    try:
        _bigquery().get_table(f"{PROJECT}.{RAW_DATASET}.{name}")
        return True
    except NotFound:
        return False


def _clear_prefix(bucket, prefix: str) -> None:
    """Delete files from an earlier run of the same day so reruns don't mix old and new parts."""
    for blob in bucket.list_blobs(prefix=prefix):
        blob.delete()


def _load_date() -> str:
    ctx = get_current_context()
    run = ctx["dag_run"]
    when = ctx.get("data_interval_end") or ctx.get("logical_date") or run.run_after
    return pendulum.instance(when).in_timezone(LOCAL_TZ).to_date_string()


# ---------- DAG ----------

@dag(
    dag_id="raw_api_ingest",
    schedule="30 7 * * *",                    # 7:30 AM New York time, daily
    start_date=pendulum.datetime(2026, 10, 1, tz=LOCAL_TZ),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    params={"full_refresh": Param(False, type="boolean",
                                  description="Pull full history for every source")},
    tags=["ingestion", "raw", "boston"],
)
def raw_api_ingest():

    for src in SOURCES:

        @task(task_id=f"extract_{src.name}_to_gcs")
        def extract(source=src) -> dict:
            ctx = get_current_context()
            load_date = _load_date()
            since = None
            if source.mode == "incremental":
                full = ctx["params"].get("full_refresh") or not table_exists(source.name)
                if not full:
                    since = (pendulum.parse(load_date) - timedelta(days=source.lookback_days)).to_date_string()

            bucket = _bucket()
            prefix = f"{GCS_PREFIX}/{source.name}/load_date={load_date}/"
            _clear_prefix(bucket, prefix)

            part, rows, columns = 0, 0, None
            for rid in _resource_ids(source, since, load_date):
                for page in fetch_pages(rid, source.date_column, since):
                    lines = []
                    for row in page:
                        row.pop("_full_text", None)
                        if columns is None:
                            columns = list(row)
                            bad = [c for c in columns if not VALID_COLUMN.match(c)]
                            if bad:
                                raise ValueError(f"Column names BigQuery can't accept: {bad}")
                        record = {k: _raw(v) for k, v in row.items()}
                        record["_load_date"] = load_date
                        lines.append(json.dumps(record, ensure_ascii=False))
                    data = ("\n".join(lines) + "\n").encode("utf-8")
                    blob = bucket.blob(f"{prefix}part-{part:05d}.json")
                    blob.upload_from_string(data, content_type="application/x-ndjson", timeout=TIMEOUT)
                    rows += len(page)
                    part += 1
                    print(f"page {part}: {len(page)} rows (running total {rows}) -> {blob.name}")

            uri = f"gs://{BUCKET}/{prefix}part-*.json"
            print(f"{source.name}: {rows} rows in {part} files since={since or 'ALL'} -> {uri}")
            return {"rows": rows, "files": part, "uri": uri, "columns": columns, "load_date": load_date}

        @task(task_id=f"load_{src.name}_to_bigquery")
        def load(meta: dict, source=src) -> int:
            from google.cloud import bigquery

            if meta["rows"] == 0:
                print(f"{source.name}: nothing new, skipping load")
                return 0
            bq = _bigquery()
            bq.create_dataset(bigquery.Dataset(f"{PROJECT}.{RAW_DATASET}"), exists_ok=True)
            schema = [bigquery.SchemaField(c, "STRING") for c in meta["columns"]]
            schema.append(bigquery.SchemaField("_load_date", "DATE"))
            table = bigquery.Table(f"{PROJECT}.{RAW_DATASET}.{source.name}", schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field="_load_date")
            bq.create_table(table, exists_ok=True)

            partition = meta["load_date"].replace("-", "")
            job = bq.load_table_from_uri(
                meta["uri"],
                f"{PROJECT}.{RAW_DATASET}.{source.name}${partition}",
                job_config=bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                    schema=schema,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
                ),
            )
            job.result()
            if job.output_rows != meta["rows"]:
                raise ValueError(f"{source.name}: wrote {meta['rows']} rows to GCS but loaded {job.output_rows}")
            print(f"Loaded {job.output_rows} rows from {meta['files']} files into "
                  f"{RAW_DATASET}.{source.name}${meta['load_date']}")
            return job.output_rows

        load(extract())


raw_api_ingest()
