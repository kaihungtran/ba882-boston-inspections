-- int_inspections: violation rows -> one row per inspection (license_number + inspection_date).
-- Spec: ml/dbt_feature_spec.md §3.1 and docs/data_model.md. Source: stg_food_inspections (one row per violation).
--
-- target         = has at least one critical (***) violation, as 0/1
-- is_followup    = previous visit failed or had a critical, and came within var('followup_window_days') days
-- is_routine     = not a follow-up. The ML training mart keeps routine inspections only.
-- History over all inspections (including follow-ups) is built in int_inspection_history.

{{ config(materialized='table', schema='intermediate') }}

with violations as (
    select * from {{ ref('stg_food_inspections') }}
),

inspections as (
    select
        farm_fingerprint(concat(license_number, '|', cast(inspection_date as string))) as inspection_id,
        license_number,
        inspection_date,
        count(*)                                                        as n_rows,
        countif(violation_level in ('*', '**', '***'))                  as n_violations,
        countif(violation_level = '***')                                as n_critical,
        countif(violation_level = '**')                                 as n_major,
        countif(violation_level = '*')                                  as n_minor,
        logical_or(result_fail)                                         as result_fail,
        any_value(result_code)                                          as result_code,     -- rows disagree in 0.29% of inspections
        any_value(license_category)                                     as license_category,
        any_value(business_name)                                        as business_name,
        any_value(city)                                                 as city_clean,
        approx_quantiles(latitude, 2)[safe_offset(1)]                   as latitude,        -- median
        approx_quantiles(longitude, 2)[safe_offset(1)]                  as longitude,
        countif(inspector_comments is not null)                         as n_comments
    from violations
    group by license_number, inspection_date
),

with_target as (
    select
        *,
        cast(n_critical > 0 as int64)                                   as target,
        cast(inspection_date >= '2020-01-01' as int64)                  as fda_code_era
    from inspections
),

sequenced as (
    select
        *,
        lag(inspection_date) over w                                     as prev_inspection_date,
        lag(result_fail) over w                                         as prev_result_fail,
        lag(target) over w                                              as prev_target
    from with_target
    window w as (partition by license_number order by inspection_date)
),

flagged as (
    select
        *,
        date_diff(inspection_date, prev_inspection_date, day)           as days_since_prev,
        (prev_result_fail or prev_target = 1)
            and date_diff(inspection_date, prev_inspection_date, day) <= {{ var('followup_window_days', 30) }}
                                                                        as is_followup
    from sequenced
)

select
    inspection_id,
    license_number,
    inspection_date,
    n_rows,
    n_violations,
    n_critical,
    n_major,
    n_minor,
    result_fail,
    result_code,
    license_category,
    business_name,
    city_clean,
    latitude,
    longitude,
    n_comments,
    target,
    fda_code_era,
    prev_inspection_date,
    days_since_prev,
    prev_result_fail,
    prev_target,
    is_followup,
    not coalesce(is_followup, false)                                    as is_routine
from flagged
