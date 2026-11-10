-- Match rate by method, and the unmatched licenses-feed records for manual review (spec §3.3).
-- Compile:  dbt compile --select int_license_crosswalk_unmatched --profiles-dir .
-- then run the SQL from target/compiled/.../analyses/ in BigQuery. Manual fixes can go into
-- seeds/license_overrides.csv (docs/data_model.md).

with crosswalk as (
    select * from {{ ref('int_license_crosswalk') }}
)

select
    'summary'                                                           as row_type,
    coalesce(match_method, 'unmatched')                                 as match_method,
    count(*)                                                            as n,
    round(100 * count(*) / sum(count(*)) over (), 1)                    as pct,
    cast(null as string)                                                as business_name,
    cast(null as string)                                                as address,
    cast(null as string)                                                as license_category,
    cast(null as string)                                                as property_id
from crosswalk
group by match_method

union all

select
    'unmatched', null, null, null,
    business_name, address, license_category, property_id
from crosswalk
where not is_matched

order by row_type desc, n desc
