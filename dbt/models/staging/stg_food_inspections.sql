-- Starter model. Column names below are guesses: confirm against raw.food_inspections.
with source as (
    select * from {{ source('raw', 'food_inspections') }}
)

select
    cast(licenseno as string)      as license_number,
    trim(businessname)             as business_name,
    cast(resultdttm as timestamp)  as inspected_at,
    result                         as result_code,
    violation                      as violation_code,
    viol_level                     as violation_level,
    violdesc                       as violation_description,
    comments                       as inspector_comments
from source
