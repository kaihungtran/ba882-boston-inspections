-- One row per establishment x inspection x violation. Column names confirmed 2026-10-13.
-- Rows with no inspection date (e.g. result = 'HE_NotReq') are dropped.
with source as (
    select * from {{ source('raw', 'food_inspections') }}
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
    location
from source
where resultdttm is not null
