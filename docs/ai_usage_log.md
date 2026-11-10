# AI-Assistant Usage Log

The syllabus requires an appendix documenting the prompts and outputs that supported our work, including the tool and version used. Add a row whenever an AI tool meaningfully shaped code, analysis or writing. Fact-check the output and note what you changed.

| Date | Member | Tool & version | What we asked (prompt summary) | What it produced | How we verified / changed it |
|---|---|---|---|---|---|
| 2026-10-06 | Kai Tran | Claude (claude-opus-5-5) | Read the syllabus and project outline; propose 6 team roles, repo structure and an issue backlog | This repo scaffold, TEAM.md role draft, starter DAG and dbt files, seeded issues | Roles to be discussed and finalized by the team; starter code is placeholder and must be checked against the real API fields |
| 2026-10-16 | Irene Tang | ChatGPT (GPT-6) | Help drafting SQL queries and reviewing inspection and 311 data for the GenAI part. | SQL and documentation drafts | Ran queries in BigQuery, checked the actual data and results, reviewed relevant fields for GenAI, and shared the initial data requirements with the team. |
| 2026-10-13 | Kai Tran | Claude (claude-opus-5-5) | Walk through GCP service account, Astro setup and the CKAN data check; update staging model to real columns | Setup commands, data_sources.md entry, staging model filter, CI lint fix | Ran every command in Cloud Shell; recency verified directly with a SQL query against the CKAN API |
