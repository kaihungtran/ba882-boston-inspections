-- dim_establishment: one row per establishment (license_number). From int_establishment_geo (spec §3.2).
--   * latest name / address / category; median location over its inspections, else the matched license record's
--   * neighborhood_id -> dim_neighborhood (26 neighborhoods; census tracts are not available yet)
--   * is_active_license: for choosing the scoring population only, never a model feature

with establishments as (
    select * from {{ ref('int_establishment_geo') }}
)

select
    license_number,
    business_name,
    address,
    city_clean,
    license_category,
    is_active_license,
    first_inspection_date,
    last_inspection_date,
    n_inspections,
    latitude,
    longitude,
    location_source,
    neighborhood_id,
    neighborhood,
    neighborhood_source,
    license_match_method,
    matched_license_feed_row
from establishments
