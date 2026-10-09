"""Seed the project backlog (labels, milestones, issues) with the GitHub CLI.

Run ONCE (needs `gh auth login` with admin rights on the repo):

    python scripts/seed_github.py kaihungtran/ba882-boston-inspections

Running it twice creates duplicate issues.
"""
import json
import subprocess
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else "kaihungtran/ba882-boston-inspections"


def api(method, path, body=None):
    cmd = ["gh", "api", "-X", method, f"repos/{REPO}/{path}", "--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body or {}), capture_output=True, text=True)
    if r.returncode != 0:
        print("ERR", path, r.stdout[:300], r.stderr[:300])
        return None
    return json.loads(r.stdout) if r.stdout.strip() else None


LABELS = [
    ("area: pm", "5319e7", "Project management, meetings, presentations"),
    ("area: infra", "0e8a16", "GCP, Terraform, CI/CD"),
    ("area: ingestion", "1d76db", "Airflow DAGs, API extraction, GCS/BigQuery raw loads"),
    ("area: warehouse", "0052cc", "dbt models, tests, docs"),
    ("area: app-bi", "fbca04", "Dashboard, Quarto reports, Streamlit app"),
    ("area: ml", "d93f0b", "Features, training, deployment, monitoring"),
    ("area: genai", "b60205", "LLM tagging, summaries, evals, RAG"),
    ("type: feature", "a2eeef", "New functionality"),
    ("type: bug", "d73a4a", "Something is broken"),
    ("type: research", "c5def5", "Investigation or spike"),
    ("type: chore", "ededed", "Setup, cleanup, docs"),
    ("priority: high", "e11d21", "Blocks other work or a deadline"),
    ("presentation", "f9d0c4", "Needed for a class presentation"),
]

MILESTONES = [
    ("Phase 0: Setup", "2026-10-13T23:59:00Z", "Roles assigned, GCP shared, data access confirmed"),
    ("Phase 1: Data Pipeline", "2026-10-27T19:30:00Z", "Automated pipeline + inspection-trends dashboard. Presentation Tue 10/27"),
    ("Phase 2: Machine Learning", "2026-11-24T19:30:00Z", "Deployed model with scheduled risk scores (internal target)"),
    ("Phase 3: Generative AI + Final", "2026-12-08T19:30:00Z", "LLM tags & summaries, Streamlit app. Final presentation Tue 12/8"),
]

P0, P1, P2, P3 = (m[0] for m in MILESTONES)


def body(goal, criteria, notes=""):
    s = f"## Goal\n{goal}\n\n## Acceptance criteria\n" + "\n".join(f"- [ ] {c}" for c in criteria)
    if notes:
        s += f"\n\n## Notes\n{notes}"
    return s


ISSUES = [
    # ---------------- Phase 0 ----------------
    (P0, "Assign team roles and fill in TEAM.md", ["area: pm", "type: chore", "priority: high"],
     body("Every member picks an owner role and a backup role.",
          ["All 6 roles in TEAM.md have an owner and a backup",
           "CODEOWNERS filled in with GitHub usernames",
           "Each member assigned to at least one Phase 1 issue"],
          "Draft roles are in TEAM.md. Discuss at the next team meeting.")),
    (P0, "Create GitHub Project board and protect main", ["area: pm", "type: chore", "priority: high"],
     body("Set up the board we'll be evaluated on.",
          ["Project (board view) created and linked to this repo, with columns: Backlog, Ready, In Progress, In Review, Done",
           "All issues added to the board; fields for Phase and Area",
           "Branch protection on main: PR required, 1 approval, CI must pass",
           "All 6 teammates added as collaborators"])),
    (P0, "Set up shared GCP project, IAM and service accounts", ["area: infra", "type: chore", "priority: high"],
     body("One GCP project the whole team and Astronomer can use.",
          ["Project created with billing/credits; all members have access",
           "APIs enabled: BigQuery, Cloud Storage, Secret Manager, Cloud Run, Vertex AI",
           "Service account for Airflow with least-privilege roles",
           "GCS landing bucket and BigQuery datasets raw / staging / marts created"],
          "Later codified in Terraform (see the IaC issue).")),
    (P0, "Confirm inspection data recency and API access", ["area: ingestion", "type: research", "priority: high"],
     body("The city marks the inspections dataset as legacy. Make sure it still has recent records before we build on it.",
          ["CKAN resource IDs found for inspections, licenses and 311; added to .env.example",
           "Latest inspection date, row counts and date range recorded in docs/data_sources.md",
           "Test API pull (pagination + filtering by date) works",
           "If data is stale: propose an alternative source to the team"])),
    (P0, "Investigate the new 311 system schema and transition guide", ["area: genai", "area: ingestion", "type: research"],
     body("311 is moving to a new system with a different structure.",
          ["Read the city's transition guide; document old vs new fields",
           "List of 311 request types relevant to food safety (rodents, sanitation, trash ...)",
           "Decision recorded: which 311 resource(s) we ingest"])),
    (P0, "Set up Astronomer workspace and local Airflow dev", ["area: ingestion", "type: chore"],
     body("Everyone can run DAGs locally and we can deploy to Astronomer.",
          ["`astro dev init` run in airflow/ and generated files committed",
           "Astronomer deployment created; GCP connection configured via env vars/secrets",
           "README has local setup steps verified by a second teammate"])),

    # ---------------- Phase 1 ----------------
    (P1, "Airflow DAG: food inspections → GCS → BigQuery raw", ["area: ingestion", "type: feature", "priority: high"],
     body("Daily, incremental ingestion of inspection results.",
          ["DAG runs daily on Astronomer", "Raw files land in GCS partitioned by load date",
           "Loads into raw.food_inspections with a _loaded_at column", "Incremental: only new records after the first backfill",
           "Retries and failure alerts configured"],
          "Starter skeleton: airflow/dags/ingest_food_inspections.py")),
    (P1, "Airflow DAG: active food establishment licenses", ["area: ingestion", "type: feature"],
     body("Daily snapshot of active licenses.", ["Lands in GCS + raw.food_licenses", "Runs daily", "Snapshot date column for history"])),
    (P1, "Airflow DAG: 311 service requests (food-safety types)", ["area: ingestion", "type: feature"],
     body("Daily load of relevant 311 requests.", ["Filtered to request types agreed in the 311 research issue",
                                                   "Lands in GCS + raw.requests_311", "Lat/long kept for spatial joins"])),
    (P1, "Load static reference data: neighborhoods and Census ACS", ["area: genai", "area: ingestion", "type: feature"],
     body("Neighborhood context for each establishment.", ["Neighborhood/tract boundaries in BigQuery as GEOGRAPHY",
                                                         "Selected ACS tract variables (income, population density ...) loaded",
                                                         "Load script/DAG is re-runnable"])),
    (P1, "dbt: initialize project, sources and staging models", ["area: warehouse", "type: feature", "priority: high"],
     body("Clean, typed staging layer for every raw table.", ["stg_food_inspections, stg_food_licenses, stg_requests_311, stg_neighborhoods",
                                                            "Column names and types confirmed against real raw data",
                                                            "Source freshness configured"])),
    (P1, "dbt: match establishments across inspections and licenses", ["area: warehouse", "type: feature"],
     body("One establishment key used everywhere.", ["int_ model that resolves license number / name / address",
                                                   "Match rate documented; unmatched records investigated",
                                                   "Establishments geocoded to a neighborhood"])),
    (P1, "dbt: marts for inspections, violations, establishments, neighborhoods", ["area: warehouse", "type: feature", "priority: high"],
     body("Mart tables the dashboard and ML read from.", ["dim_establishment, dim_neighborhood, fct_inspections, fct_violations",
                                                        "fct_311_nearby: complaints within X m / N days of each establishment",
                                                        "Grain of each model documented"])),
    (P1, "dbt: data tests, contracts and docs", ["area: warehouse", "type: feature"],
     body("Data quality controls the syllabus asks for.", ["unique / not_null / relationships / accepted_values tests on key columns",
                                                         "Contracts on marts used downstream", "dbt docs generated and shared"])),
    (P1, "Orchestrate dbt from Airflow after ingestion", ["area: ingestion", "area: warehouse", "type: feature"],
     body("The whole pipeline runs end to end every day.", ["dbt build runs after all ingestion DAGs succeed (Cosmos or BashOperator)",
                                                          "Failures alert the team", "One full successful daily run demonstrated"])),
    (P1, "Pipeline monitoring, observability and alerting", ["area: ingestion", "area: infra", "type: feature"],
     body("We know when the pipeline breaks or data goes stale.", ["Failure callbacks send email/Slack",
                                                                  "Freshness + row-count checks", "Simple pipeline-health view or Quarto report"])),
    (P1, "Phase 1 dashboard of inspection trends", ["area: app-bi", "type: feature", "priority: high", "presentation"],
     body("Dashboard on the marts showing inspection trends.", ["Tool chosen (Superset / Metabase / Looker Studio / Streamlit) and why",
                                                              "Pass/fail rate over time, by neighborhood and license type; top violation types; 311 overlay",
                                                              "Accessible by the stakeholder team for the demo"])),
    (P1, "Terraform: buckets, datasets, service accounts", ["area: infra", "type: feature"],
     body("Move point-and-click setup into IaC (session 6 topic).", ["GCS bucket, BigQuery datasets, service accounts in infra/terraform",
                                                                   "Remote state in GCS", "terraform plan shows no drift"])),
    (P1, "CI: lint + dbt parse on every pull request", ["area: infra", "type: chore"],
     body("CI is green and required.", ["Starter workflow in .github/workflows/ci.yml passes",
                                       "Add pytest for DAG import tests", "CI required in branch protection"])),
    (P1, "Phase 1 presentation and demo (Tue 10/27)", ["area: pm", "presentation", "priority: high"],
     body("Present progress and demo the pipeline.", ["Slides: problem, architecture, data, pipeline demo, dashboard, next steps",
                                                     "Every member presents a part", "Dry run by Sun 10/25",
                                                     "Prepare for stakeholder questions from the evaluating team"])),

    # ---------------- Phase 2 ----------------
    (P2, "EDA and target definition: fail next routine inspection", ["area: ml", "type: research"],
     body("Define exactly what we predict and avoid leakage.", ["Definition of 'routine inspection' and 'fail' documented",
                                                              "Base rate and class balance reported", "Time-based train/test split chosen"])),
    (P2, "dbt: ML feature mart", ["area: warehouse", "area: ml", "type: feature"],
     body("One row per establishment per inspection date with features as of that date.",
          ["Violation history, days since last inspection, license type, nearby 311 counts, neighborhood ACS",
           "Point-in-time correct (no future data)", "Tested and documented"])),
    (P2, "Train baseline and improved models with MLflow tracking", ["area: ml", "type: feature"],
     body("A model that beats the baseline.", ["Baseline (e.g. logistic regression) and a stronger model (e.g. gradient boosting)",
                                              "Runs tracked in MLflow", "Metrics: AUC, precision@top-k (inspector capacity), calibration"])),
    (P2, "Deploy model and schedule risk-score refresh", ["area: ml", "area: ingestion", "type: feature"],
     body("Scores refresh automatically.", ["Model served (Cloud Run or Vertex AI) or batch-scored in Airflow",
                                           "Scores written to marts.risk_scores on a schedule", "Model version recorded with each score"])),
    (P2, "Model monitoring and automated evaluation report", ["area: ml", "area: app-bi", "type: feature"],
     body("We can see if the model drifts.", ["Quarto report on model performance, rendered on a schedule",
                                             "Feature/score drift checks"])),
    (P2, "Add risk scores to the dashboard", ["area: app-bi", "type: feature"],
     body("Inspectors can see a ranked list.", ["Ranked list of highest-risk establishments", "Filter by neighborhood"])),

    # ---------------- Phase 3 ----------------
    (P3, "LLM violation theme tagging with an evaluation set", ["area: genai", "type: feature", "priority: high"],
     body("Each violation tagged by theme.", ["Theme taxonomy agreed (pests, temperature, hygiene, facilities, ...)",
                                             "Prompt versioned in genai/prompts/", "Distinct descriptions tagged once and cached",
                                             "~200 hand-labeled rows; accuracy reported", "Tags written to BigQuery"])),
    (P3, "Plain-English restaurant summaries", ["area: genai", "type: feature"],
     body("A short, factual summary per establishment.", ["Generated from recent inspection history",
                                                        "Grounded: no claims not in the data (spot-check sample)", "Refreshed on a schedule"])),
    (P3, "Use LLM tags as model features and compare", ["area: ml", "area: genai", "type: feature"],
     body("Do the GenAI features improve the model?", ["Retrain with theme features", "Before/after comparison in MLflow"])),
    (P3, "Streamlit app: restaurant lookup with risk score and summary", ["area: app-bi", "type: feature", "priority: high", "presentation"],
     body("The interface stakeholders will use.", ["Search by name/address", "Shows risk score, history, themes and summary",
                                                 "Deployed on Cloud Run with a shareable URL"])),
    (P3, "Stretch: RAG Q&A over violation history", ["area: genai", "type: research"],
     body("Ask questions like 'which restaurants in Allston had pest issues this year?'",
          ["Embeddings in a vector store", "Basic retrieval evaluation", "Hooked into the Streamlit app if time allows"])),
    (P3, "Final presentation and demo (Tue 12/8)", ["area: pm", "presentation", "priority: high"],
     body("Final end-to-end story.", ["Slides + live demo of app", "Every member presents", "AI-usage appendix complete",
                                     "Dry run by Sun 12/6"])),
    (P3, "Maintain AI-usage appendix", ["area: pm", "type: chore"],
     body("Required by the syllabus AI policy.", ["docs/ai_usage_log.md kept current by all members",
                                                 "Final appendix lists tools, versions, prompts and outputs"])),
]


def main():
    for name, color, desc in LABELS:
        api("POST", "labels", {"name": name, "color": color, "description": desc})
    ms = {}
    for title, due, desc in MILESTONES:
        m = api("POST", "milestones", {"title": title, "due_on": due, "description": desc})
        if m:
            ms[title] = m["number"]
    for milestone, title, labels, text in ISSUES:
        i = api("POST", "issues", {"title": title, "body": text, "labels": labels, "milestone": ms.get(milestone)})
        print(i["number"] if i else "FAIL", title)


if __name__ == "__main__":
    main()
