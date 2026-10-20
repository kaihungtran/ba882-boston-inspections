# ML feature spec for dbt (intermediate + marts)

**From:** Machine learning (Bruce) · **For:** Data warehouse (Kai, Yanlun) · **Status:** draft for review
Model and column names follow [`docs/data_model.md`](../docs/data_model.md). This file adds the ML-specific detail on top of it.
**Evidence:** [`notebooks/01_eda_target_baseline.ipynb`](notebooks/01_eda_target_baseline.ipynb) (2026-10-13 landing snapshot). Section numbers below (§) point into that notebook.

This is the list of transforms ML needs, from the raw bucket tables through to two marts:

- `ml_features`: one row per **routine inspection**, with features and target. Used for training.
- `ml_scoring_features`: one row per **active establishment** as of today. Scored weekly, and the results are written to `marts.ml_risk_scores`.

The notebook's pandas version of this table is `data/features_v0.parquet`. The dbt version should reproduce it row for row (see [Parity check](#7-parity-check)).

---

## 1. Rules that apply to every feature

1. **Point in time.** A feature for an inspection on date *D* may only use data from **before** *D*. In SQL, that means windows ending at `1 PRECEDING`, never `CURRENT ROW`. Breaking this rule leaks the answer into the features, and the model looks better than it really is.
2. **Compute history over all inspections, then filter.** Follow-ups and pre-2020 inspections count as history. Filter to routine inspections only at the end, in the mart.
3. **Never use current-snapshot fields as features.** `licstatus`, `issdttm`, `expdttm` and `status_date` hold today's values, repeated on every historical row (§2, §9). They may be used to choose the scoring population, but never as model inputs.
4. **Missing means unknown.** A missing value stays `NULL`. For example, an establishment with no prior inspections has `prev_n_critical` = `NULL`, not 0. The ML pipeline handles the imputation.

---

## 2. Staging fixes (`stg_*`)

### `stg_food_inspections` (grain: one row per violation)

`main` already confirms the column names and drops rows with a null `resultdttm`. That model is still missing the following:

- Admin result codes aren't dropped.
- Timestamps go through a plain `cast`, which may fail on the mixed formats.
- There's no level cleanup, code-system or severity flag.
- `location` isn't parsed into lat/lon.
- `city` and `state` aren't normalised.

The full mapping is below (§1). `licstatus` is already staged as `license_status`; it's for the scoring population only.

| Raw column | Staged as | Transform |
|---|---|---|
| `licenseno` | `license_number` | `trim(cast(... as string))`; drop rows where it is empty or `'nan'` |
| `resultdttm` | `inspected_at` | Timestamp formats are mixed (with and without fractional seconds, `+00` offsets). Use `coalesce(safe_cast(x as timestamp), safe.parse_timestamp(...))` and check that the parse rate is ≥ 99.3%. Drop rows that are still null (0.7%) |
| — | `inspection_date` | `date(inspected_at)` (UTC, which matches the notebook) |
| `result` | `result_code` | Unchanged. **Drop** rows where the code is in `HE_NotReq, HE_OutBus, DATAERR, HE_Misc, HE_Hold, Closed`; these are admin records, not inspections (§2b). Keep `HE_Hearing`, `HE_TSOP`, `HE_Closure` and `HE_VolClos` |
| `viol_level` | `violation_level` | Accept only `*`, `**`, `***`. Anything else (e.g. the one `1919` row) becomes `NULL`. A `NULL` level means "no violation on this row", not missing data |
| `violation` | `violation_code` | Unchanged |
| — | `violation_code_system` | `'fda'` if the code matches `^\d{3}\.\d{3}/` or `^M-`; `'boston_legacy'` if it doesn't match; `NULL` if there is no code (§2e) |
| — | `fda_severity` | Regex suffix `-(P\|PF\|C)$`; `'M'` for codes starting with `M-` |
| `violdesc` | `violation_description` | `trim` |
| `viol_status` | `violation_status` | Unchanged (`Pass` / `Fail`) |
| `violdttm` | `violation_at` | Same parsing as `inspected_at` |
| `licensecat` | `license_category` | Unchanged (`FS`, `FT`, `RF`, `MFW`) |
| `descript` | `license_description` | Unchanged |
| `businessname`, `address`, `zip` | same | `trim` |
| `city` | `city_raw` | `upper`, `trim`, strip a trailing `/` (e.g. `MISSION HILL/`). This is a stopgap until the spatial neighborhood join exists |
| `state` | `state` | `upper` (`Ma`, `ma` → `MA`) |
| `location` | `latitude`, `longitude` | `regexp_extract` on `(lat, lon)`. Set to `NULL` if outside the bounding box lat 42.2–42.42, lon −71.2 to −70.95 |
| `property_id` | `property_id` | Unchanged; used for license matching |
| `licstatus`, `issdttm`, `expdttm` | same | Keep for scoring-population logic **only** (see Rule 3) |
| `dbaname`, `status_date`, `namefirst`, `legalowner` | — | Drop (99% / 59% / 42% null, and not needed) |
| `comments` | `inspector_comments` | Keep. Not an ML feature for now, but GenAI will tag it |

