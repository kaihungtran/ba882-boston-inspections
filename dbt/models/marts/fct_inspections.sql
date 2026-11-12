-- fct_inspections: one row per inspection (license_number + inspection_date). Used by the dashboard and as the
-- spine for the ML marts. From int_inspections (spec §3.1 in ml/dbt_feature_spec.md).
--   * target = 1 when the inspection had at least one critical (***) violation.
--   * is_routine / is_followup: follow-up = previous visit failed or had a critical within 30 days.
--   * license_number -> dim_establishment; fct_violations.inspection_id -> this table.

with inspections as (
    select * from {{ ref('int_inspections') }}
)

select
    inspection_id,
    license_number,
    inspection_date,
    result_code,
    result_fail,
    n_violations,
    n_critical,
    n_major,
    n_minor,
    target,
    is_routine,
    is_followup,
    fda_code_era,
    prev_inspection_date,
    days_since_prev,
    license_category,
    latitude,
    longitude
from inspections
