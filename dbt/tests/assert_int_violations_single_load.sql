-- Every inspection's violation rows must come from one daily load (its latest). Two loads inside one
-- inspection would mean an edited comment was counted twice.
select inspection_id, count(distinct source_load_date) as loads
from {{ ref('int_violations') }}
group by inspection_id
having count(distinct source_load_date) > 1
