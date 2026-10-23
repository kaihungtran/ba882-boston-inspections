# App & Dashboard

Owner: **BI & app** (see [TEAM.md](../TEAM.md))

- Phase 1: inspection-trends dashboard (Streamlit, this folder)
- Phase 3: Streamlit app to look up a restaurant's risk score and LLM summary, deployed on Cloud Run

## Pages

| Page | Data |
|---|---|
| Pass/fail trends | `stg_food_inspections` (stub data for now) |
| Results by neighborhood (map + table) | `stg_food_inspections` (stub) + `stg_neighborhoods` boundaries (real) |
| Top violations | `stg_food_inspections` (stub) |
| Food-safety 311 (map + monthly) | `stg_311_requests` where `is_food_safety`, + `stg_neighborhoods` (real) |

`raw.food_inspections` isn't in BigQuery yet, so the inspection pages use randomly generated
rows shaped like `stg_food_inspections` (see `stub_data.py`). Every stub page shows a **STUB DATA**
banner. Set `USE_STUB_INSPECTIONS=false` once `stg_food_inspections` is built in your dataset.

## Setup

From the repo root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

gcloud auth application-default login     # BigQuery access; no key files
cp .env.example .env                      # never commit .env
```

Set these in `.env`:

| Variable | Example | Notes |
|---|---|---|
| `GCP_PROJECT_ID` | `ba882-team10-inspections` | |
| `BQ_STAGING_DATASET` | `dev_<you>_staging` | Where your `stg_*` models are built. The shared `staging` dataset is empty until dbt runs in prod |
| `USE_STUB_INSPECTIONS` | `true` | `true` until `stg_food_inspections` exists |

## Run

```bash
streamlit run app/app.py
```

Opens at http://localhost:8501. Query results are cached for an hour (`st.cache_data`), so
clicking around doesn't rescan BigQuery. Use **Clear cache** in the sidebar to force a refresh.

## Layout

| File | What it does |
|---|---|
| `app.py` | Entry point and page navigation |
| `views/` | One file per page |
| `queries.py` | All SQL. Table names come from `.env`; no dataset names are hardcoded |
| `data.py` | Picks BigQuery or stub data for each page |
| `bq.py` | BigQuery client (application default credentials) and cached query runner |
| `stub_data.py` | STUB inspection rows + pandas versions of the inspection queries |
| `charts.py` | Colors, Altair charts, the neighborhood choropleth (pydeck) |
| `config.py` | Reads and validates `.env` |

When the marts land (`fct_inspections`, `dim_neighborhood`), point the inspection queries in
`queries.py` at them instead of rolling `stg_food_inspections` up to inspections in the app.
