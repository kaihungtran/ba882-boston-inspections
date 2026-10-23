-- stg_311_requests_new: one row per case from the new 311 system (since Aug 2025).
-- Spec: docs/staging_columns.md. Source: raw.requests_311_new (raw_api_ingest, incremental,
-- 30-day lookback on open_date). Column names confirmed 2026-10-21 from INFORMATION_SCHEMA.
-- Case IDs look like BCS-00119697 and don't overlap with legacy IDs (checked 2026-10-21).

with raw_rows as (
    select * from {{ source('raw', 'requests_311_new') }}
),

latest_copy as (
    select *
    from raw_rows
    where {{ clean_text('case_id') }} is not null
    qualify row_number() over (
        partition by trim(case_id)
        order by _load_date desc, safe_cast(_id as int64) desc
    ) = 1
),

cleaned as (
    select
        {{ clean_text('case_id') }}                                     as case_id,
        {{ safe_ts('open_date') }}                                      as opened_at,
        {{ safe_ts('close_date') }}                                     as closed_at,
        {{ clean_text('case_status') }}                                 as case_status,
        {{ clean_text('case_topic') }}                                  as case_topic,        -- original, kept for GenAI
        {{ clean_text('service_name') }}                                as service_name,      -- original, kept for GenAI
        {{ clean_text('assigned_department') }}                         as department,
        {{ clean_text('report_source') }}                               as report_source,     -- values differ from legacy (e.g. BOS311)
        safe_cast(latitude as float64)                                  as lat_raw,
        safe_cast(longitude as float64)                                 as lon_raw,
        _load_date
    from latest_copy
)

select
    case_id,
    'new'                                                               as source_system,
    opened_at,
    closed_at,
    case_status,
    case_topic,
    service_name,
    coalesce(case_topic, service_name)                                  as case_category,     -- seed lookup key
    department,
    report_source,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lat_raw end   as latitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lon_raw end   as longitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then st_geogpoint(lon_raw, lat_raw) end as point,
    _load_date
from cleaned
