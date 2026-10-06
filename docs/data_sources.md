# Data Sources

| Source | Portal | Updates | Access | Notes |
|---|---|---|---|---|
| Food Establishment Inspections | [data.boston.gov](https://data.boston.gov/dataset/food-establishment-inspections) | Daily | CKAN `datastore_search` API | Marked **legacy**: confirm latest record date before relying on it |
| 311 Service Requests | [data.boston.gov](https://data.boston.gov/dataset/311-service-requests) | Daily | CKAN API | Moving to a new system with a different schema; see the city's [transition guide](https://data.boston.gov/dataset/311-service-requests/resource/6e86da47-9b6c-459a-ab97-0e64045081a0) |
| Active Food Establishment Licenses | [data.boston.gov](https://data.boston.gov/dataset/active-food-establishment-licenses) | Daily | CKAN API | Master list of establishments |
| Neighborhood boundaries | [data.boston.gov](https://data.boston.gov/dataset/boston-neighborhood-boundaries-approximated-by-2020-census-tracts) | Static | GeoJSON / shapefile | Spatial join with establishments and 311 |
| Census ACS 5-year | [census.gov](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Annual | Census API (free key) | Tract-level context |

## To fill in after the data-access check
- [ ] CKAN resource IDs for each dataset (put in `.env.example`)
- [ ] Latest inspection date found: ____
- [ ] Row counts and date range per source
- [ ] Join keys between inspections and licenses
