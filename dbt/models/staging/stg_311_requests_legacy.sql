-- stg_311_requests_legacy: one row per case from the old 311 system.
-- Spec: docs/staging_columns.md. Source: raw.requests_311_legacy (raw_api_ingest, incremental,
-- 30-day lookback on open_dt). Each daily partition repeats the last 30 days, so keep the newest copy.
-- Default-geocode points (e.g. City Hall) are removed later, in int_311_geo.

with raw_rows as (
    select * from {{ source('raw', 'requests_311_legacy') }}
),

latest_copy as (
    select *
    from raw_rows
    where {{ clean_text('case_enquiry_id') }} is not null
    qualify row_number() over (
        partition by trim(case_enquiry_id)
        order by _load_date desc, safe_cast(_id as int64) desc
    ) = 1
),

cleaned as (
    select
        {{ clean_text('case_enquiry_id') }}                             as case_id,
        {{ safe_ts('open_dt') }}                                        as opened_at,
        {{ safe_ts('closed_dt') }}                                      as closed_at,
        {{ clean_text('case_status') }}                                 as case_status,
        {{ clean_text('case_title') }}                                  as case_title,        -- original text, for GenAI
        {{ clean_text('type') }}                                        as type,              -- original, kept for GenAI
        {{ clean_text('reason') }}                                      as reason,
        {{ clean_text('subject') }}                                     as subject,
        {{ clean_text('department') }}                                  as department,
        {{ clean_text('source') }}                                      as report_source,
        safe_cast(latitude as float64)                                  as lat_raw,
        safe_cast(longitude as float64)                                 as lon_raw,
        _load_date
    from latest_copy
)

select
    case_id,
    'legacy'                                                            as source_system,
    opened_at,
    closed_at,
    case_status,
    case_title,
    type,
    reason,
    subject,
    type                                                                as case_category,     -- seed lookup key
    department,
    report_source,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lat_raw end   as latitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then lon_raw end   as longitude,
    case when {{ in_boston('lat_raw', 'lon_raw') }} then st_geogpoint(lon_raw, lat_raw) end as point,
    _load_date
from cleaned
