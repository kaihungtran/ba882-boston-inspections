-- Leakage asserts from ml/dbt_feature_spec.md §5, checked on the feature model itself:
--   * no earlier inspections  =>  no prior criticals
--   * criticals in the past 365 days can't exceed all prior criticals
--   * the first visit has no previous-visit values
select inspection_id, n_prior_insp, prior_critical_total, critical_past_365d, prev_n_critical
from {{ ref('int_inspection_history') }}
where (n_prior_insp = 0 and prior_critical_total != 0)
   or critical_past_365d > prior_critical_total
   or (n_prior_insp = 0 and prev_n_critical is not null)
