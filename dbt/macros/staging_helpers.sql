{#
  Shared cleaning helpers for staging models. See docs/staging_columns.md ("Rules for every staging model").
  Every raw column arrives as text, so these all take a text expression.
#}

{# Blank or whitespace-only text becomes NULL; otherwise trimmed. Use for free text we must not rewrite. #}
{% macro clean_text(col) -%}
    nullif(trim({{ col }}), '')
{%- endmacro %}


{# Like clean_text, and also collapses runs of whitespace ("55  COURT ST" -> "55 COURT ST"). #}
{% macro squish(col) -%}
    nullif(regexp_replace(trim({{ col }}), r'\s+', ' '), '')
{%- endmacro %}


{#
  Parse the mixed timestamp formats in the raw feeds. Tries a plain cast first (handles
  "2012-02-27 13:47:59+00" and fractional seconds), then explicit formats. Unparseable -> NULL.
  Values without an offset are read as UTC.
#}
{% macro safe_ts(col) -%}
    coalesce(
        safe_cast(nullif(trim({{ col }}), '') as timestamp),
        safe.parse_timestamp('%Y-%m-%d %H:%M:%E*S%Ez', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%Y-%m-%dT%H:%M:%E*S%Ez', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%Y-%m-%dT%H:%M:%E*S', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%m/%d/%Y %H:%M:%S', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%m/%d/%Y %I:%M:%S %p', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%m/%d/%Y %H:%M', nullif(trim({{ col }}), '')),
        safe.parse_timestamp('%m/%d/%Y', nullif(trim({{ col }}), ''))
    )
{%- endmacro %}


{# True when a point falls inside Boston's bounding box (lat 42.2-42.42, lon -71.2 to -70.95). #}
{% macro in_boston(lat, lon) -%}
    ({{ lat }} between 42.2 and 42.42 and {{ lon }} between -71.2 and -70.95)
{%- endmacro %}


{# City text: upper, trimmed, trailing "/" removed ("MISSION HILL/" -> "MISSION HILL"). #}
{% macro clean_city(col) -%}
    nullif(trim(regexp_replace(upper(trim({{ col }})), r'/+$', '')), '')
{%- endmacro %}
