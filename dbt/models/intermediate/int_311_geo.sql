-- int_311_geo: one row per 311 case that the food-safety seed classifies, with a usable point.
-- Input to fct_311_nearby. Spec: ml/dbt_feature_spec.md §3.4. Source: stg_311_requests.
--   * keep: categories in seeds/food_safety_311_categories.csv with a signal_group, a point inside Boston
--     (staging nulls the rest) and opened_at not null. This includes categories kept OUT of the main count
--     (is_food_safety = false, e.g. Improper Storage of Trash) so ML can compare with and without them.
--     The main count is is_food_safety = true; marts must filter on it.
--   * drop default-geocode points: a point holding more than max(50, 1% of food-safety cases) of these
--     cases. When a caller gives no address the city drops the case on a fixed spot (e.g. City Hall).
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

point_counts as (
    select
        st_astext(point)                                                as point_wkt,
        count(*)                                                        as cases_at_point
    from cases
    group by point_wkt
),

threshold as (
    select greatest({{ var('default_geocode_min_cases', 50) }}, 0.01 * countif(is_food_safety)) as max_cases_per_point
    from cases
),

kept as (
    select c.*
    from cases as c
    join point_counts as pc
      on pc.point_wkt = st_astext(c.point)
    cross join threshold as t
    where pc.cases_at_point <= t.max_cases_per_point
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
