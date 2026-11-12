-- int_inspections must have one row per license_number + inspection_date (spec §3.1).
select license_number, inspection_date, count(*) as n
from {{ ref('int_inspections') }}
group by license_number, inspection_date
having count(*) > 1
