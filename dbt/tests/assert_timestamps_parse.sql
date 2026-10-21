-- Fails if safe_ts can't parse more than 1% of non-blank values in a key timestamp column.
-- Each row returned is a column over the threshold.
{% set checks = [
    ('food_inspections', 'resultdttm'),
    ('requests_311_legacy', 'open_dt'),
    ('requests_311_new', 'open_date'),
] %}

with rates as (
    {% for table, col in checks %}
    select
        '{{ table }}.{{ col }}'                                          as column_checked,
        count(*)                                                         as non_blank,
        countif({{ safe_ts(col) }} is null)                              as unparsed
    from {{ source('raw', table) }}
    where nullif(trim({{ col }}), '') is not null
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

select *, safe_divide(unparsed, non_blank) as unparsed_share
from rates
where safe_divide(unparsed, non_blank) > 0.01
