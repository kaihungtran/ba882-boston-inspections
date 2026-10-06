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

Planned marts: `dim_establishment`, `dim_neighborhood`, `fct_inspections`, `fct_violations`, `fct_311_nearby`, and later `ml_features`.
