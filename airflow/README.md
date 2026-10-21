# Airflow (Astronomer)

Owner: **Data ingestion** (see [TEAM.md](../TEAM.md))

## First-time setup
This folder holds our DAGs. To turn it into a full Astronomer project, run once from this folder:

```bash
brew install astro          # or see https://www.astronomer.io/docs/astro/cli/install-cli
cd airflow
astro dev init              # adds Dockerfile, packages.txt, etc. Keep our dags/ folder
astro dev start             # local Airflow at http://localhost:8080
```

Commit the generated `Dockerfile`, `packages.txt` and `requirements.txt`. Don't commit `airflow_settings.yaml` (it can hold connections and secrets).

## DAGs
| DAG | Schedule | Sources → BigQuery |
|---|---|---|
| `raw_api_ingest` | daily, 7:30 AM ET | data.boston.gov API → `gs://<bucket>/raw/<source>/load_date=.../` → `raw.food_inspections`, `raw.requests_311_legacy`, `raw.requests_311_new`, `raw.food_licenses` |

Each source is its own extract → load pair inside the DAG, so one failing doesn't block the others. To add a source, add a `Source(...)` entry to `SOURCES` in `dags/raw_api_ingest.py`.

Static reference data (neighborhood boundaries, Census ACS) lives in dbt seeds, not in Airflow.

For a full history reload, trigger the DAG with `full_refresh = true`.
