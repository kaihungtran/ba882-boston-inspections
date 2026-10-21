# dbt (BigQuery)

Owner: **Data warehouse** (see [TEAM.md](../TEAM.md))

```bash
pip install dbt-bigquery
cd dbt
cp profiles.yml.example profiles.yml   # profiles.yml is gitignored
export GCP_PROJECT_ID=<our-project>
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

## Layers
| Layer | Prefix | Purpose |
|---|---|---|
| staging | `stg_` | 1:1 with raw tables: rename, cast types, light cleaning |
| intermediate | `int_` | Joins and business logic (match inspections ↔ licenses, map 311 to neighborhoods) |
| marts | `fct_` / `dim_` | Tables used by the dashboard, ML and the app |

## Staging models (built)
| Model | Grain | Notes |
|---|---|---|
| `stg_food_inspections` | one row per violation | newest copy across daily loads; admin records dropped |
| `stg_food_licenses` | one row per active license | latest snapshot only; no license number, so `name_key` / `addr_key` for matching |
| `stg_311_requests_legacy` / `_new` | one row per case | newest copy across daily loads |
| `stg_311_requests` | one row per case | union of both systems + `is_food_safety` from the seed |
| `stg_neighborhoods` | one row per neighborhood (26) | boundary as `GEOGRAPHY` |

Column-by-column rules: `docs/staging_columns.md`. Shared cleaning macros: `macros/staging_helpers.sql`.

## Seeds
- `food_safety_311_categories.csv`: which 311 categories count as food safety. Edit by hand; ML + GenAI own it.
- `neighborhoods.csv`: generated. Rebuild with `python3 scripts/build_neighborhood_seed.py`.

```bash
dbt seed --profiles-dir .
dbt build --select staging --profiles-dir .
```

Planned marts: `dim_establishment`, `dim_neighborhood`, `fct_inspections`, `fct_violations`, `fct_311_nearby`, and later `ml_features`.
