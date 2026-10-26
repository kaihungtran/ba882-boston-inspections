"""Boston food inspections dashboard. Run from the repo root: streamlit run app/app.py"""

import config
import streamlit as st
import ui

st.set_page_config(page_title="Boston Food Inspections", page_icon=":material/restaurant:", layout="wide")
ui.inject_css()

try:
    project, dataset = config.project_id(), config.staging_dataset()
except config.ConfigError as err:
    st.error(str(err))
    st.stop()

pages = [
    st.Page("views/trends.py", title="Pass/fail trends", default=True),
    st.Page("views/neighborhoods.py", title="Results by neighborhood"),
    st.Page("views/violations.py", title="Top violations"),
    st.Page("views/complaints_311.py", title="Food-safety 311"),
]
# Navigation is drawn by hand so the brand block sits above the page links.
nav = st.navigation(pages, position="hidden")

with st.sidebar:
    ui.sidebar_brand()
    for page in pages:
        st.page_link(page)
    ui.sidebar_colophon(project, dataset)
    if st.button("Clear cache", help="Re-run BigQuery queries on the next page load"):
        st.cache_data.clear()

nav.run()
