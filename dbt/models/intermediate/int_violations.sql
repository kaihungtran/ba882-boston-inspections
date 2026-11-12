-- int_violations: one row per violation record, keeping each inspection's rows from its LATEST daily load only.
-- Source: stg_food_inspections (one row per violation; an inspection with no violations keeps one row).
--
-- Why: staging keeps the newest copy of each distinct record, and its key includes the comment text. When the
-- city edits an inspector comment, the old wording (seen only in earlier loads) and the new wording would both
-- survive as two rows. Each daily load re-pulls an inspection's rows together, so keeping only the rows from
-- the inspection's latest load drops superseded versions (and rows the city removed) while keeping genuinely
-- separate violations, which all appear in that latest load.
--
-- Keys: inspection_id matches int_inspections (license_number + inspection_date). violation_id is a stable hash
-- of the violation's identifying fields plus an ordinal for exact repeats within one inspection.
-- Text fields (violation_description, inspector_comments) are kept exactly as staged, for GenAI.

{{ config(materialized='table', schema='intermediate') }}

with records as (
    select * from {{ ref('stg_food_inspections') }}
),

latest_snapshot as (
    select *
    from records
    where true
    qualify _load_date = max(_load_date) over (partition by license_number, inspection_date)
),

numbered as (
    select
        *,
        row_number() over (
            partition by license_number, inspected_at, violation_code, violation_description
            order by source_row_id
        )                                                               as repeat_ordinal
    from latest_snapshot
)

select
    farm_fingerprint(concat(license_number, '|', cast(inspection_date as string))) as inspection_id,
    farm_fingerprint(concat(
        license_number, '|', cast(inspected_at as string), '|',
        coalesce(violation_code, ''), '|', coalesce(violation_description, ''), '|',
        cast(repeat_ordinal as string)
    ))                                                                  as violation_id,
    license_number,
    inspection_date,
    inspected_at,
    source_row_id,
    business_name,
    license_category,
    license_description,
    license_status,
    result_code,
    result_fail,
    violation_code,
    violation_code_system,
    fda_severity,
    violation_level,
    violation_description,
    violation_at,
    violation_status,
    inspector_comments,
    address,
    city,
    zip,
    property_id,
    latitude,
    longitude,
    _load_date                                                          as source_load_date
from numbered
