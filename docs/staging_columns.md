# Staging columns and cleaning

For each raw table, this lists the columns that staging keeps and the cleaning each one needs. The goal is one reference for ML, GenAI and BI. Model names follow [data_model.md](data_model.md). The ML-specific reasoning is in [ml/dbt_feature_spec.md](../ml/dbt_feature_spec.md), and the GenAI field needs are in Irene's review, `genai/inspection_variable_review.md` (on the `genai/37-variable-review` branch).

**Where the column names come from:**

| Raw table | Source of the column names |
|---|---|
| Inspections, licenses | Confirmed (2026-10-13 snapshot, `docs/data_sources.md`) |
| Legacy 311 | Taken from the city's transition guide; matches the 32 loaded columns |
| New 311 | `case_id`, `open_date`, `case_topic`, `service_name`, `latitude`, `longitude` confirmed in the GenAI review. The other new-feed names are **to confirm** |
| Neighborhoods | Property names **to confirm** |

**Used by:**

| Code | Meaning |
|---|---|
| ML | Features, target or scoring |
| GenAI | Tagging or summaries |
| BI | Dashboard |
| Match | License matching |
| Trace | Lineage only |

## Rules for every staging model

- **Every raw column arrives as text.** Cast explicitly with `safe_cast`. Never rely on autodetect.
- **Blank text becomes `NULL`.** Use `nullif(trim(x), '')` on every text column before any other cleaning.
- **Timestamps need a macro.** Formats are mixed: with and without fractional seconds, with `+00` offsets. Use a shared `safe_ts(x)` macro (`coalesce(safe_cast(x as timestamp), safe.parse_timestamp(...))`). Add a test that it parses at least 99% of non-null values.
- **Coordinates outside Boston become `NULL`.** The bounding box is lat 42.2–42.42 and lon −71.2 to −70.95.
- **Keep the original text.** Don't rewrite free text (`comments`, `violdesc`, 311 categories) beyond trimming and collapsing whitespace. GenAI needs the original wording.

---

## `raw.food_inspections` → `stg_food_inspections`

**Load pattern:** full replace each run (`WRITE_TRUNCATE`).
**Grain after staging:** one row per violation. An inspection with no violations still gets one row.

**Table-level cleaning:**
1. Drop rows where `inspected_at` is null or can't be parsed (about 0.7%).
2. Drop admin records: `result in ('HE_NotReq','HE_OutBus','DATAERR','HE_Misc','HE_Hold','Closed')`. That's about 2.7% of rows (24.6k). They're not inspections.
3. Drop rows with a blank `license_number`.

