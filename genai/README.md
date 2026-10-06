# Generative AI (Phase 3)

Owner: **Generative AI** (see [TEAM.md](../TEAM.md))

- `prompts/`: versioned prompt files (e.g. `violation_tagging_v1.md`)
- `src/`: batch tagging and summary jobs, evaluation scripts

Plan:
1. Tag each distinct violation description with a theme (pests, temperature control, hygiene, facilities, ...). Tag *distinct* descriptions once and cache results to control cost.
2. Build a hand-labeled evaluation set (~200 rows) and report accuracy per theme.
3. Generate a plain-English summary per establishment from its recent history.
4. Write tags to BigQuery so ML can use them as features.
