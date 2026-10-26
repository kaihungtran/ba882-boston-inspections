-- stg_food_inspections: one row per violation (an inspection with no violations keeps one row).
-- Spec: docs/staging_columns.md. Source: raw.food_inspections (raw_api_ingest, incremental,
-- 30-day lookback, partitioned by _load_date).
--
-- Table-level cleaning:
--   1. Keep the newest copy of each record (each daily load repeats the last 30 days). The city's
--      _id isn't a durable key, so records are matched on their content instead.
--   2. Drop rows with no parseable inspection date.
--   3. Drop admin records (not inspections).
--   4. Drop rows with a blank license number.

with source as (
    select * from {{ source('raw', 'food_inspections') }}
),

latest_copy as (
    select *
    from source
    where true
    qualify row_number() over (
        partition by licenseno, resultdttm, violation, violdesc, violdttm, comments
        order by _load_date desc, safe_cast(_id as int64) desc
    ) = 1
),

cleaned as (
    select
        safe_cast(_id as int64)                                         as source_row_id,
        {{ clean_text('licenseno') }}                                   as license_number,
        {{ squish('businessname') }}                                    as business_name,
        upper({{ clean_text('licensecat') }})                           as license_category,
        {{ clean_text('descript') }}                                    as license_description,
        {{ clean_text('licstatus') }}                                   as license_status,      -- scoring population only, never a feature
        {{ safe_ts('issdttm') }}                                        as license_issued_at,   -- never a feature
        {{ safe_ts('expdttm') }}                                        as license_expires_at,  -- never a feature
        {{ clean_text('result') }}                                      as result_code,
        {{ safe_ts('resultdttm') }}                                     as inspected_at,
        {{ clean_text('violation') }}                                   as violation_code,
        {{ clean_text('viol_level') }}                                  as violation_level_raw,
        {{ squish('violdesc') }}                                        as violation_description,
        {{ safe_ts('violdttm') }}                                       as violation_at,
        {{ clean_text('viol_status') }}                                 as violation_status,
        {{ clean_text('comments') }}                                    as inspector_comments,  -- original text, for GenAI
        {{ squish('address') }}                                         as address,
        {{ clean_city('city') }}                                        as city,
        upper({{ clean_text('state') }})                                as state,
        {{ clean_text('zip') }}                                         as zip,                 -- string: keeps leading zeros
        {{ clean_text('property_id') }}                                 as property_id,
        safe_cast(regexp_extract(location, r'\(\s*(-?\d+(?:\.\d+)?)') as float64)           as lat_raw,
        safe_cast(regexp_extract(location, r',\s*(-?\d+(?:\.\d+)?)\s*\)') as float64)       as lon_raw,
        _load_date
    from latest_copy
)

select
    source_row_id,
    license_number,
    business_name,
    license_category,
    license_description,
    license_status,
    license_issued_at,
    license_expires_at,
    result_code,
    coalesce(regexp_contains(lower(result_code), 'fail'), false)       as result_fail,
    inspected_at,
    date(inspected_at)                                                  as inspection_date,     -- UTC; timezone still an open question
    violation_code,
    case
        when violation_code is null then null
        when regexp_contains(violation_code, r'^\d{3}\.\d{3}/') or starts_with(violation_code, 'M-') then 'fda'
        else 'boston_legacy'
    end                                                                 as violation_code_system,
    case
        when starts_with(violation_code, 'M-') then 'M'
        else regexp_extract(violation_code, r'-(P|PF|C)$')
    end                                                                 as fda_severity,
    -- Only *, **, *** are real levels. NULL means "no violation on this row", not missing data.
    case when violation_level_raw in ('*', '**', '***') then violation_level_raw end as violation_level,
    violation_description,
    violation_at,
    violation_status,
    inspector_comments,
    address,
    city,
    state,
    zip,
    property_id,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lat_raw end   as latitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lon_raw end   as longitude,
    _load_date
from cleaned
where inspected_at is not null
  and (result_code is null or result_code not in ('HE_NotReq', 'HE_OutBus', 'DATAERR', 'HE_Misc', 'HE_Hold', 'Closed'))
  and license_number is not null
  and lower(license_number) != 'nan'
