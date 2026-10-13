# Runbook: Extract & Load to GCP with Astronomer

Goal: the `ingest_food_inspections` DAG pulls from data.boston.gov daily, lands raw JSON in GCS, and loads it into BigQuery `raw.food_inspections`, running locally first and then on Astronomer.

**Who does what:** steps 1–3 by the Project lead (GCP owner), steps 4–8 by Data ingestion. Steps 1–3 only need doing once for the team.

Replace these placeholders everywhere:

| Placeholder | Example |
|---|---|
| `PROJECT_ID` | `ba882-team10-inspections` (our project) |
| `BUCKET` | `ba882-team10-inspections-landing` (our bucket) |
| `REGION` | `US` |

**Status (10/13):** project, `airflow-sa` service account, its 3 roles and the key are done (Kai).

---

## 0. Prerequisites (each person, once)

- GCP account with the course credits (see the *Cloud Setup* doc on Blackboard)
- Astronomer account (details on Blackboard)
- Docker Desktop installed and **running**
- `gcloud` CLI: https://cloud.google.com/sdk/docs/install (or use Cloud Shell for steps 1–3)
- Astro CLI: `brew install astro` (Mac) or `winget install -e --id Astronomer.Astro` (Windows)

```bash
gcloud auth login
astro version          # confirms the CLI works
```

## 1. Create the GCP project and enable APIs

```bash
gcloud projects create PROJECT_ID --name="BA882 Team 10"
gcloud config set project PROJECT_ID
# Link billing / course credits in the console: Billing → Link a billing account

gcloud services enable bigquery.googleapis.com storage.googleapis.com \
  secretmanager.googleapis.com run.googleapis.com aiplatform.googleapis.com
```

Add teammates: Console → IAM → Grant access → their BU Google emails with role **Editor** (fine for a class project).

## 2. Create the landing bucket and BigQuery datasets

```bash
gcloud storage buckets create gs://BUCKET --location=US --uniform-bucket-level-access

bq --location=US mk --dataset PROJECT_ID:raw
bq --location=US mk --dataset PROJECT_ID:staging
bq --location=US mk --dataset PROJECT_ID:marts
```

> Use one location for everything. The dbt profile uses `US`, so datasets are `US`. A `us-east1` bucket can still load into `US` datasets.

## 3. Create the Airflow service account and key

```bash
gcloud iam service-accounts create airflow-sa --display-name="Airflow (Astronomer)"

cd ~                                   # keep the key OUT of any git repo folder
PROJECT=ba882-team10-inspections
SA=airflow-sa@$PROJECT.iam.gserviceaccount.com
for ROLE in roles/storage.objectAdmin roles/bigquery.dataEditor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA" --role="$ROLE" --condition=None --quiet
done

gcloud iam service-accounts keys create ~/gcp-key.json --iam-account=$SA
```

Share `gcp-key.json` with the ingestion owner **privately** (DM, not Slack channel, never git). It is gitignored by the pattern `gcp-key*.json`.

> If your org blocks key creation ("constraints/iam.disableServiceAccountKeyCreation"), ask the TA. The fallback is Astronomer's workload identity, which is more setup.

## 4. Initialize the Astronomer project (once, then commit)

> Run this **inside the repo's `airflow/` folder**, never in your home folder. `astro dev init` turns whatever folder you're in into an Astro project.

```bash
cd ~/ba882-boston-inspections/airflow
cp requirements.txt requirements.keep    # astro init may overwrite it
astro dev init                           # say yes if asked about a non-empty folder
cat requirements.keep >> requirements.txt && rm requirements.keep
sort -u requirements.txt -o requirements.txt
```

Commit the generated `Dockerfile`, `packages.txt`, `requirements.txt` and `.dockerignore` on a branch (`ingestion/6-astro-setup`) and open a PR.

## 5. Find the CKAN resource ID (issue #4)

1. Open https://data.boston.gov/dataset/food-establishment-inspections
2. Click the data file → **Data API** button. The `resource_id` is in the example URL.
3. Test it in a browser:
   `https://data.boston.gov/api/3/action/datastore_search?resource_id=RESOURCE_ID&limit=5`
4. Check the newest record: add `&sort=resultdttm desc`. **Record the latest date in `docs/data_sources.md`.** If it's months old, tell the team immediately.
5. While there, compare the returned field names to `dbt/models/staging/stg_food_inspections.sql` and fix any that differ.

## 6. Wire up credentials and config locally

```bash
mv ~/Downloads/gcp-key.json airflow/include/gcp-key.json
```

Create `airflow/.env` (gitignored; Astro loads it automatically):

```bash
GOOGLE_APPLICATION_CREDENTIALS=/usr/local/airflow/include/gcp-key.json
GCP_PROJECT_ID=PROJECT_ID
GCS_LANDING_BUCKET=BUCKET
CKAN_INSPECTIONS_RESOURCE_ID=RESOURCE_ID
```

Double-check nothing secret is staged: `git status` should **not** list `gcp-key.json` or `.env`.

## 7. Run and test locally

```bash
cd airflow
astro dev start          # first build takes a few minutes
```

1. Open http://localhost:8080 (login `admin` / `admin` if prompted)
2. Find `ingest_food_inspections` → unpause it → **Trigger**
3. Watch both tasks go green. If one fails, click it → **Logs**.

Common errors:

| Error | Fix |
|---|---|
| `DefaultCredentialsError` | `.env` path is wrong, or the key isn't in `airflow/include/` |
| `403 ... storage.objects.create` | Service account missing `storage.objectAdmin` (step 3) |
| `403 ... bigquery.jobs.create` | Missing `bigquery.jobUser` |
| `404 Not found: Dataset PROJECT_ID:raw` | Step 2 not done, or dataset location mismatch |
| CKAN returns `success: false` | Wrong resource ID (step 5) |
| DAG doesn't appear | Import error: run `astro dev parse` |

Stop with `astro dev stop`. After editing `requirements.txt`, run `astro dev restart`.

## 8. Verify the load

```bash
gcloud storage ls gs://BUCKET/raw/food_inspections/
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) AS n, MAX(resultdttm) AS latest FROM `PROJECT_ID.raw.food_inspections`'
```

Screenshot both for the Phase 1 slides.

## 9. Deploy to Astronomer

```bash
astro login
astro deployment create --name ba882-team10 --runtime-version <latest shown in Astro UI>
# or create the deployment in the Astro UI, which is easier the first time
```

In the Astro UI → your deployment → **Environment Variables**, add the same four values from step 6. For the key, Astronomer can't see your laptop's `include/` file, so either:

- **Option A (simplest):** add `GOOGLE_APPLICATION_CREDENTIALS_JSON` as a **secret** env var with the full key contents, and we add three lines to the DAG to write it to a temp file (ask Kai/Claude to make this PR), **or**
- **Option B:** create an Airflow **Connection** (Admin → Connections → Google Cloud, paste the key JSON) and switch the DAG to use `GCSHook` / `BigQueryHook`.

Then deploy:

```bash
cd airflow
astro deploy
```

Trigger the DAG in the Astro UI and repeat step 8.

## 10. Repeat for the other sources

Copy `ingest_food_inspections.py` for licenses (#8) and 311 (#9), changing the resource ID, GCS path and raw table name. After the first full backfill works, switch inspections to incremental loads (filter on `resultdttm` greater than the max already in BigQuery, `WRITE_APPEND`).

Next stop: dbt reads `raw.*` (issue #11).