| Raw column | Staged as (type) | Cleaning | Used by |
|---|---|---|---|
| `_id` | `source_row_id` (INT64) | None. **This is the city's row id**, used to trace tags and summaries back to source rows. It's not a durable key, because the city could renumber it if it rebuilds the dataset | Trace, GenAI |
| `licenseno` | `license_number` (STRING) | Trim. Drop the row if blank or `'nan'` | ML, GenAI, BI |
| `businessname` | `business_name` | Trim; collapse repeated spaces | GenAI, BI, Match |
| `licensecat` | `license_category` | Trim, upper. Accepted values: `FS`, `FT`, `RF`, `MFW` | ML, BI |
| `descript` | `license_description` | Trim | BI |
| `licstatus` | `license_status` | Trim. **Scoring population only; never a feature** (it holds today's value) | ML (scoring) |
| `issdttm` | `license_issued_at` (TIMESTAMP) | `safe_ts`. **Never a feature** | ML (scoring) |
| `expdttm` | `license_expires_at` (TIMESTAMP) | `safe_ts`. **Never a feature** | ML (scoring) |
| `result` | `result_code` | Trim. Add `result_fail = regexp_contains(lower(result_code), 'fail')` | ML, GenAI, BI |
| `resultdttm` | `inspected_at` (TIMESTAMP), `inspection_date` (DATE) | `safe_ts`; take `date()` in UTC (the timezone is still an open question) | ML, GenAI, BI |
| `violation` | `violation_code` | Trim. Add `violation_code_system`: `'fda'` if it matches `^\d{3}\.\d{3}/` or `^M-`, otherwise `'boston_legacy'`. Add `fda_severity`: the suffix `-(P\|PF\|C)$`, or `'M'` for `M-` codes | ML, GenAI |
| `viol_level` | `violation_level` | Keep only `*`, `**`, `***`; anything else (e.g. `1919`) becomes `NULL`. **`NULL` means no violation on this row**, not missing data | ML, GenAI, BI |
| `violdesc` | `violation_description` | Trim; collapse repeated spaces (the raw data has `Clean Cloths  Hair Restraint`) | GenAI, BI |
| `violdttm` | `violation_at` (TIMESTAMP) | `safe_ts` | GenAI |
| `viol_status` | `violation_status` | Trim. Accepted values: `Pass`, `Fail` | GenAI, BI |
| `comments` | `inspector_comments` | Trim only. Keep the original text | GenAI |
| `address` | `address` | Trim; collapse repeated spaces (`55  COURT ST`) | Match, BI |
| `city` | `city` | Upper, trim, strip a trailing `/` (`MISSION HILL/`). Fallback neighborhood only | ML (fallback), BI |
| `state` | `state` | Upper (`Ma`, `ma` → `MA`) | BI |
| `zip` | `zip` (STRING) | Trim. **Keep as a string**, so leading zeros survive (`02108`) | BI |
| `property_id` | `property_id` (STRING) | Trim | Match, GenAI |
| `location` | `latitude`, `longitude` (FLOAT64) | `regexp_extract` the two numbers from `(lat, lon)`, then apply the bounding-box rule | ML, BI |
| `_loaded_at` | `_loaded_at` (TIMESTAMP) | None. Used for source freshness | Ops |

**Dropped:** `dbaname` (99% null), `status_date` (59% null), and `legalowner`, `namefirst` and `namelast` (owner names; unused, and they're personal data).

**Tests:**
- `not_null` on `license_number` and `inspected_at`
- `accepted_values` on `violation_level`, `license_category` and `violation_status`
- `safe_ts` parses at least 99% of values

---

## `raw.food_licenses` → `stg_food_licenses`

**Load pattern:** a full snapshot each day, appended as a new `_load_date` partition.
**Grain after staging:** one row per active license in the latest snapshot.

**Table-level cleaning:**
1. **Keep only the latest partition** (`where _load_date = (select max(_load_date) ...)`). Without this, every license is duplicated once per day loaded.

| Raw column | Staged as (type) | Cleaning | Used by |
|---|---|---|---|
| `businessname` | `business_name`, `name_key` | Trim. `name_key` = upper with `[^A-Z0-9]` removed | Match, BI |
| `address` | `address`, `addr_key` | Trim, collapse spaces. `addr_key` = the first two tokens, upper-cased | Match |
| `licensecat` | `license_category` | Trim, upper | Match |
| `city` | `city` | Same as inspections | BI |
| `state` | `state` | Upper | BI |
| `zip` | `zip` (STRING) | Keep as a string | BI |
| `descript` | `license_description` | Trim | BI |
| `license_add_dt_tm` | `license_added_at` (TIMESTAMP) | `safe_ts`. **Never a feature**: it only exists for licenses still active today | Scoring QA |
| `property_id` | `property_id` (STRING) | Trim | Match |
| `latitude`, `longitude` | same (FLOAT64) | `safe_cast`, then the bounding-box rule | ML (missing-coordinate fill), BI |
| `_load_date` | `_load_date` (DATE) | None | Ops |

**Dropped:** `_id` (changes between daily snapshots), `dbaname`, `licstatus` (always `Active` in this feed), and `dayphn_cleaned` (phone number; unused).

---

## `raw.requests_311_legacy` → `stg_311_requests_legacy`

**Load pattern:** incremental with a **30-day lookback**. Each day's partition repeats the last 30 days of cases.
**Grain after staging:** one row per case.

**Table-level cleaning:**
1. **Dedupe on `case_enquiry_id`**, keeping the row with the latest `_load_date`:
   ```sql
   qualify row_number() over (partition by case_enquiry_id order by _load_date desc) = 1
   ```
   This likely explains why BigQuery showed 199.6k rows on Oct 16 against 189.4k in a single bucket partition on Oct 13. Category counts taken before the dedupe are inflated.

| Raw column | Staged as (type) | Cleaning | Used by |
|---|---|---|---|
| `case_enquiry_id` | `case_id` (STRING) | Trim | ML, GenAI |
| `open_dt` | `opened_at` (TIMESTAMP) | `safe_ts`. Formats are mixed, and pandas' default parsing dropped about 75% of them | ML, BI |
| `closed_dt` | `closed_at` (TIMESTAMP) | `safe_ts` | BI |
| `case_status` | `case_status` | Trim | BI |
| `case_title` | `case_title` | Trim. Keep the original text | GenAI |
| `type` | `type`, `case_category` | Trim. **Keep the original `type`** (GenAI's recommendation), and copy it into `case_category` for the union | ML (seed lookup), GenAI |
| `reason` | `reason` | Trim. Keep the original | GenAI, ML (seed fallback) |
| `subject` | `subject` | Trim. Keep the original | GenAI |
| `department` | `department` | Trim | BI |
| `latitude`, `longitude` | `latitude`, `longitude` (FLOAT64), `point` (GEOGRAPHY) | `safe_cast`, then the bounding-box rule; `point = st_geogpoint(longitude, latitude)`. Default-geocode points are removed later, in `int_311_geo` | ML |
| `source` | `report_source` | Trim | BI |
| — | `source_system` | Constant `'legacy'` | All |
| `_load_date` | `_load_date` (DATE) | None | Ops |

**Dropped:**
- `_id`
- `sla_target_dt`, `on_time`, `closure_reason`, `queue`
- `submitted_photo`, `closed_photo`
- `location`, `location_street_name`, `location_zipcode`, `geom_4326`
- `neighborhood`, `neighborhood_services_district`, `ward`, `precinct`, `fire_district`, `pwd_district`, `police_district`, `city_council_district`

**Check with BI** before dropping `on_time` or the district fields.

---

## `raw.requests_311_new` → `stg_311_requests_new`

**Load pattern:** incremental with a 30-day lookback, on `open_date`.
**Grain after staging:** one row per case.

**Table-level cleaning:**
1. Dedupe on `case_id`, keeping the latest `_load_date` (same pattern as legacy).

| Raw column | Staged as (type) | Cleaning | Used by |
|---|---|---|---|
| `case_id` | `case_id` (STRING) | Trim | ML, GenAI |
| `open_date` | `opened_at` (TIMESTAMP) | `safe_ts` | ML, BI |
| `case_topic` | `case_topic`, `case_category` | Trim. **Keep the original.** `case_category = coalesce(case_topic, service_name)` | ML (seed lookup), GenAI |
| `service_name` | `service_name` | Trim. Keep the original | GenAI, ML (seed fallback) |
| `latitude`, `longitude` | `latitude`, `longitude`, `point` | Same as legacy | ML |
| Close date (name to confirm) | `closed_at` | `safe_ts` | BI |
| Case status (name to confirm) | `case_status` | Trim | BI |
| Assigned department (name to confirm) | `department` | Trim | BI |
| Report source (name to confirm) | `report_source` | Trim. Values differ from legacy (e.g. `Call` vs `Constituent Call`) | BI |
| — | `source_system` | Constant `'new'` | All |
| `_load_date` | `_load_date` | None | Ops |

**Dropped:** all other fields.

### `stg_311_requests`: union of the two

- **Union** the shared columns. The legacy-only columns (`type`, `reason`, `subject`) and the new-only ones (`case_topic`, `service_name`) are `NULL` on the other side's rows.
- **Join** `seeds/food_safety_311_categories.csv` on `source_system` + `case_category` to get `is_food_safety`. The new-system rows of the seed get filled in at the Inspectional Services cutover (Fall 2026).
- **Dedupe across feeds** on `case_id` if the ids carry over between the two systems. If they don't, flag it.
- **Test:** warn if daily `is_food_safety` volume drops more than 50% below the trailing 4-week average.

---

## neighborhoods (GeoJSON) → `stg_neighborhood_tracts`

**Load pattern:** a static GeoJSON file in GCS only. **It isn't in BigQuery yet.** Ingestion needs to load it into `raw.neighborhoods`: one feature per line, using `bq load --source_format=NEWLINE_DELIMITED_JSON --json_extension=GEOJSON`.

| Raw field | Staged as (type) | Cleaning | Used by |
|---|---|---|---|
| Polygon geometry | `geom` (GEOGRAPHY) | `st_geogfromgeojson(..., make_valid => true)` | ML, BI |
| Tract GEOID (name to confirm) | `tract_geoid` (STRING) | Keep as an 11-character string, zero-padded. This is the key for the Census ACS join | ML, BI |
| Neighborhood name (name to confirm) | `neighborhood` | Trim | ML, BI |

**Tests:** `unique` and `not_null` on `tract_geoid`.
