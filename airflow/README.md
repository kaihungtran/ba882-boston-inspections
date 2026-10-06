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
| DAG | Schedule | Source → target |
|---|---|---|
| `ingest_food_inspections` | daily | CKAN API → `gs://<bucket>/raw/food_inspections/` → `raw.food_inspections` |
| `ingest_food_licenses` | daily | CKAN API → GCS → `raw.food_licenses` |
| `ingest_311_requests` | daily | CKAN API (filtered types) → GCS → `raw.requests_311` |
| `load_static_reference` | manual | Neighborhood boundaries + ACS → `raw.*` |
| `dbt_build` | daily, after ingestion | runs `dbt build` |

`dags/ingest_food_inspections.py` is a starter skeleton to copy for the other sources.
