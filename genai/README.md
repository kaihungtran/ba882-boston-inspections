# Generative AI

Owner: **Irene (Yihui Tang)** | Backup: **Yanlun** — see [TEAM.md](../TEAM.md).

This folder covers violation-theme tagging and short, factual summaries of Boston restaurant inspection history. The outputs can also support the ML model and app.

## Plan

- **Phase 1 — Data review:** Review raw inspection text and identify the fields needed for GenAI. Check relevant categories in the Legacy and New 311 datasets and share input requirements with the dbt team.
- **Phase 2 — GenAI preparation:** Explore and test possible violation-theme mappings using real inspection descriptions. Coordinate with the ML team on how the tags could be used later.
- **Phase 3 — GenAI implementation:** Tag distinct violation descriptions and cache results to control costs. Evaluate the tags against a hand-labeled sample (~200 records), generate grounded restaurant summaries, and write outputs to BigQuery for downstream use.

## Files

- [inspection_variable_review.md](inspection_variable_review.md) — Phase 1 findings and input requirements.
- [sql/profile_raw_sources.sql](sql/profile_raw_sources.sql) — Read-only BigQuery queries used for data profiling.
- `prompts/` — Versioned LLM prompts.
- `src/` — Tagging, summary, and evaluation code.

Tasks are tracked in GitHub Issues: [Phase 1 variable review (#37)](https://github.com/kaihungtran/ba882-boston-inspections/issues/37), [LLM violation theme tagging (#27)](https://github.com/kaihungtran/ba882-boston-inspections/issues/27), and [restaurant summaries (#28)](https://github.com/kaihungtran/ba882-boston-inspections/issues/28). ML integration is coordinated with the ML team under [Issue #29](https://github.com/kaihungtran/ba882-boston-inspections/issues/29).
