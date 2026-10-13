# Data Sources

| Source | Portal | Updates | Access | Notes |
|---|---|---|---|---|
| Food Establishment Inspections | [data.boston.gov](https://data.boston.gov/dataset/food-establishment-inspections) | Daily | CKAN `datastore_search` API | Marked **legacy**: confirm latest record date before relying on it |
| 311 Service Requests | [data.boston.gov](https://data.boston.gov/dataset/311-service-requests) | Daily | CKAN API | Moving to a new system with a different schema; see the city's [transition guide](https://data.boston.gov/dataset/311-service-requests/resource/6e86da47-9b6c-459a-ab97-0e64045081a0) |
| Active Food Establishment Licenses | [data.boston.gov](https://data.boston.gov/dataset/active-food-establishment-licenses) | Daily | CKAN API | Master list of establishments |
| Neighborhood boundaries | [data.boston.gov](https://data.boston.gov/dataset/boston-neighborhood-boundaries-approximated-by-2020-census-tracts) | Static | GeoJSON / shapefile | Spatial join with establishments and 311 |
| Census ACS 5-year | [census.gov](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Annual | Census API (free key) | Tract-level context |

## Data-access check (issue #4)

### Food Establishment Inspections ✅ checked 2026-10-13 (Kai)
- **CKAN resource ID:** `4582bec6-2b4f-4f9e-bc55-cbaa73117f4c`
- **Latest inspection (`resultdttm`):** 2026-10-09 21:13 UTC, so the dataset is still updated despite the "legacy" label
- **Rows:** 904,930 total; 898,532 have an inspection date. The other ~6,400 are establishments with no inspection on file (e.g. `result = 'HE_NotReq'`), filtered out in `stg_food_inspections`
- **Grain:** one row per establishment × inspection × violation
- **All columns arrive as text** (dates like `2012-02-27 13:47:59+00`); types are cast in staging
- **Columns:** `_id, businessname, dbaname, legalowner, namelast, namefirst, licenseno, issdttm, expdttm, licstatus, licensecat, descript, result, resultdttm, violation, viol_level, violdesc, violdttm, viol_status, status_date, comments, address, city, state, zip, property_id, location`
- Recency check: `SELECT MAX("resultdttm") FROM "4582bec6-2b4f-4f9e-bc55-cbaa73117f4c"` via `datastore_search_sql`

### Still to check
- [ ] Active Food Establishment Licenses: resource ID, row count
- [ ] 311 Service Requests: resource ID(s), old vs new system (issue #5)
- [ ] Join key between inspections and licenses (likely `licenseno`)
