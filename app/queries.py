"""All SQL used by the app. Table names come from .env via config.table().

stg_food_inspections is one row per violation, so inspection-level queries first roll up to
one row per license_number + inspection_date (the same key the planned fct_inspections uses).
Swap these to the marts once fct_inspections / dim_neighborhood exist.
"""

from config import table


def _inspections_cte() -> str:
    return f"""
    inspections as (
        select
            license_number,
            inspection_date,
            any_value(license_category)   as license_category,
            logical_or(result_fail)       as failed,
            countif(violation_level is not null) as n_violations,
            any_value(latitude)           as latitude,
            any_value(longitude)          as longitude,
            any_value(city)               as city
        from {table('stg_food_inspections')}
        group by license_number, inspection_date
    )"""


def inspections_monthly() -> str:
    return f"""
    with {_inspections_cte()}
    select
        date_trunc(inspection_date, month) as month,
        coalesce(license_category, 'Unknown') as license_category,
        count(*)       as n_inspections,
        countif(failed) as n_failed
    from inspections
    group by month, license_category
    order by month
    """


def inspections_by_neighborhood() -> str:
    return f"""
    -- Point-in-polygon first; where coordinates are missing (~13%), fall back to the city field.
    with {_inspections_cte()}
    select
        coalesce(by_point.neighborhood, by_city.neighborhood, 'Unmatched') as neighborhood,
        extract(year from i.inspection_date) as year,
        count(*)                              as n_inspections,
        countif(i.failed)                     as n_failed,
        count(distinct i.license_number)      as n_establishments
    from inspections as i
    left join {table('stg_neighborhoods')} as by_point
        on st_contains(by_point.geom, st_geogpoint(i.longitude, i.latitude))
    left join {table('stg_neighborhoods')} as by_city
        on upper(by_city.neighborhood) = i.city
    group by neighborhood, year
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
        source_system,
        count(*)                              as n_cases
    from {table('stg_311_requests')}
    where is_food_safety
      and opened_at is not null
    group by month, theme, source_system
    order by month
    """


def food_safety_311_by_neighborhood() -> str:
    return f"""
    select
        coalesce(n.neighborhood, 'Unmatched')  as neighborhood,
        coalesce(r.food_safety_theme, 'other') as theme,
        count(*)                               as n_cases
    from {table('stg_311_requests')} as r
    left join {table('stg_neighborhoods')} as n
        on st_contains(n.geom, r.point)
    where r.is_food_safety
    group by neighborhood, theme
    """


def food_safety_311_summary() -> str:
    return f"""
    select
        count(*)                   as n_cases,
        countif(is_food_safety)    as n_food_safety,
        countif(is_food_safety and point is null) as n_food_safety_no_location,
        min(opened_at)             as first_opened,
        max(opened_at)             as last_opened,
        max(_load_date)            as last_load_date
    from {table('stg_311_requests')}
    """
