-- Warn if fewer than 85% of licenses-feed records match an inspection license number
-- (docs/data_model.md open item; the notebook matched 87.4%).
{{ config(severity='warn') }}

select
    countif(is_matched)                                                 as matched,
    count(*)                                                            as total,
    safe_divide(countif(is_matched), count(*))                          as match_rate
from {{ ref('int_license_crosswalk') }}
having safe_divide(countif(is_matched), count(*)) < 0.85
