-- fct_violations: one row per violation. Used by GenAI (violation theme tagging, restaurant summaries) and for
-- violation-level analysis. Grain, keys and dedupe come from int_violations: an edited inspector comment is one
-- row (its latest wording), not two.
--   * violation_description and inspector_comments are the full original text (staging only trims them).
--   * inspection_id -> fct_inspections, license_number -> dim_establishment.
--   * The placeholder row kept upstream for an inspection with no violations is excluded here.

with violations as (
    select * from {{ ref('int_violations') }}
)

select
    violation_id,
    inspection_id,
    license_number,
    inspection_date,
    inspected_at,
    violation_code,
    violation_code_system,
    fda_severity,
    violation_level,
    violation_description,
    violation_at,
    violation_status,
    inspector_comments,
    result_code,
    source_row_id,
    source_load_date
from violations
where violation_code is not null
   or violation_description is not null
