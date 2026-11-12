-- Warn when a point that is not in seeds/default_geocode_points.csv looks like a default geocode:
-- many unrelated 311 categories piled on one exact coordinate (City Hall had 10 categories, 389 cases).
-- Real addresses with many complaints usually show 1-3 categories (mostly trash), so they don't trigger it.
-- Review each flagged point; add it to the seed if it is a default geocode. Nothing is removed automatically.
{{ config(severity='warn') }}

with cases as (
    select *
    from {{ ref('stg_311_requests') }}
    where (is_food_safety or signal_group is not null)
      and point is not null
),

default_points as (
    select st_geogpoint(longitude, latitude) as default_point
    from {{ ref('default_geocode_points') }}
),

on_default_point as (
    select distinct c.case_id
    from cases as c
    join default_points as d
      on st_dwithin(c.point, d.default_point, {{ var('default_geocode_radius_m', 5) }})
),

unlisted as (
    select c.*
    from cases as c
    left join on_default_point as x
      on x.case_id = c.case_id
    where x.case_id is null
),

by_point as (
    select
        st_astext(point)                                                as point_wkt,
        count(*)                                                        as n_cases,
        count(distinct case_category)                                   as n_categories
    from unlisted
    group by point_wkt
)

select *
from by_point
where n_categories >= {{ var('pileup_min_categories', 6) }}
  and n_cases >= {{ var('pileup_min_cases', 30) }}
