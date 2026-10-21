-- stg_311_requests: legacy + new 311 cases in one shape, with is_food_safety from the seed.
-- Legacy-only columns (case_title, type, reason, subject) and new-only columns (case_topic,
-- service_name) are NULL on the other feed's rows.
-- No cross-feed dedupe: the two systems use different ID formats with no overlap (checked 2026-10-21).
-- When Inspectional Services moves to the new system (planned Fall 2026), add its categories to
-- seeds/food_safety_311_categories.csv, or the food-safety volume will drop (see the warn test).

with legacy as (
    select
        case_id, source_system, opened_at, closed_at, case_status,
        case_title, type, reason, subject,
        cast(null as string) as case_topic,
        cast(null as string) as service_name,
        case_category, department, report_source,
        latitude, longitude, point, _load_date
    from {{ ref('stg_311_requests_legacy') }}
),

new_system as (
    select
        case_id, source_system, opened_at, closed_at, case_status,
        cast(null as string) as case_title,
        cast(null as string) as type,
        cast(null as string) as reason,
        cast(null as string) as subject,
        case_topic, service_name,
        case_category, department, report_source,
        latitude, longitude, point, _load_date
    from {{ ref('stg_311_requests_new') }}
),

unioned as (
    select * from legacy
    union all
    select * from new_system
)

select
    u.*,
    coalesce(c.is_food_safety, false) as is_food_safety,
    c.theme                           as food_safety_theme
from unioned as u
left join {{ ref('food_safety_311_categories') }} as c
    on c.source_system = u.source_system
   and c.case_category = u.case_category
