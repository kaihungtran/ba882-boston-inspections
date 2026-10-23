-- int_establishment_geo: one row per license_number, the base for dim_establishment.
-- Spec: ml/dbt_feature_spec.md §3.2 and docs/data_model.md.
--   * name / address / category / status: most recent record
--   * latitude / longitude: median over all of the license's inspections (about 13% have none);
--     if none, the matched licenses-feed record's coordinates
--   * neighborhood: the stg_neighborhoods boundary containing the point. Without a point, fall back to the
--     cleaned city name when it equals a neighborhood name (e.g. DORCHESTER).
--     Note: stg_neighborhoods has 26 neighborhoods, not census tracts, so there is no tract_geoid yet.
--   * is_active_license: scoring population only, never a model feature

{{ config(materialized='table', schema='intermediate') }}

with records as (
    select * from {{ ref('stg_food_inspections') }}
),

inspections as (
    select * from {{ ref('int_inspections') }}
),

neighborhoods as (
    select * from {{ ref('stg_neighborhoods') }}
),

latest as (
    select
        license_number,
        business_name,
        address,
        city                                                            as city_clean,
        license_category,
        license_status
    from records
    where true
    qualify row_number() over (
        partition by license_number
        order by inspected_at desc, source_row_id desc
    ) = 1
),

per_license as (
    select
        license_number,
        min(inspection_date)                                            as first_inspection_date,
        max(inspection_date)                                            as last_inspection_date,
        count(*)                                                        as n_inspections,
        approx_quantiles(latitude, 2)[safe_offset(1)]                   as latitude,
        approx_quantiles(longitude, 2)[safe_offset(1)]                  as longitude
    from inspections
    group by license_number
),

crosswalk as (
    select *
    from {{ ref('int_license_crosswalk') }}
    where license_number is not null
    qualify row_number() over (
        partition by license_number
        order by case match_method
                     when 'name_category_address' then 1
                     when 'property_id_name' then 2
                     else 3
                 end,
                 license_row_key
    ) = 1
),

located as (
    select
        l.license_number,
        l.business_name,
        l.address,
        l.city_clean,
        l.license_category,
        l.license_status = 'Active'                                     as is_active_license,
        p.first_inspection_date,
        p.last_inspection_date,
        p.n_inspections,
        c.license_row_key                                               as matched_license_feed_row,
        c.match_method                                                  as license_match_method,
        coalesce(p.latitude, c.latitude)                                as latitude,
        coalesce(p.longitude, c.longitude)                              as longitude,
        case
            when p.latitude is not null then 'inspections'
            when c.latitude is not null then 'licenses'
        end                                                             as location_source
    from latest as l
    left join per_license as p on p.license_number = l.license_number
    left join crosswalk as c on c.license_number = l.license_number
),

with_point as (
    select
        *,
        case when latitude is not null and longitude is not null
             then st_geogpoint(longitude, latitude) end                 as point
    from located
),

by_point as (
    select
        p.*,
        n.neighborhood_id                                               as point_neighborhood_id,
        n.neighborhood                                                  as point_neighborhood
    from with_point as p
    left join neighborhoods as n
      on st_contains(n.geom, p.point)
    where true
    qualify row_number() over (partition by p.license_number order by n.neighborhood_id) = 1
)

select
    b.license_number,
    b.business_name,
    b.address,
    b.city_clean,
    b.license_category,
    b.is_active_license,
    b.first_inspection_date,
    b.last_inspection_date,
    b.n_inspections,
    b.matched_license_feed_row,
    b.license_match_method,
    b.latitude,
    b.longitude,
    b.point,
    b.location_source,
    coalesce(b.point_neighborhood_id, c.neighborhood_id)                as neighborhood_id,
    coalesce(b.point_neighborhood, c.neighborhood)                      as neighborhood,
    case
        when b.point_neighborhood_id is not null then 'point'
        when c.neighborhood_id is not null then 'city_name'
    end                                                                 as neighborhood_source
from by_point as b
left join neighborhoods as c
  on b.point_neighborhood_id is null
 and upper(c.neighborhood) = b.city_clean
