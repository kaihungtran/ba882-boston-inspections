-- stg_neighborhoods: one row per Boston neighborhood (26), with its boundary as a GEOGRAPHY.
-- Source: seed neighborhoods.csv, built by scripts/build_neighborhood_seed.py from data.boston.gov.
-- Note: this file is neighborhood-level, not census tracts (no tract GEOID), so it can't key the
-- Census ACS join on its own. Use it for point-in-neighborhood lookups.

select
    cast(neighborhood_id as string)                                     as neighborhood_id,
    trim(neighborhood)                                                  as neighborhood,
    safe_cast(acres as float64)                                         as acres,
    safe_cast(sqmiles as float64)                                       as sqmiles,
    st_geogfromgeojson(geometry_geojson, make_valid => true)            as geom
from {{ ref('neighborhoods') }}
