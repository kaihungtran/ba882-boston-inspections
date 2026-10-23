-- int_license_crosswalk: one row per record in the active licenses feed, with the inspection license_number
-- it belongs to. Spec: ml/dbt_feature_spec.md §3.3 and docs/data_model.md.
-- The licenses feed has no license number, so records are matched in passes, strongest first:
--   1. name_category_address  name_key + license_category + addr_key (the spec's key)
--   2. property_id_name       property_id + name_key (spec suggests property_id as a tie-breaker)
--   3. address_category       addr_key + license_category
-- A pass only counts when its key points to exactly one license_number on the inspections side
-- ("drop any key that maps to more than one license number"). Unmatched rows keep license_number NULL;
-- list them with analyses/int_license_crosswalk_unmatched.sql for manual review.
-- Used for the scoring population and QA, not for training.

{{ config(materialized='table', schema='intermediate') }}

with license_feed as (
    select
        to_hex(md5(concat(
            coalesce(name_key, ''), '|', coalesce(addr_key, ''), '|',
            coalesce(property_id, ''), '|', coalesce(license_category, '')
        )))                                                             as license_row_key,
        *
    from {{ ref('stg_food_licenses') }}
    where true
    qualify row_number() over (
        partition by name_key, addr_key, property_id, license_category
        order by business_name, address
    ) = 1
),

-- Every name/address/category/property combination a license number has used in the inspections feed.
inspection_keys as (
    select distinct
        license_number,
        regexp_replace(upper(business_name), r'[^A-Z0-9]', '')         as name_key,   -- same rule as stg_food_licenses
        coalesce(regexp_extract(upper(address), r'^(\S+\s+\S+)'), upper(address)) as addr_key,
        license_category,
        property_id
    from {{ ref('stg_food_inspections') }}
),

candidates as (
    select f.license_row_key, k.license_number, 1 as priority, 'name_category_address' as match_method
    from license_feed as f
    join inspection_keys as k
      on k.name_key = f.name_key
     and k.license_category = f.license_category
     and k.addr_key = f.addr_key

    union all

    select f.license_row_key, k.license_number, 2, 'property_id_name'
    from license_feed as f
    join inspection_keys as k
      on k.property_id = f.property_id
     and k.name_key = f.name_key

    union all

    select f.license_row_key, k.license_number, 3, 'address_category'
    from license_feed as f
    join inspection_keys as k
      on k.addr_key = f.addr_key
     and k.license_category = f.license_category
),

unambiguous as (
    -- Named matched_license_number, not license_number: BigQuery would otherwise read the HAVING clause's
    -- license_number as this aggregate ("aggregations of aggregations are not allowed").
    select license_row_key, priority, match_method, any_value(license_number) as matched_license_number
    from candidates
    group by license_row_key, priority, match_method
    having count(distinct candidates.license_number) = 1
),

best as (
    select *
    from unambiguous
    where true
    qualify row_number() over (partition by license_row_key order by priority) = 1
)

select
    f.license_row_key,
    b.matched_license_number                                            as license_number,
    b.match_method,
    b.matched_license_number is not null                                as is_matched,
    count(b.matched_license_number) over (partition by b.matched_license_number) > 1 as is_license_number_shared,
    f.business_name,
    f.name_key,
    f.address,
    f.addr_key,
    f.license_category,
    f.property_id,
    f.license_added_at,                                                 -- never a model feature
    f.latitude,
    f.longitude
from license_feed as f
left join best as b
  on b.license_row_key = f.license_row_key