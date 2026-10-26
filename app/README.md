# App & Dashboard

Owner: **BI & app** (see [TEAM.md](../TEAM.md))

- Phase 1: inspection-trends dashboard (Streamlit, this folder)
- Phase 3: Streamlit app to look up a restaurant's risk score and LLM summary, deployed on Cloud Run

## Pages

| Page | Data |
|---|---|
| Pass/fail trends | `stg_food_inspections` |
| Results by neighborhood (map + table) | `stg_food_inspections` + `stg_neighborhoods` boundaries |
| Top violations | `stg_food_inspections` |
| Food-safety 311 (map + monthly) | `stg_311_requests` where `is_food_safety`, + `stg_neighborhoods` |

If the dataset you point at has no `stg_food_inspections` yet, set `USE_STUB_INSPECTIONS=true`
and the inspection pages use randomly generated rows in the same shape (see `stub_data.py`),
with a **STUB DATA** notice on every such page.

The app has a light and a dark theme. Viewers switch (or follow their system setting) from the
⋮ menu → Settings.

## Run locally

From the repo root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

gcloud auth application-default login     # BigQuery access; no key files
cp .env.example .env                      # never commit .env
streamlit run app/app.py                  # http://localhost:8501
```

Set these in `.env`:

| Variable | Example | Notes |
|---|---|---|
| `GCP_PROJECT_ID` | `ba882-team10-inspections` | |
| `BQ_STAGING_DATASET` | `dev_<you>_staging` | Where your `stg_*` models are built. The shared `staging` dataset is empty until dbt runs in prod |
| `USE_STUB_INSPECTIONS` | `false` | `true` only if your dataset has no `stg_food_inspections` |

Run from the repo root so Streamlit picks up `.streamlit/config.toml` (the theme). Query results
are cached for an hour (`st.cache_data`), so clicking around doesn't rescan BigQuery. **Clear
cache** in the sidebar forces a refresh.

## Deploy to Streamlit Community Cloud

The hosted copy can't use anyone's personal Google login, so it authenticates with a
service-account key stored in the app's secrets. Nothing secret goes in the repo.

1. **Service account** (needs IAM rights on the GCP project; ask the project lead if you
   don't have them):
   ```bash
   P=ba882-team10-inspections
   gcloud iam service-accounts create streamlit-dashboard --project $P --display-name "Streamlit dashboard"
   SA=streamlit-dashboard@$P.iam.gserviceaccount.com
   gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.jobUser
   gcloud projects add-iam-policy-binding $P --member serviceAccount:$SA --role roles/bigquery.dataViewer
   gcloud iam service-accounts keys create ~/streamlit-dashboard-key.json --iam-account $SA
   ```
   `dataViewer` at project level reads every dataset. Narrow it to the staging dataset with
   `bq add-iam-policy-binding` if you prefer.
2. **Push the branch** and open https://share.streamlit.io → *Create app* → this repo, the
   branch, main file path `app/app.py`. Under *Advanced settings* pick **Python 3.11**.
   The repo belongs to `kaihungtran`, so GitHub may ask the repo owner to approve the
   Streamlit GitHub app the first time.
3. **Secrets**: in the app's *Settings → Secrets*, paste
   [.streamlit/secrets.toml.example](../.streamlit/secrets.toml.example) with the values
   filled in from the key file. Then delete the key file from your laptop.
4. Deploy. The app's URL is `https://<name>.streamlit.app`. Anyone with the link can open it.

Dependencies come from the root `requirements.txt`, which points at `app/requirements.txt`.

## Layout

| File | What it does |
|---|---|
| `app.py` | Entry point, sidebar and page navigation |
| `views/` | One file per page |
| `queries.py` | All SQL. Table names come from settings; no dataset names are hardcoded |
| `data.py` | Picks BigQuery or stub data for each page |
| `bq.py` | BigQuery client (secrets key or application default credentials) and cached query runner |
| `stub_data.py` | STUB inspection rows + pandas versions of the inspection queries |
| `charts.py` | Chart palettes, Altair theme, line/bar helpers, the neighborhood choropleth (pydeck) |
| `ui.py` | Page furniture: global CSS, page headers, stat tiles, notices, sidebar |
| `config.py` | Reads settings from `.env` or Streamlit secrets and validates them |
| `../.streamlit/config.toml` | Streamlit theme, light and dark. Lives in the repo root because Streamlit reads it from the working directory |
| `../.streamlit/secrets.toml.example` | Template for the deployed app's secrets |

When the marts land (`fct_inspections`, `dim_neighborhood`), point the inspection queries in
`queries.py` at them instead of rolling `stg_food_inspections` up to inspections in the app.
