-- stg_food_licenses: one row per active license in the latest daily snapshot.
-- Spec: docs/staging_columns.md. Source: raw.food_licenses (raw_api_ingest, full snapshot per _load_date).
-- This feed has no license number, so name_key / addr_key / property_id are the matching keys.

with source as (
    select * from {{ source('raw', 'food_licenses') }}
),

latest_snapshot as (
    -- Each day appends a full snapshot; without this every license repeats once per load.
    select *
    from source
    where _load_date = (select max(_load_date) from source)
),

cleaned as (
    select
        {{ squish('businessname') }}                                    as business_name,
        {{ squish('address') }}                                         as address,
        upper({{ clean_text('licensecat') }})                           as license_category,
        {{ clean_city('city') }}                                        as city,
        upper({{ clean_text('state') }})                                as state,
        {{ clean_text('zip') }}                                         as zip,
        {{ clean_text('descript') }}                                    as license_description,
        {{ safe_ts('license_add_dt_tm') }}                              as license_added_at,  -- never a feature
        {{ clean_text('property_id') }}                                 as property_id,
        safe_cast(latitude as float64)                                  as lat_raw,
        safe_cast(longitude as float64)                                 as lon_raw,
        _load_date
    from latest_snapshot
)

select
    business_name,
    regexp_replace(upper(business_name), r'[^A-Z0-9]', '')             as name_key,
    address,
    coalesce(regexp_extract(upper(address), r'^(\S+\s+\S+)'), upper(address)) as addr_key,
    license_category,
    city,
    state,
    zip,
    license_description,
    license_added_at,
    property_id,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lat_raw end   as latitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lon_raw end   as longitude,
    _load_date
from cleaned
