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

## Intermediate models (built)
Spec: `ml/dbt_feature_spec.md` §3–4 (ML). Materialized as tables in the `intermediate` schema.

| Model | Grain | Notes |
|---|---|---|
| `int_violations` | one row per violation record | each inspection's rows from its latest load only, so an edited comment isn't counted twice; full description and comment text |
| `int_inspections` | one row per inspection (license + date) | violations rolled up; `target` = any `***`; `is_routine` / `is_followup` via `var('followup_window_days', 30)` |
| `int_inspection_history` | one row per inspection | ~20 point-in-time features; every window ends at `1 PRECEDING` (no leakage) |
| `int_license_crosswalk` | one row per licenses-feed record | matched `license_number`: name+category+address, then property_id+name, then address+category |
| `int_establishment_geo` | one row per license | latest details, median location, neighborhood; `is_active_license` for scoring only |
| `int_311_geo` | one row per classified 311 case | default geocodes in `seeds/default_geocode_points.csv` removed; main count = `is_food_safety`, `signal_group` kept |

Tests: grain and leakage asserts (`tests/assert_int_*`), license match-rate warning (`tests/warn_license_match_rate.sql`), new default-geocode candidates (`tests/warn_new_geocode_pileup.sql`).
Unmatched licenses for manual review: `analyses/int_license_crosswalk_unmatched.sql`.

```bash
dbt build --select staging intermediate --profiles-dir .
```

## Seeds
- `food_safety_311_categories.csv`: which 311 categories count as food safety. Edit by hand; ML + GenAI own it.
- `neighborhoods.csv`: generated. Rebuild with `python3 scripts/build_neighborhood_seed.py`.
- `default_geocode_points.csv`: 311 default geocodes (City Hall Plaza and variants) removed by `int_311_geo`. Add a point when `warn_new_geocode_pileup` flags one and you confirm it.

```bash
dbt seed --profiles-dir .
dbt build --select staging --profiles-dir .
```

## Marts (built)
Materialized as tables in the `marts` schema. Keys: `fct_violations` → `fct_inspections` → `dim_establishment` → `dim_neighborhood`.

| Model | Grain | Notes |
|---|---|---|
| `fct_violations` | one row per violation | full `violation_description` and `inspector_comments` for GenAI; an edited comment is one row (latest wording) |
| `fct_inspections` | one row per inspection (license + date) | result, violation counts, `target`, `is_routine` / `is_followup` |
| `dim_establishment` | one row per license | latest details, location, neighborhood, `is_active_license` (scoring only) |
| `dim_neighborhood` | one row per neighborhood (26) | boundary; census tracts and ACS not loaded yet |

```bash
dbt build --select marts --profiles-dir .
```

Next: `fct_311_nearby`, `ml_features`, `ml_scoring_features` (`ml/dbt_feature_spec.md` §3.5, §5).
