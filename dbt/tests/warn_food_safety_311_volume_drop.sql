-- Warns when food-safety 311 volume over the last 7 days falls below half of the daily average
-- over the 4 weeks before. That's what the Inspectional Services move to the new 311 system will
-- look like if nobody adds its categories to seeds/food_safety_311_categories.csv.
-- (Weekly rather than single-day comparison, so weekends don't trigger it.)
{{ config(severity='warn') }}

with daily as (
    select date(opened_at) as d, count(*) as cases
    from {{ ref('stg_311_requests') }}
    where is_food_safety
      and date(opened_at) between date_sub(current_date(), interval 35 day) and date_sub(current_date(), interval 1 day)
    group by 1
),

windows as (
    select
        sum(if(d >= date_sub(current_date(), interval 7 day), cases, 0)) / 7    as recent_daily_avg,
        sum(if(d <  date_sub(current_date(), interval 7 day), cases, 0)) / 28   as baseline_daily_avg
    from daily
)

select *
from windows
where baseline_daily_avg > 0
  and recent_daily_avg < 0.5 * baseline_daily_avg
