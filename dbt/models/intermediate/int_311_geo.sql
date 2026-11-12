-- int_311_geo: one row per 311 case that the food-safety seed classifies, with a usable point.
-- Input to fct_311_nearby. Spec: ml/dbt_feature_spec.md §3.4. Source: stg_311_requests.
--   * keep: categories in seeds/food_safety_311_categories.csv with a signal_group, a point inside Boston
--     (staging nulls the rest) and opened_at not null. This includes categories kept OUT of the main count
--     (is_food_safety = false, e.g. Improper Storage of Trash) so ML can compare with and without them.
--     The main count is is_food_safety = true; marts must filter on it.
--   * drop default geocodes: cases within var('default_geocode_radius_m') meters of a point in
--     seeds/default_geocode_points.csv (City Hall Plaza and variants, where the city drops cases with no
--     usable address). A fixed list, not a count threshold, so a case's inclusion never depends on cases
--     that arrive later and the result is reproducible. tests/warn_new_geocode_pileup.sql flags new
--     candidates for review.
--   * original category fields are kept for GenAI (type, reason, subject, case_topic, service_name)
--   * neighborhood from stg_neighborhoods (26 neighborhoods, not tracts)

{{ config(materialized='table', schema='intermediate') }}

with cases as (
    select *
    from {{ ref('stg_311_requests') }}
    where (is_food_safety or signal_group is not null)
      and point is not null
      and opened_at is not null
),

default_points as (
    select st_geogpoint(longitude, latitude) as default_point
    from {{ ref('default_geocode_points') }}
),

-- Cases on a default point. Found with an inner spatial join, then excluded by case_id: BigQuery does not
-- allow NOT EXISTS / anti-joins whose only condition is a distance.
on_default_point as (
    select distinct c.case_id
    from cases as c
    join default_points as d
      on st_dwithin(c.point, d.default_point, {{ var('default_geocode_radius_m', 5) }})
),

kept as (
    select c.*
    from cases as c
    left join on_default_point as x
      on x.case_id = c.case_id
    where x.case_id is null
),

neighborhoods as (
    select * from {{ ref('stg_neighborhoods') }}
)

select
    k.case_id,
    k.source_system,
    k.opened_at,
    date(k.opened_at)                                                   as opened_date,
    k.closed_at,
    k.case_status,
    k.case_category,
    k.is_food_safety,
    k.signal_group,
    k.food_safety_theme,
    k.type,
    k.reason,
    k.subject,
    k.case_topic,
    k.service_name,
    k.department,
    k.report_source,
    k.latitude,
    k.longitude,
    k.point,
    n.neighborhood_id,
    n.neighborhood
from kept as k
left join neighborhoods as n
  on st_contains(n.geom, k.point)
where true
qualify row_number() over (partition by k.case_id order by n.neighborhood_id) = 1
