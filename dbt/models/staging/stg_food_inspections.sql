-- One row per establishment x inspection x violation.
-- Source: raw.food_inspections, loaded by the raw_api_ingest DAG. All columns arrive as text,
-- plus _load_date. Each daily load re-pulls the last 30 days, so the same record sits in many
-- _load_date partitions: keep only the copy from the most recent load.
-- Rows with no inspection date (e.g. result = 'HE_NotReq') are dropped.
--
-- Dedup key assumption: licenseno + resultdttm + violation + violdesc + violdttm + comments
-- identifies one record. Refine if we find two genuinely different rows sharing it.

with source as (
    select * from {{ source('raw', 'food_inspections') }}
),

deduped as (
    select *
    from source
    where resultdttm is not null
    qualify row_number() over (
        partition by licenseno, resultdttm, violation, violdesc, violdttm, comments
        order by _load_date desc, safe_cast(_id as int64) desc
    ) = 1
)

select
    cast(licenseno as string)                 as license_number,
    trim(businessname)                        as business_name,
    trim(dbaname)                             as dba_name,
    licensecat                                as license_category,
    descript                                  as license_description,
    licstatus                                 as license_status,
    cast(resultdttm as timestamp)             as inspected_at,
    result                                    as result_code,
    violation                                 as violation_code,
    viol_level                                as violation_level,
    violdesc                                  as violation_description,
    cast(violdttm as timestamp)               as violation_at,
    viol_status                               as violation_status,
    comments                                  as inspector_comments,
    trim(address)                             as address,
    trim(city)                                as city,
    zip,
    location,
    _load_date                                as loaded_on
from deduped
