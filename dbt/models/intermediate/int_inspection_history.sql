-- int_inspection_history: point-in-time features for every inspection.
-- Spec: ml/dbt_feature_spec.md §4 (feature catalog). One row per inspection, same grain as int_inspections.
--
-- Rules (§1):
--   * A feature for an inspection on date D uses only earlier inspections: every window ends at 1 PRECEDING.
--   * History covers ALL inspections (follow-ups too); the routine-only filter happens in the mart.
--   * No current-snapshot fields (license status, issue/expiry dates) and nothing about the current visit
--     is a feature. The current visit's outcome columns are kept only as the target / for the mart.
--   * Missing means unknown: lag/last-value features are NULL when there is no earlier visit.
--     Running counts (prior_*_total, *_past_365d) are 0 when there is no earlier visit.
-- Not here: neighborhood (from int_establishment_geo / dim_establishment) and complaints_311_near
-- (from fct_311_nearby), both joined in the ml_features mart.

{{ config(materialized='table', schema='intermediate') }}

with inspections as (
    select * from {{ ref('int_inspections') }}
),

-- For each routine visit, the target of the routine visit before it (for prev2_routine_target).
routine_sequence as (
    select
        inspection_id,
        lag(target) over (partition by license_number order by inspection_date) as prev_routine_target
    from inspections
    where is_routine
),

base as (
    select
        i.*,
        r.prev_routine_target
    from inspections as i
    left join routine_sequence as r
      on r.inspection_id = i.inspection_id
),

windowed as (
    select
        *,
        row_number() over w - 1                                         as n_prior_insp,
        min(inspection_date) over (partition by license_number)         as first_inspection_date,

        lag(n_violations) over w                                        as prev_n_violations,
        lag(n_critical) over w                                          as prev_n_critical,
        lag(n_major) over w                                             as prev_n_major,

        coalesce(sum(n_violations) over w_prior, 0)                     as prior_violations_total,
        coalesce(sum(n_critical) over w_prior, 0)                       as prior_critical_total,
        coalesce(sum(target) over w_prior, 0)                           as prior_target_total,
        coalesce(sum(if(result_code in ('HE_Hearing', 'HE_TSOP', 'HE_Closure', 'HE_VolClos'), 1, 0))
                 over w_prior, 0)                                       as prior_enforcement_count,

        coalesce(sum(n_violations) over w_365, 0)                       as violations_past_365d,
        coalesce(sum(n_critical) over w_365, 0)                         as critical_past_365d,
        coalesce(sum(n_major) over w_365, 0)                            as major_past_365d,

        last_value(if(is_routine, n_critical, null) ignore nulls) over w_prior     as last_routine_n_critical,
        last_value(if(is_routine, inspection_date, null) ignore nulls) over w_prior as last_routine_date,
        -- Wrapped in a struct so a NULL target on the last routine visit isn't skipped by IGNORE NULLS.
        last_value(if(is_routine, struct(prev_routine_target as v), null) ignore nulls) over w_prior
                                                                        as last_routine_prev
    from base
    window
        w as (partition by license_number order by inspection_date),
        w_prior as (
            partition by license_number order by inspection_date
            rows between unbounded preceding and 1 preceding
        ),
        w_365 as (
            partition by license_number order by unix_date(inspection_date)
            range between 365 preceding and 1 preceding
        )
)

select
    -- keys and current-visit outcome (labels, not features)
    inspection_id,
    license_number,
    inspection_date,
    is_routine,
    is_followup,
    target,
    result_fail,                                                        -- comparison only
    n_major,                                                            -- for the alternative target (** or ***)
    n_critical,

    -- context
    license_category,
    city_clean,                                                         -- P2 stopgap until neighborhood
    latitude,
    longitude,
    fda_code_era,
    extract(month from inspection_date)                                 as month,

    -- history features (P0)
    last_routine_n_critical,
    prior_violations_total,
    date_diff(inspection_date, first_inspection_date, day)              as days_since_first_insp,
    days_since_prev,
    prev_n_violations,
    date_diff(inspection_date, last_routine_date, day)                  as days_since_last_routine,
    violations_past_365d,
    prior_target_total / nullif(n_prior_insp, 0)                        as prior_critical_rate,
    prev_n_critical,
    critical_past_365d,
    n_prior_insp,
    cast(prev_result_fail as int64)                                     as prev_result_fail,
    prior_critical_total,

    -- new features to try (P1)
    prev_n_major,
    major_past_365d,
    last_routine_n_critical > 0                                         as last_routine_had_critical,
    last_routine_prev.v                                                 as prev2_routine_target,
    prior_enforcement_count,

    -- P2
    prev_inspection_date > last_routine_date                            as had_followup_since_last_routine
from windowed
