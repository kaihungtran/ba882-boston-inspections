-- dim_neighborhood: one row per Boston neighborhood (26), with its boundary. From stg_neighborhoods.
-- Neighborhood-level only: docs/data_model.md plans census tracts with ACS columns, which need tract shapes.

with neighborhoods as (
    select * from {{ ref('stg_neighborhoods') }}
)

select
    neighborhood_id,
    neighborhood,
    acres,
    sqmiles,
    geom
from neighborhoods
