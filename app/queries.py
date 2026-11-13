"""All SQL used by the app. Table names come from settings via config.table() / config.int_table().

Inspection-level pages read the dbt intermediate layer: int_inspections (one row per license +
date, violations rolled up, routine vs follow-up flagged) and int_establishment_geo (one row per
license with its neighborhood). Violation rows still come from stg_food_inspections. Swap to the
marts (fct_inspections, dim_establishment) once PR #44 lands.
"""

from config import int_table, table


def inspections_monthly() -> str:
    return f"""
    select
        date_trunc(inspection_date, month) as month,
        coalesce(license_category, 'Unknown') as license_category,
        is_routine,
        count(*)            as n_inspections,
        countif(result_fail) as n_failed,
        countif(target = 1)  as n_critical
    from {int_table('int_inspections')}
    group by month, license_category, is_routine
    order by month
    """


def inspections_by_neighborhood() -> str:
    return f"""
    -- Neighborhood is assigned in int_establishment_geo (point in boundary, else the city name).
    select
        coalesce(e.neighborhood, 'Unmatched') as neighborhood,
        extract(year from i.inspection_date)  as year,
        i.is_routine,
        count(*)                              as n_inspections,
        countif(i.result_fail)                as n_failed,
        count(distinct i.license_number)      as n_establishments
    from {int_table('int_inspections')} as i
    left join {int_table('int_establishment_geo')} as e
        using (license_number)
    group by neighborhood, year, is_routine
    """


def violations_by_type() -> str:
    return f"""
    select
        violation_description,
        violation_level,
        extract(year from inspection_date) as year,
        count(*) as n_violations
    from {table('stg_food_inspections')}
    where violation_level is not null
      and violation_description is not null
    group by violation_description, violation_level, year
    """


def neighborhood_shapes() -> str:
    return f"""
    select
        neighborhood,
        sqmiles,
        st_asgeojson(st_simplify(geom, 10)) as geojson
    from {table('stg_neighborhoods')}
    """


def food_safety_311_monthly() -> str:
    return f"""
    select
        date_trunc(date(opened_at), month)    as month,
        coalesce(food_safety_theme, 'other')  as theme,
        coalesce(signal_group, 'unclassified') as signal_group,
        count(*)                              as n_cases
    from {table('stg_311_requests')}
    where is_food_safety
      and opened_at is not null
    group by month, theme, signal_group
    order by month
    """


def food_safety_311_by_neighborhood() -> str:
    return f"""
    select
        coalesce(n.neighborhood, 'Unmatched')  as neighborhood,
        coalesce(r.food_safety_theme, 'other') as theme,
        coalesce(r.signal_group, 'unclassified') as signal_group,
        count(*)                               as n_cases
    from {table('stg_311_requests')} as r
    left join {table('stg_neighborhoods')} as n
        on st_contains(n.geom, r.point)
    where r.is_food_safety
    group by neighborhood, theme, signal_group
    """


def food_safety_311_summary() -> str:
    return f"""
    select
        count(*)                   as n_cases,
        countif(is_food_safety)    as n_food_safety,
        countif(is_food_safety and point is null) as n_food_safety_no_location,
        -- signal_group comes from the seed: a complaint about an establishment vs nearby conditions
        countif(is_food_safety and signal_group = 'direct_food_safety')  as n_direct,
        countif(is_food_safety and signal_group = 'environment_context') as n_context,
        min(opened_at)             as first_opened,
        max(opened_at)             as last_opened,
        max(_load_date)            as last_load_date
    from {table('stg_311_requests')}
    """


def data_status(include_inspections: bool = True) -> str:
    """One row per source: row count, latest load date and the dates the data covers."""
    parts = []
    if include_inspections:
        parts.append(f"""
        select 'Food inspections' as source, 'stg_food_inspections' as view_name, count(*) as n_rows,
               cast(max(_load_date) as date) as latest_load,
               min(inspection_date) as first_date, max(inspection_date) as last_date
        from {table('stg_food_inspections')}""")
    parts.append(f"""
        select '311 service requests' as source, 'stg_311_requests' as view_name, count(*) as n_rows,
               cast(max(_load_date) as date) as latest_load,
               min(date(opened_at)) as first_date, max(date(opened_at)) as last_date
        from {table('stg_311_requests')}""")
    parts.append(f"""
        select 'Active food licenses' as source, 'stg_food_licenses' as view_name, count(*) as n_rows,
               cast(max(_load_date) as date) as latest_load,
               min(date(license_added_at)) as first_date, max(date(license_added_at)) as last_date
        from {table('stg_food_licenses')}""")
    parts.append(f"""
        select 'Neighborhood boundaries' as source, 'stg_neighborhoods' as view_name, count(*) as n_rows,
               cast(null as date) as latest_load, cast(null as date) as first_date, cast(null as date) as last_date
        from {table('stg_neighborhoods')}""")
    return "\n        union all".join(parts)


def built_tables() -> str:
    """When each dbt-built intermediate table was last rebuilt (they're tables, not views, so they
    don't pick up new loads until dbt runs)."""
    project, dataset = int_table("x").strip("`").rsplit(".", 2)[:2]
    return f"""
    select
        table_id                                   as table_name,
        row_count                                  as n_rows,
        timestamp_millis(last_modified_time)       as built_at
    from `{project}.{dataset}.__TABLES__`
    where table_id like 'int\\\\_%'
    order by table_id
    """
