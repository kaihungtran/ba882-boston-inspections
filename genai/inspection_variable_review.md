# GenAI Phase 1 — Inspection Text and 311 Input Review

Irene (Yihui) Tang · BA882 Team 10 · October 16, 2026

Reviewed the raw inspection text to decide which fields GenAI will need for violation tagging and restaurant summaries. Also checked the category structure in both 311 datasets, since the GenAI role supports early 311 category research. This review focuses on the raw data fields and what we may need for the GenAI part later.

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

| Raw fields | Why GenAI needs them | Data preparation considerations |
|---|---|---|
| `_id`, `licenseno`, `property_id` | Trace source records and group a restaurant's history after the establishment link is validated. | The original IDs may be useful, but a reliable establishment key still needs to be validated. |
| `resultdttm`, `violdttm` | Order past inspections and label the timing of observations. | These fields are stored as strings, so converting them to date/time formats could be helpful. |
| `violation`, `violdesc` | Map violation codes and descriptions to themes. | Both original fields would be useful. Their relationship and missing values still need to be checked. |
| `comments` | Support factual summaries and retain evidence of corrective actions. | Original comments would be useful, especially when they mention corrections already completed on site. |
| `result`, `viol_level`, `viol_status` | Provide context for an issue and distinguish recorded outcomes/status. | These fields provide context, but a violation row does not necessarily mean the inspection failed. |

**Possible themes**: Based on the inspection descriptions and 311 categories, temperature control, pests, cleanliness, facilities, and personal hygiene could be useful themes for later tagging. For example, `Hot Holding` is related to temperature control, while `Rodent Activity` appears in the Legacy 311 data. These are just initial ideas, and the full mapping of violation descriptions has not been tested yet.

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

**Recommendation:** Keeping the original 311 category fields would make it easier to create a consistent mapping later. Similar category names should not automatically be treated as equivalent, and nearby complaints do not necessarily indicate violations at a restaurant.

## 3. Takeaways and next steps

- **Data preparation:** The inspection text, IDs, and date fields would be useful for future GenAI work. The difference between violation rows and inspection events still needs to be considered, and the establishment-level link has not been fully validated. For 311, keeping the original category fields would also make later comparisons and mapping easier.
- **Next GenAI steps:** The 454 distinct violation descriptions could be a starting point for theme mapping. The next step would be to test the tagging approach using real descriptions and evaluate the results with hand-labeled examples. Restaurant summaries would also need reliable historical inspection records.
- **Possible ML use:** The GenAI theme tags could potentially be used as ML features later, depending on the model requirements. Any features would need to use only information available before the prediction date.

**Scope:** This review focuses on inspection text and the category structure of the two 311 datasets. It does not cover food-license deduplication, cross-table matching, or ACS/neighborhood analysis.
