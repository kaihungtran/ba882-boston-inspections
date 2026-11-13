"""Page furniture: design tokens, global CSS, and the small HTML components the pages share
(page header, stat tiles, notices, section rules, sidebar brand).

The app ships a light and a dark theme (.streamlit/config.toml) and viewers switch in
Settings, so nothing here hardcodes a text or surface color: HTML pieces inherit the page's
text color (currentColor, blended with color-mix), and charts use grays that read on both
surfaces. Only palettes that must flip (chart ramps, the basemap) ask is_dark()."""

import html

import config
import streamlit as st

FONT_BODY = "IBM Plex Sans, system-ui, -apple-system, Segoe UI, sans-serif"
FONT_DISPLAY = "Fraunces, Georgia, Times New Roman, serif"
FONT_MONO = "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace"

AMBER = "#e0a030"
# Chart chrome that is legible on both the light (#f7f5f0) and dark (#171614) surfaces.
CHART_INK = "#8c8a84"
CHART_GRID = "rgba(128, 128, 128, 0.22)"

# Surfaces, mirrored from .streamlit/config.toml.
SURFACE_LIGHT = "#f7f5f0"
SURFACE_DARK = "#171614"


def is_dark() -> bool:
    """Active theme, as Streamlit reports it. Only used where a palette must flip."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001 - older Streamlit or bare mode
        return False


def surface() -> str:
    return SURFACE_DARK if is_dark() else SURFACE_LIGHT


def chart_text() -> str:
    """Stronger-than-chrome chart text (category labels). Falls back gracefully if the
    theme guess is wrong: both values stay readable on either surface."""
    return "#c9c5b9" if is_dark() else "#5c5a55"


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {{
  --display: {FONT_DISPLAY}; --mono: {FONT_MONO}; --amber: {AMBER};
  --ink-55: color-mix(in srgb, currentColor 55%, transparent);
  --ink-75: color-mix(in srgb, currentColor 75%, transparent);
  --rule: color-mix(in srgb, currentColor 22%, transparent);
}}

.block-container {{ max-width: 1120px; padding-top: 2.75rem; padding-bottom: 5rem; }}

/* Page header */
.pg-kicker {{ font-family: var(--mono); font-size: .72rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--ink-55); margin: 0 0 .6rem; }}
.pg-title {{ font-family: var(--display); font-weight: 500; font-size: 2.7rem; line-height: 1.05;
  letter-spacing: -.012em; color: inherit; margin: 0 0 .8rem; font-variation-settings: "opsz" 144; }}
.pg-lede {{ font-size: 1.02rem; line-height: 1.55; color: var(--ink-75); max-width: 64ch; margin: 0 0 1.6rem; }}

/* Notices */
.notice {{ --tone: var(--amber); display: flex; gap: 1rem; align-items: flex-start; border-left: 3px solid var(--tone);
  background: color-mix(in srgb, var(--tone) 13%, transparent); padding: .8rem 1rem; margin: 0 0 1.5rem;
  font-size: .92rem; line-height: 1.5; color: inherit; }}
.notice .tag {{ font-family: var(--mono); font-size: .68rem; font-weight: 600; letter-spacing: .1em;
  text-transform: uppercase; color: color-mix(in srgb, var(--tone) 60%, currentColor); white-space: nowrap; padding-top: .25rem; }}
.notice.stale {{ --tone: #d03b3b; }}
.notice b {{ font-weight: 600; }}
.notice code {{ font-family: var(--mono); font-size: .84em; background: color-mix(in srgb, currentColor 9%, transparent);
  padding: .05em .3em; border-radius: 3px; color: inherit; }}

/* Stat tiles */
.stat-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1.6rem;
  margin: 1.4rem 0 1.2rem; }}
.stat {{ border-top: 1px solid currentColor; padding-top: .65rem; }}
.stat-label {{ font-size: .76rem; letter-spacing: .05em; text-transform: uppercase; color: var(--ink-55); margin-bottom: .3rem; }}
.stat-value {{ font-family: var(--display); font-weight: 500; font-size: 2.3rem; line-height: 1.05; color: inherit;
  font-variation-settings: "opsz" 72; }}
.stat-note {{ font-size: .8rem; color: var(--ink-75); margin-top: .35rem; }}

/* Section heading with menu-card dotted leaders between title and note */
.sec {{ display: flex; align-items: baseline; gap: .75rem; margin: 2.4rem 0 1rem; }}
.sec-title {{ font-family: var(--display); font-weight: 500; font-size: 1.4rem; color: inherit; margin: 0; white-space: nowrap; }}
.sec-leader {{ flex: 1; border-bottom: 2px dotted var(--rule); transform: translateY(-.35em); min-width: 2rem; }}
.sec-note {{ font-size: .8rem; color: var(--ink-55); text-align: right; }}

/* Map legend */
.legend {{ font-size: .78rem; color: var(--ink-55); display: flex; align-items: center; gap: .5rem; margin: .5rem 0 0; }}
.legend i {{ display: inline-block; width: 26px; height: 9px; }}
.legend .gap {{ width: 10px; }}

/* Widgets and captions */
[data-testid="stWidgetLabel"] p {{ font-size: .74rem; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-55); }}
[data-testid="stCaptionContainer"] p {{ font-size: .84rem; }}
[data-testid="stExpander"] summary p {{ font-size: .9rem; }}

/* Sidebar: espresso and brass in both themes (colors mirror [theme.*.sidebar] in config.toml) */
.brand-mark {{ color: #d9a441; margin: .2rem 0 .5rem; }}
.brand-mark svg {{ width: 26px; height: 26px; display: block; }}
.brand {{ font-family: var(--display); font-weight: 500; font-size: 1.45rem; line-height: 1.12; color: #f6efe3; margin: 0 0 .35rem; }}
.brand-sub {{ font-family: var(--mono); font-size: .66rem; letter-spacing: .12em; text-transform: uppercase; color: #d9a441; margin-bottom: 1.4rem; }}
.colophon {{ font-size: .78rem; line-height: 1.6; color: #c9bba8; border-top: 1px solid #4a382d; padding-top: .9rem; margin-top: 1.6rem; }}
.colophon-h {{ font-family: var(--mono); font-size: .64rem; letter-spacing: .12em; text-transform: uppercase; color: #d9a441; margin-bottom: .3rem; }}
.colophon-item {{ margin-bottom: .45rem; }}
.colophon b {{ color: #f6efe3; font-weight: 500; }}
.colophon code {{ font-family: var(--mono); font-size: .7rem; color: #e8d7bd; background: none; padding: 0; overflow-wrap: anywhere; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{ padding: .3rem .5rem; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] p {{ font-size: .95rem; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    # Hidden marker so tests can check which theme the server believes is active.
    st.markdown(f'<span class="theme-probe" data-theme="{"dark" if is_dark() else "light"}" hidden></span>',
                unsafe_allow_html=True)


def _html(markup: str) -> None:
    # One block, no blank lines: Markdown would otherwise split the HTML into paragraphs.
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def page_header(kicker: str, title: str, lede: str | None = None) -> None:
    _html(f"""
        <div>
          <p class="pg-kicker">{html.escape(kicker)}</p>
          <div class="pg-title" role="heading" aria-level="1">{html.escape(title)}</div>
          {f'<p class="pg-lede">{lede}</p>' if lede else ''}
        </div>
    """)


def stat_row(stats: list[tuple[str, str, str | None]]) -> None:
    """stats: (label, value, note) triples. Values are preformatted strings."""
    tiles = "".join(
        f'<div class="stat"><div class="stat-label">{html.escape(label)}</div>'
        f'<div class="stat-value">{html.escape(value)}</div>'
        + (f'<div class="stat-note">{html.escape(note)}</div>' if note else "")
        + "</div>"
        for label, value, note in stats
    )
    _html(f'<div class="stat-row">{tiles}</div>')


def section(title: str, note: str | None = None) -> None:
    _html(f"""
        <div class="sec">
          <div class="sec-title" role="heading" aria-level="2">{html.escape(title)}</div>
          <span class="sec-leader"></span>
          {f'<span class="sec-note">{html.escape(note)}</span>' if note else ''}
        </div>
    """)


def _ago(days: int) -> str:
    return "today" if days <= 0 else "1 day ago" if days == 1 else f"{days} days ago"


def freshness_banner(freshness: dict | None) -> None:
    """Shown above every page when the last load is older than the dbt freshness thresholds."""
    if not freshness or freshness["status"] == "Fresh":
        return
    stale = freshness["status"] == "Stale"
    through = freshness.get("inspections_through")
    # Built as one string: _html() joins lines without spaces.
    message = (
        f"The pipeline last loaded data on <b>{freshness['latest_load']:%b %d, %Y}</b> "
        f"({_ago(freshness['age_days'])}), so nothing since then is included. "
        + (f"Inspections run through {through:%b %d, %Y}. " if through else "")
        + "See the Data freshness page for each source."
    )
    _html(f"""
        <div class="notice{' stale' if stale else ''}">
          <span class="tag">{'Stale data' if stale else 'Data behind'}</span>
          <span>{message}</span>
        </div>
    """)


def stub_notice() -> None:
    if config.use_stub_inspections():
        _html("""
            <div class="notice"><span class="tag">Stub data</span>
            <span>These inspection numbers are randomly generated, not real. <code>raw.food_inspections</code>
            isn't in BigQuery yet. Set <code>USE_STUB_INSPECTIONS=false</code> once
            <code>stg_food_inspections</code> is built.</span></div>
        """)


def sidebar_brand() -> None:
    _html("""
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03C11.34 12.84 13 11.12 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.76 0-5 2.24-5 4z"/></svg>
        </div>
        <div class="brand">Boston<br>Food Inspections</div>
        <div class="brand-sub">Est. 2006 · BA882 Phase 1</div>
    """)


def sidebar_colophon(project: str, dataset: str, freshness: dict | None = None,
                     intermediate: str | None = None) -> None:
    last_load = (
        f'<div class="colophon-item">Last load · <b>{freshness["latest_load"]:%b %d, %Y}</b>'
        f'<br>{_ago(freshness["age_days"])} · {freshness["status"].lower()}</div>'
        if freshness else ""
    )
    source = (
        "<b>stub data</b><br><code>USE_STUB_INSPECTIONS=true</code>"
        if config.use_stub_inspections()
        else "<b>BigQuery</b><br><code>int_inspections</code>"
    )
    datasets = f"<code>{html.escape(project)}.{html.escape(dataset)}</code>"
    if intermediate and intermediate != dataset:
        datasets += f"<br><code>{html.escape(project)}.{html.escape(intermediate)}</code>"
    _html(f"""
        <div class="colophon">
          <div class="colophon-h">Data</div>
          <div class="colophon-item">BigQuery<br>{datasets}</div>
          <div class="colophon-item">Inspections · {source}</div>
          <div class="colophon-item">311 and neighborhoods · <b>BigQuery</b></div>
          {last_load}
          <div class="colophon-item">Query results cached for one hour</div>
          <div class="colophon-item">Light or dark: ⋮ menu → Settings</div>
          <div class="colophon-h" style="margin-top:.9rem">Source</div>
          <div class="colophon-item">City of Boston · data.boston.gov<br>Food inspections, licenses and 311</div>
        </div>
    """)