### `stg_311_requests`: union of the legacy and new feeds

Boston is moving 311 to a new vendor one department at a time. The [transition guide](https://docs.google.com/document/d/e/2PACX-1vQ9ExKIGyrLJeyVUO92qNw0Cbj5m6Sz2IAATdBgYiAGW69Wuv7dk10PHUPR7UdawGt_e89q9VhxH-I0/pub) lists **Inspectional Services as "Planned, Fall 2026"**. Today all the food-safety types (Rodent Activity, Unsanitary Conditions, Food Alert) are in the legacy feed, and none are in the new one. We assume, though the guide doesn't say, that these cases are handled by Inspectional Services. Once it cuts over, new food-safety cases will probably appear **only in the new feed**. Reading the legacy feed alone would make the 311 feature quietly drop to zero.

- **Sources.** Declare both bucket folders as sources: `requests_311_legacy` and `requests_311_new`. Right now `_sources.yml` has a single `requests_311` entry, which matches neither folder.
- **Stage each feed separately, then union them** into one model with the same columns:

  | Column | Legacy field | New-system field |
  |---|---|---|
  | `case_id` | `case_enquiry_id` | Case ID |
  | `opened_at` | `open_dt` (mixed formats, same parsing approach) | Open Date |
  | `case_category` | `type` | Case Topic, falling back to Service Name |
  | `department` | `department` | Assigned Department |
  | `latitude`, `longitude` | `latitude`, `longitude` | Latitude (Y), Longitude (X) |
  | `source_system` | `'legacy'` | `'new'` |

  The guide gives this field mapping. Check the exact column names in the raw new-feed files. `type` has **no direct equivalent** in the new system, so `case_category` won't line up value for value across the two systems.
- **`is_food_safety` from a seed, not a regex.** Add a seed `seeds/food_safety_311_categories.csv` with the columns `source_system`, `case_category` and `is_food_safety`.
  - **Legacy rows:** start from what the notebook's regex matched (§10): Rodent Activity, Pest Infestation - Residential, Unsanitary Conditions (Establishment / Food / Employees), Food Alert (Confirmed / Unconfirmed), Overflowing or Un-kept Dumpster, and others.
  - **New-system rows:** fill these in from the new feed's data dictionary (linked from the guide) once Inspectional Services moves over.
- **Avoid double counting.** During the cutover, the same case could appear in both feeds. Dedupe on `case_id` if the ids carry over. If they don't, flag it.
- **Test.** Add a test that warns when the daily count of `is_food_safety` cases drops by more than 50% from the trailing 4-week average. That's how the cutover will show up if nobody updates the seed.

### `stg_neighborhood_tracts`

- The GeoJSON is in the bucket at `raw/neighborhoods/` but isn't declared as a source yet. Load it with a `GEOGRAPHY` column for the polygon and a `neighborhood` name.

### `stg_food_licenses`

- This table has **no license number** (§9). Normalise for matching:
  - `name_key`: upper-case `businessname`, then strip `[^A-Z0-9]`
  - `addr_key`: the first two tokens of the upper-cased address
  - `licensecat`
- Keep `license_add_dt_tm`, `latitude`, `longitude` and `property_id`.

---

## 3. Intermediate models (`int_*`)

> `dbt_project.yml` currently sets intermediate models to `ephemeral`. `int_inspections` and `int_inspection_history` feed both marts and use heavy window functions, so please materialize at least those two as `table` (or `view`).

### 3.1 `int_inspections`: violation rows → one row per inspection

**Grain:** `license_number` + `inspection_date`. That's about 195k rows (from about 874k violation rows) across about 10.7k establishments (§4).

| Column | Definition |
|---|---|
| `inspection_id` | `farm_fingerprint(license_number \|\| inspection_date)` (or a dbt surrogate key) |
| `n_rows` | `count(*)` |
| `n_violations` | `countif(violation_level in ('*','**','***'))` |
| `n_critical` | `countif(violation_level = '***')` |
| `n_major` | `countif(violation_level = '**')` |
| `result_fail` | `logical_or(regexp_contains(lower(result_code), 'fail'))` |
| `result_code` | One value per inspection. In 0.29% of inspections the rows disagree on the code; the notebook takes the first row's code. `any_value` is fine |
| `license_category`, `business_name` | `any_value` |
| `city_clean` | `any_value(city_raw)` |
| `latitude`, `longitude` | Median per inspection (`approx_quantiles(x, 2)[offset(1)]`) |
| **`target`** | `n_critical > 0` (as an int 0/1) |
| `fda_code_era` | `inspection_date >= '2020-01-01'` (as an int 0/1) |

Then, per license ordered by `inspection_date`, add the following:

| Column | Definition |
|---|---|
| `prev_inspection_date` | `lag(inspection_date)` |
| `days_since_prev` | `date_diff(inspection_date, prev_inspection_date, day)` |
| `prev_result_fail` | `lag(result_fail)` |
| `prev_target` | `lag(target)` |
| **`is_followup`** | `(prev_result_fail or prev_target = 1) and days_since_prev <= 30`. The 30-day window is backed by §6: 96% of re-visits after a fail come within 30 days. Put the 30 in a dbt `var('followup_window_days', 30)` so we can test 21 and 45 |
| **`is_routine`** | `not coalesce(is_followup, false)` |

Tests: `unique` on (`license_number`, `inspection_date`), `not_null` on `target`, and `accepted_values` on `license_category`.

### 3.2 `dim_establishment` (built from `int_establishment_geo`): one row per license

| Column | Definition |
|---|---|
| `license_number` | Primary key |
| `license_category`, `business_name`, `address` | The most recent value |
| `latitude`, `longitude` | Median over all of the license's inspections. About 13% of establishments have none (§2d) |
| `tract_geoid` → `neighborhood` | `ST_CONTAINS(tract.geom, ST_GEOGPOINT(lon, lat))`, then look up `neighborhood` in `dim_neighborhood`. This replaces `city_clean`. Where coordinates are missing, fall back to `city_clean` (see [data_model.md](../docs/data_model.md)) |
| `first_inspection_date` | `min(inspection_date)` |
| `is_active_license` | `licstatus = 'Active'` on the latest row. **Used for the scoring population only** |
| `matched_license_feed_row` | From the license match below (QA only) |

### 3.3 `int_license_crosswalk`

Match `stg_food_licenses` to inspection license numbers on `name_key | licensecat | addr_key`. First drop any key that maps to more than one license number on the inspections side. The notebook matches 87.4% of license-feed rows this way. Please export the unmatched rows for manual review. This model matters for scoring and QA, not for training.

### 3.4 `int_311_geo`

Starts from `stg_311_requests`. Keep rows where `is_food_safety`, the coordinates are in Boston and `opened_at` is not null. **Drop default-geocode points**: any single lat/lon that holds more than `max(50, 1% of rows)` complaints (§10).

### 3.5 `fct_311_nearby` → `complaints_311_near`

`fct_311_nearby` (see [data_model.md](../docs/data_model.md)) has one row per inspection × nearby complaint. It covers complaints within **250 m** that were opened in the **90 days before** the inspection date:

```sql
select
  i.inspection_id,
  c.case_id,
  st_distance(st_geogpoint(i.longitude, i.latitude), c.point) as distance_m,
  date_diff(i.inspection_date, date(c.opened_at), day)         as days_before
from {{ ref('int_inspections') }} i
join {{ ref('int_311_geo') }} c
  on st_dwithin(st_geogpoint(i.longitude, i.latitude), c.point, {{ var('radius_311_m', 250) }})
 and date(c.opened_at) <  i.inspection_date
 and date(c.opened_at) >= date_sub(i.inspection_date, interval {{ var('window_311_days', 90) }} day)
where i.latitude is not null
```

The ML feature is `complaints_311_near = count(case_id)` per `inspection_id`. Inspections that have coordinates but no matches get **0**. Inspections with no coordinates get `NULL`.

**Coverage rule:** if `inspection_date` is earlier than (first 311 record date + 90 days), set the count to `NULL`, not 0. Before that date, 0 means "no data". Right now 311 only starts in January 2026, so this feature exists for just 3% of inspections, and none of them fall in the training window. See the ingestion ask in §6.

---

## 4. Feature catalog (`int_inspection_history`)

All features are windows over `int_inspections`, partitioned by `license_number` and ordered by `inspection_date`.

**Priority:**

- **P0:** in the current baseline model, and needed for v1.
- **P1:** build now; the model needs it soon.
- **P2:** cheap to keep; candidate to drop.

Importance is the permutation importance from §11 (drop in PR AUC on validation).

### History features

| Feature | Definition (SQL sketch) | Priority | Importance / evidence |
|---|---|---|---|
| `last_routine_n_critical` | `last_value(if(is_routine, n_critical, null) ignore nulls) over (... rows between unbounded preceding and 1 preceding)` | P0 | **0.036 (#1).** The visit just before a routine one is often a passed follow-up, so look back to the last *routine* visit |
| `prior_violations_total` | `sum(n_violations) over (... rows between unbounded preceding and 1 preceding)` | P0 | 0.027 (#2) |
| `days_since_first_insp` | `date_diff(inspection_date, min(inspection_date) over (partition by license_number), day)` | P0 | 0.018 (#3) |
| `days_since_prev` | From `int_inspections` | P0 | 0.015 |
| `prev_n_violations` | `lag(n_violations)` | P0 | 0.011 |
| `days_since_last_routine` | `date_diff(inspection_date, last_value(if(is_routine, inspection_date, null) ignore nulls) over (... 1 preceding), day)` | P0 | 0.010. Non-monotonic (§7 H5) |
| `violations_past_365d` | `sum(n_violations) over (partition by license_number order by unix_date(inspection_date) range between 365 preceding and 1 preceding)` | P0 | 0.010 |
| `prior_critical_rate` | `sum(target) over (... unbounded preceding and 1 preceding) / nullif(n_prior_insp, 0)` | P0 | 0.009 |
| `prev_n_critical` | `lag(n_critical)` | P0 | 0.008 |
| `critical_past_365d` | Like `violations_past_365d`, but summing `n_critical` | P0 | 0.006 |
| `n_prior_insp` | `row_number() over (...) - 1` | P0 | 0.006. `= 0` captures the low-risk first visit (10% vs 22%, §7 H6) |
| `prev_result_fail` | From `int_inspections` (cast to 0/1) | P0 | 0.005 |
| `prior_critical_total` | `sum(n_critical) over (... unbounded preceding and 1 preceding)` | P0 | 0.004 |
| `fda_code_era` | From `int_inspections` | P0 | Keeps predictions calibrated across the 2019 code change (§11) |
| `had_followup_since_last_routine` | `prev_inspection_date > last_routine_date` (`NULL` if there is no prior routine visit) | P2 | ≈ 0 |

### Establishment and context features

| Feature | Definition | Priority | Evidence |
|---|---|---|---|
| `license_category` | From `int_inspections` | P0 | FS 26% → FT 20% → RF 15% → MFW 8% (§7 H2) |
| `neighborhood` | From `dim_establishment` (spatial join via `tract_geoid`) | P1 | Replaces `city`. Raw rates vary from 11% to 30%, but the model gains little once history is in |
| `city_clean` | Stopgap until `neighborhood` exists | P2 | 0.002 |
| `month` | `extract(month from inspection_date)` | P2 | Seasonality rejected (§7 H4) |
| `complaints_311_near` | Aggregated from `fct_311_nearby` | P1 (**blocked on 311 backfill**) | Critical rate rises from 15% to 30% as complaints increase (§10) |

### New features ML would like to try (P1, not yet in the notebook)

| Feature | Definition | Why |
|---|---|---|
| `prev_n_major` / `major_past_365d` | Like the critical versions, but with `n_major` (`**`) | Priority Foundation items absorbed part of the old "critical" class in 2019 |
| `last_routine_had_critical` | `last_routine_n_critical > 0` | Repeat-offender signal: 42% vs 17% (§7 H1) |
| `prev2_routine_target` | The target from the second-to-last routine visit | Two criticals in a row: 48.5% vs 14.3% for two clean visits (§7 H1) |
| `prior_enforcement_count` | Count of prior inspections with `result_code in ('HE_Hearing','HE_TSOP','HE_Closure','HE_VolClos')` | Enforcement history; these codes have a 44–79% critical rate |
| `prior_critical_by_theme_*` | Prior counts per violation theme (temperature, PIC, surfaces, …) | Will be built from the GenAI violation tags once they exist. Placeholder for now |

### Never use as features (they leak)

`licstatus`, `issdttm`, `expdttm`, `status_date`, `license_add_dt_tm`, `license_age_days`. Anything else about the **current** inspection is also off limits: `n_violations`, `n_critical`, `result_code` and `result_fail` of the same row. §9 shows the leak: establishments inactive today had a 32% critical rate, against 27% for those still active.

---

## 5. Marts

### `ml_features` (training)

- **Grain:** one row per inspection where `is_routine = true` (about 120k rows across all years, about 46k since 2020).
- **Columns:** `inspection_id`, `license_number`, `inspection_date`, `target`, `result_fail` (kept for comparison only), `latitude`, `longitude`, and every P0 and P1 feature from §4.
- **Do not add a split column.** ML does the time-based train/valid/test split in code.
- **Tests:**
  - `unique(inspection_id)`
  - `not_null(target)`
  - `n_prior_insp = 0 ⇒ prior_critical_total = 0`
  - `critical_past_365d <= prior_critical_total`

  These are the same leakage asserts as §8.
- Please add a dbt model contract once the column list settles.

### `ml_scoring_features` (weekly scoring)

- **Grain:** one row per `license_number` where `is_active_license`, with `score_date` set to the run date.
- **Population:** active licenses from the inspections feed, all four categories. The licenses feed only covers FS/FT, so use it as a cross-check through `int_license_crosswalk`.
- **Features:** the **same definitions**, evaluated as if a routine inspection happened on `score_date`. All "prior" windows then include every inspection to date. `days_since_*` are measured to `score_date`, and `fda_code_era = 1`.
- **Implementation tip:** append one synthetic row per active license (`inspection_date = score_date`, `is_routine = true`, `target = NULL`) to `int_inspections` before the window step. That way both marts share one feature model and can't drift apart.

---

## 6. Asks for ingestion (Kai, Fei)

1. **Backfill legacy 311 to at least 2020.** data.boston.gov publishes one file per year back to 2011. Without it, the 311 feature can't be trained.
2. **Keep ingesting both 311 feeds, and watch for the Inspectional Services cutover** ("Fall 2026" per the transition guide). When it happens, tell ML and the warehouse team so the new-system rows in the `food_safety_311_categories` seed get filled in. Also check whether the legacy feed keeps receiving updates afterwards. The guide doesn't say.
3. Add a load timestamp to the raw tables so `_sources.yml` freshness works (there's an existing TODO for this).
4. Declare `neighborhoods`, `requests_311_legacy` and `requests_311_new` as sources, replacing the current single `requests_311` entry.

## 7. Parity check

Once `ml_features` builds, ML will compare it against `data/features_v0.parquet` on (`license_number`, `inspection_date`). Expected differences are under 1% of rows, because SQL and pandas handle `result_code` ties and timestamp edge cases slightly differently. Anything larger needs a look before we retrain on the dbt table.

## 8. Open questions

- **Timezones.** Should `inspection_date` use UTC (the notebook's choice) or America/New_York? Timestamps are stored with `+00`, but some may really be local time. If we switch, the notebook and dbt must switch together.
- **Follow-up window.** We'll keep it at 30 days for now. ML will run a robustness check with 21 and 45 days.
- **311 across the cutover.** The two systems categorise cases differently, so the complaint counts may shift at the cutover even after mapping. ML will check the feature for a level change around the cutover date and may add a `source_system` share or a cutover flag.
- **Alternative target.** `**` or `***` (`n_major + n_critical > 0`). Please expose `n_major` in the mart so ML can test this without any dbt change.
