# Team Roles and Responsibilities

> **Status: DRAFT, for team discussion.** Put your name next to the role you want (and a backup role), then we finalize at our next meeting. The syllabus requires that each member has an assigned role, and that we track the project on GitHub. Our teammates' assessment is 30% of the project grade, so ownership matters.

Our project outline lists 5 roles. With 6 people, we split the old "Project lead and app" role into **Project lead & DevOps** and **BI & app**, since each is a full job.

## Role summary

| # | Role | Owner | Backup | GitHub label |
|---|---|---|---|---|
| 1 | Project lead & DevOps | TBD | TBD | `area: infra`, `area: pm` |
| 2 | Data ingestion | TBD | TBD | `area: ingestion` |
| 3 | Data warehouse (dbt) | TBD | TBD | `area: warehouse` |
| 4 | BI & app | TBD | TBD | `area: app-bi` |
| 5 | Machine learning | Bruce | TBD | `area: ml` |
| 6 | Generative AI | TBD | TBD | `area: genai` |

## Responsibilities in detail

### 1. Project lead & DevOps
- Owns the GitHub Project board: weekly triage, milestones, keeping issues current
- Runs weekly standups and keeps meeting notes in `docs/meetings/`
- Sets up the shared GCP project, IAM for all members, service accounts and Secret Manager
- Infrastructure as Code with Terraform (`infra/terraform/`): buckets, BigQuery datasets, service accounts
- CI with GitHub Actions (linting, `dbt parse`, tests on every pull request)
- Coordinates the Phase 1 and final presentations and the AI-usage appendix
- **Heaviest in:** setup and every presentation week

### 2. Data ingestion
- Airflow DAGs on Astronomer for all sources: inspections, licenses, 311, static neighborhood/ACS data
- Incremental loads from the data.boston.gov (CKAN) API into GCS, then raw BigQuery tables
- Handles the risks: confirm inspection data is still current; adapt to the new 311 system schema
- Retries, failure alerts and data freshness checks in the pipeline
- Later: the scheduled batch-scoring DAG (with ML) and the LLM batch DAG (with GenAI)
- **Heaviest in:** Phase 1

### 3. Data warehouse (dbt)
- dbt project: sources, staging, intermediate and mart models in BigQuery
- Matching establishments across inspections and licenses (license number, name/address cleanup)
- Data tests (unique, not null, relationships, accepted values), source freshness, model contracts
- dbt docs and data dictionary
- Builds the ML feature mart together with the ML owner in Phase 2
- **Heaviest in:** Phase 1 and early Phase 2

### 4. BI & app
- Phase 1 dashboard of inspection trends (Superset, Metabase, Looker Studio or Streamlit)
- Automated Quarto reports (pipeline health, model performance)
- Phase 3 Streamlit app: look up a restaurant, see its risk score and LLM summary; deployed on Cloud Run
- Demo flows for presentations and for the stakeholder team that evaluates us
- **Heaviest in:** end of Phase 1 and Phase 3

### 5. Machine learning
- EDA and a careful target definition: "fails next routine inspection" with no data leakage
- Features: violation history, days since last inspection, license type, nearby 311 complaints
- Training and experiment tracking with MLflow; time-based train/test split; baseline vs. tuned models
- Model deployment (Cloud Run or Vertex AI) and scheduled risk-score refresh
- Model monitoring and evaluation write-up
- **Heaviest in:** Phase 2

### 6. Generative AI
- Owns secondary data sources early on (311 mapping, ACS, neighborhoods) to support ingestion in Phase 1
- LLM tagging of violations by theme (pests, temperature control, hygiene, ...) with a labeled evaluation set
- Plain-English restaurant summaries; prompt versioning in `genai/prompts/`
- Cost and caching controls for LLM calls; feeds tags back to ML as new features
- Optional stretch: RAG / Q&A over violation history with a vector store
- **Heaviest in:** Phase 3

## Ground rules
- Everyone contributes in every phase. When your role is quiet, pick up issues in the busiest area.
- Every pull request gets one reviewer who is **not** the author.
- Each person keeps their own work visible on GitHub (issues assigned, commits, reviews), since peer and instructor evaluation will look at it.
- Log meaningful AI-assistant use in [docs/ai_usage_log.md](docs/ai_usage_log.md) for the required appendix.
