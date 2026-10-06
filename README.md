# Predicting Food Safety Risk to Prioritize Boston Restaurant Inspections

BA882 Deploying Analytics Pipelines · Team Project · Fall 2026

We are building a cloud data pipeline and a predictive model that scores each Boston food establishment's risk of failing its next inspection. The goal is to help the city's Health Division decide which places to visit first and catch serious violations sooner. Chicago's [food inspection model](https://github.com/Chicago/food-inspections-evaluation) is the precedent.

## Team

See [TEAM.md](TEAM.md) for roles, owners and responsibilities.

## Timeline

| Milestone | Due | What we show |
|---|---|---|
| Phase 0: Setup | Tue 10/13 | Roles assigned, GCP project shared, data access confirmed |
| Phase 1: Data Pipeline | **Tue 10/27 (presentation)** | Daily Airflow ingestion, dbt warehouse, inspection-trends dashboard |
| Phase 2: Machine Learning | Tue 11/24 (internal) | Deployed model, scheduled risk scores |
| Phase 3: Generative AI + Final | **Tue 12/8 (final presentation)** | LLM violation tags and summaries, Streamlit app |

## Architecture

```
data.boston.gov / Census API
        │  (Airflow on Astronomer, daily)
        ▼
GCS landing bucket (raw JSON/CSV, partitioned by load date)
        │
        ▼
BigQuery  raw  →  staging  →  intermediate  →  marts      (dbt)
                                               │
                 ┌─────────────────────────────┼──────────────────────────┐
                 ▼                             ▼                          ▼
        Dashboard (Phase 1)        ML training + scoring (Phase 2)   LLM tagging + summaries (Phase 3)
                                               │                          │
                                               └──────────► Streamlit app ◄┘
```

## Data sources

| Source | Updates | Role |
|---|---|---|
| [Food Establishment Inspections](https://data.boston.gov/dataset/food-establishment-inspections) | Daily | Core: inspection results and violations |
| [311 Service Requests](https://data.boston.gov/dataset/311-service-requests) | Daily | Nearby complaints (rodents, sanitation) as risk signals |
| [Active Food Establishment Licenses](https://data.boston.gov/dataset/active-food-establishment-licenses) | Daily | Master list of establishments and license types |
| [Neighborhood boundaries](https://data.boston.gov/dataset/boston-neighborhood-boundaries-approximated-by-2020-census-tracts) and [Census ACS](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Static / annual | Neighborhood context |

More detail in [docs/data_sources.md](docs/data_sources.md).

## Repository layout

| Folder | Contents | Owner role |
|---|---|---|
| `airflow/` | Astronomer project: ingestion DAGs, dbt orchestration, scoring DAGs | Data ingestion |
| `dbt/` | dbt project: staging, intermediate and mart models, tests, docs | Data warehouse |
| `ml/` | EDA notebooks, feature engineering, training, evaluation, deployment code | Machine learning |
| `genai/` | Prompts, LLM tagging and summary pipeline, evaluations | Generative AI |
| `app/` | Streamlit app and dashboard code | BI & app |
| `reports/` | Quarto reports (automated pipeline and model reports) | BI & app |
| `infra/terraform/` | GCP buckets, datasets, service accounts as code | Project lead & DevOps |
| `docs/` | Architecture notes, data dictionary, AI-usage appendix | Everyone |

## How we work

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first pull request. In short: every piece of work is a GitHub issue, every change goes through a branch and a pull request, and every pull request is reviewed by a second teammate.

## Getting started

1. Clone the repo and create a Python 3.11+ virtual environment.
2. Ask the project lead for access to the shared GCP project.
3. Authenticate locally: `gcloud auth application-default login`
4. Copy `.env.example` to `.env` and fill in values. **Never commit `.env` or service-account keys.**
5. Follow the README inside the folder you're working in (`airflow/`, `dbt/`, ...).
