# GenAI Phase 1 — Inspection Text and 311 Input Review

Yihui (Irene) Tang · BA882 Team 10 · October 16, 2026

I reviewed the raw inspection text to decide which fields GenAI will need for violation tagging and restaurant summaries. I also checked the category structure in both 311 datasets, since the GenAI role supports early 311 category research. This is an **input review**, not a dbt implementation, ML feature engineering, or a finished LLM model.

**Sources:** `ba882-team10-inspections.raw.food_inspections`, `raw.requests_311_legacy`, and `raw.requests_311_new` in the team BigQuery project. Results reflect queries run on October 16, 2026. See [`sql/profile_raw_sources.sql`](sql/profile_raw_sources.sql). The inspection text examples came from a 20-row query result; 311 category counts came from the top-40 query results. The raw tables may change after refreshes.

## 1. Inspection text: what the data shows

| Finding | Observed result | Why it matters for GenAI |
|---|---:|---|
| Raw rows | 905,459 | These are source rows, not necessarily separate inspection visits. |
| Distinct `_id` values | 905,459 | Each row had a unique ID in this snapshot; this does **not** establish an inspection-event key. |
| Nonblank `violdesc` | 836,170 (92.35%) | Most rows contain a violation description. |
| Nonblank `comments` | 816,959 (90.23%) | Inspector notes are available on many rows. |
| Rows with both text fields | 809,662 (89.42%) | Both sources of text can be used together; not all rows necessarily warrant an LLM call. |
| Distinct `violdesc` / `violation` | 454 / 462 | The descriptions repeat frequently; the code-to-description relationship needs verification before mapping. |
| Top 30 `violdesc` values | 496,786 records (59.41% of nonblank descriptions) | Grouping distinct descriptions first could avoid repeated tagging work. |
| Missing `resultdttm` | 6,398 (0.71%) | Date parsing and missing-value handling will matter for historical summaries. |

The 20-row exploratory sample included 17 different descriptions. Nine rows were marked `HE_Pass` even though a violation description was present, so **a violation row is not the same thing as a failed inspection**. The sample also showed that `violdesc` generally names the issue (for example, *Hot Holding*), while `comments` may give temperatures, inspector observations, or actions already completed on site. These observations are based on a small nonrepresentative sample, not a measurement of the full table.

### Fields needed for GenAI

| Raw fields | Why GenAI needs them | Requested clean input (dbt owner) |
|---|---|---|
| `_id`, `licenseno`, `property_id` | Trace source records and group a restaurant's history after the establishment link is validated. | Preserve raw IDs; provide a tested establishment key. Do not assume `property_id` or a row ID uniquely identifies a restaurant or inspection visit. |
| `resultdttm`, `violdttm` | Order past inspections and label the timing of observations. | Parse the original strings into typed dates/timestamps, retaining raw values when useful. |
| `violation`, `violdesc` | Map violation codes and descriptions to themes. | Keep both original fields; check code-to-description mapping and blank values. |
| `comments` | Support factual summaries and retain evidence of corrective actions. | Preserve the original text, including corrections reported as already completed. |
| `result`, `viol_level`, `viol_status` | Provide context for an issue and distinguish recorded outcomes/status. | Keep original values and document their meanings; do not infer inspection failure from the mere presence of a violation. |

**Initial theme directions:** temperature control (*Hot Holding*, *Cold Holding*), pests (*Rodent Activity* in 311; *Insects Rodents Animals* in inspections), cleanliness (*Food Contact Surfaces Clean*), facilities (*Improper Maintenance of Floors*), and personnel hygiene (*Hand Cleaner / Drying Tissue*). These are **examples for a draft taxonomy**, not approved labels or a finished mapping of all 454 descriptions. Inspection themes and 311 complaint themes are different concepts.

## 2. 311 Legacy vs New: category input for the team

| Field purpose | Legacy 311 | New 311 |
|---|---|---|
| Category | `reason`, `type` | `case_topic`, `service_name` |
| Case ID | `case_enquiry_id` | `case_id` |
| Opened | `open_dt` | `open_date` |
| Location | `latitude`, `longitude` | `latitude`, `longitude` |

The **top 40 category pairs** covered 190,914 of 199,594 Legacy rows (95.65%) and 81,624 of 83,378 New rows (97.90%), based on table counts visible in BigQuery. Of those top-40 rows, 190,800 Legacy and 81,539 New had numerically parseable latitude and longitude (99.94% and 99.90%, respectively). This is **not** proof that the coordinates or spatial matches are accurate.

| Legacy `type` (top-40 results) | Rows | New `service_name` (top-40 results) | Rows | Interpretation |
|---|---:|---|---:|---|
| `Rodent Activity` | 5,819 | No direct match in New top 40 | — | Strong candidate for a pest-related complaint theme; do not substitute `Wild Animal Issue`. |
| `Unsanitary Conditions - Establishment` | 701 | No direct match in New top 40 | — | Potentially relevant; the remaining low-frequency New categories were not checked. |
| `Improper Storage of Trash (Barrels)` | 10,950 | `Improper Trash Storage` | 4,053 | Similar trash-storage topics; proposed mapping, not verified one-to-one. |
| `Illegal Dumping` | 1,785 | `Illegal Dumping or Disposal` | 3,558 | Similar environmental topics; proposed mapping. |
| — | — | `Overflowing Trash` | 2,333 | Possible nearby sanitation context, not a restaurant-specific violation. |

**Recommendation:** Keep the original 311 source categories and create a separate, reviewed complaint-theme mapping if the team uses 311 in downstream analysis. Do not combine unrelated requests, treat a 311 complaint as evidence against a restaurant, or assume that Old/New category names are equivalent. The complete mapping and any spatial/time joins are **not implemented here**.

## 3. Handoff and next GenAI step

- **For Kai / dbt:** Please retain and type the inspection fields above, document inspection-event vs violation-row grain, and provide a stable establishment link and historical inspection records. For 311, preserve the source category fields so an agreed mapping can be applied without losing their original meaning. The warehouse cleaning, joins, deduplication, and spatial models remain with dbt/ingestion owners.
- **For later GenAI work:** Start with a reviewed mapping of the 454 distinct nonblank violation descriptions, then test/version tagging prompts and assess results using hand-labeled examples. Use the verified historical inspection records to produce grounded summaries. The model, evaluation, scheduled jobs, and BigQuery outputs have **not** been built in Phase 1.
- **For ML:** Any historical theme tags can be handed to Bruce for feature testing. This review does **not** construct ML predictors, train a model, choose spatial radii, or claim predictive improvement. Features must respect the prediction cutoff date.

**Scope note:** Food-license deduplication, cross-table key testing, ML modeling, and optional RAG are outside this deliverable. The broader team plan also mentions neighborhood/ACS source research, but no ACS/neighborhood raw-data findings are claimed in this review; any remaining responsibility should be confirmed with the project lead.
