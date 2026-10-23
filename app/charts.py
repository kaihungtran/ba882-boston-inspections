"""Shared chart pieces: palette, stub banner, Altair charts and the neighborhood choropleth."""

import json

import altair as alt
import config
import pandas as pd
import pydeck as pdk
import streamlit as st

# Validated categorical order (dataviz reference palette). Assign in this order, never cycle.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# Status colors are reserved for pass/fail and always paired with a text label.
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
# Single-hue blue ramp for magnitude (light -> dark).
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
NO_DATA = "#e1e0d9"

# 311 food-safety themes from seeds/food_safety_311_categories.csv, in a fixed color order.
THEMES = ["pests", "sanitation", "hygiene", "food_alert", "trash", "facilities", "other"]


def stub_banner() -> None:
    if config.use_stub_inspections():
        st.warning(
            "**STUB DATA.** These inspection numbers are randomly generated, not real. "
            "`raw.food_inspections` isn't in BigQuery yet. Set `USE_STUB_INSPECTIONS=false` "
            "in `.env` once `stg_food_inspections` is built.",
            icon="⚠️",
        )


def _hover_line(df: pd.DataFrame, x: str, y: str, y_title: str, y_format: str, color: str) -> alt.Chart:
    """Single-series line with a crosshair + tooltip on the nearest point."""
    nearest = alt.selection_point(nearest=True, on="pointerover", fields=[x], empty=False)
    base = alt.Chart(df).encode(x=alt.X(f"{x}:T", title=None))
    line = base.mark_line(strokeWidth=2, color=color).encode(
        y=alt.Y(f"{y}:Q", title=y_title, axis=alt.Axis(format=y_format))
    )
    points = base.mark_point(size=70, filled=True, color=color).encode(
        y=f"{y}:Q", opacity=alt.condition(nearest, alt.value(1), alt.value(0))
    )
    rule = base.mark_rule(color="#898781", strokeWidth=1).encode(
        opacity=alt.condition(nearest, alt.value(0.6), alt.value(0)),
        tooltip=[alt.Tooltip(f"{x}:T", title="Month", format="%b %Y"),
                 alt.Tooltip(f"{y}:Q", title=y_title, format=y_format)],
    ).add_params(nearest)
    return (line + points + rule).properties(height=280)


def rate_line(df: pd.DataFrame, x: str, y: str, y_title: str) -> alt.Chart:
    return _hover_line(df, x, y, y_title, ".0%", CATEGORICAL[0])


def count_line(df: pd.DataFrame, x: str, y: str, y_title: str) -> alt.Chart:
    return _hover_line(df, x, y, y_title, ",.0f", CATEGORICAL[0])


def stacked_bars(df: pd.DataFrame, x: str, y: str, color: str, domain: list, colors: list,
                 y_title: str, color_title: str) -> alt.Chart:
    # Month labels are built here, not in Vega: Vega reads dates as UTC midnight and shifts
    # them into the viewer's time zone, which can move a bar into the previous month.
    df = df.assign(month_label=pd.to_datetime(df[x]).dt.strftime("%b %Y"))
    month_order = df.sort_values(x)["month_label"].unique().tolist()
    return (
        alt.Chart(df)
        .mark_bar(stroke="#fcfcfb", strokeWidth=1)
        .encode(
            x=alt.X("month_label:O", title=None, sort=month_order,
                    axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
            y=alt.Y(f"sum({y}):Q", title=y_title),
            color=alt.Color(f"{color}:N", title=color_title,
                            scale=alt.Scale(domain=domain, range=colors),
                            legend=alt.Legend(orient="top")),
            order=alt.Order(f"{color}_order:Q"),
            tooltip=[alt.Tooltip("month_label:N", title="Month"),
                     alt.Tooltip(f"{color}:N", title=color_title),
                     alt.Tooltip(f"sum({y}):Q", title=y_title, format=",")],
        )
        .transform_calculate(**{f"{color}_order": f"indexof({json.dumps(domain)}, datum.{color})"})
        .properties(height=300)
    )


def _bin_colors(values: pd.Series, steps: list) -> pd.Series:
    """Quantile-bin values onto a sequential ramp; returns the hex step per row."""
    valid = values.dropna()
    if valid.empty or valid.nunique() == 1:
        return values.map(lambda v: steps[len(steps) // 2] if pd.notna(v) else NO_DATA)
    bins = pd.qcut(valid.rank(method="first"), q=min(len(steps), len(valid)), labels=False)
    return values.index.to_series().map(
        lambda i: steps[int(bins[i] * (len(steps) - 1) / max(bins.max(), 1))] if i in bins.index else NO_DATA
    )


def _hex_to_rgba(hex_color: str, alpha: int = 210) -> list:
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [alpha]


def choropleth(shapes: pd.DataFrame, values: pd.DataFrame, value_col: str, label_fn) -> None:
    """Neighborhood map. `shapes` has neighborhood + geojson; `values` has neighborhood + value_col.
    label_fn(row) -> tooltip text for one neighborhood."""
    merged = shapes.merge(values, on="neighborhood", how="left")
    merged["fill"] = _bin_colors(merged[value_col], SEQUENTIAL[1:])
    features = []
    for _, row in merged.iterrows():
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geojson"]),
            "properties": {
                "neighborhood": row["neighborhood"],
                "label": label_fn(row) if pd.notna(row[value_col]) else "No data",
                "fill": _hex_to_rgba(row["fill"]),
            },
        })
    layer = pdk.Layer(
        "GeoJsonLayer",
        {"type": "FeatureCollection", "features": features},
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill",
        get_line_color=[252, 252, 251],
        line_width_min_pixels=1,
        auto_highlight=True,
        highlight_color=[11, 11, 11, 60],
    )
    view = pdk.ViewState(latitude=42.32, longitude=-71.08, zoom=10.6)
    st.pydeck_chart(
        pdk.Deck(layers=[layer], initial_view_state=view, map_provider="carto", map_style="light",
                 tooltip={"html": "<b>{neighborhood}</b><br/>{label}"}),
        height=520,
    )
    _sequential_legend(merged[value_col])


def _sequential_legend(values: pd.Series) -> None:
    valid = values.dropna()
    if valid.empty:
        return
    swatches = "".join(
        f'<span style="display:inline-block;width:28px;height:10px;background:{c}"></span>'
        for c in SEQUENTIAL[1:]
    )
    st.markdown(
        f'<div style="font-size:0.8rem;color:#898781;display:flex;align-items:center;gap:8px">'
        f"<span>Lower</span><span>{swatches}</span><span>Higher</span>"
        f'<span style="margin-left:12px;display:inline-block;width:14px;height:10px;background:{NO_DATA}"></span>'
        f"<span>No data</span></div>",
        unsafe_allow_html=True,
    )
