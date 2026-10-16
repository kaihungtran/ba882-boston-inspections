# AI-Assistant Usage Log

The syllabus requires an appendix documenting the prompts and outputs that supported our work, including the tool and version used. Add a row whenever an AI tool meaningfully shaped code, analysis or writing. Fact-check the output and note what you changed.

| Date | Member | Tool & version | What we asked (prompt summary) | What it produced | How we verified / changed it |
|---|---|---|---|---|---|
| 2026-10-06 | Kai Tran | Claude (claude-opus-5-5) | Read the syllabus and project outline; propose 6 team roles, repo structure and an issue backlog | This repo scaffold, TEAM.md role draft, starter DAG and dbt files, seeded issues | Roles to be discussed and finalized by the team; starter code is placeholder and must be checked against the real API fields |
| 2026-10-16 | Bruce | Claude Code (claude-opus-5-5) | Write an ML notebook: EDA, recency check, target definition, leakage-safe features and time-split baselines from the raw GCS data | `ml/notebooks/01_eda_target_baseline.ipynb` | Executed end to end on mock data shaped like the CKAN feeds; column names and folder names still to confirm against the real bucket |
