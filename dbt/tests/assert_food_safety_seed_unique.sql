-- Each (source_system, case_category) appears once in the 311 food-safety seed,
-- otherwise the join in stg_311_requests would duplicate cases.
select source_system, case_category, count(*) as n
from {{ ref('food_safety_311_categories') }}
group by 1, 2
having count(*) > 1
