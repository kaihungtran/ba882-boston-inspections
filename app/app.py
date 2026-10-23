"""Boston food inspections dashboard. Run from the repo root: streamlit run app/app.py"""

import config
import streamlit as st

st.set_page_config(page_title="Boston Food Inspections", page_icon="🍽️", layout="wide")

try:
    project, dataset = config.project_id(), config.staging_dataset()
except config.ConfigError as err:
    st.error(str(err))
    st.stop()

pages = [
    st.Page("views/trends.py", title="Pass/fail trends", icon="📈", default=True),
    st.Page("views/neighborhoods.py", title="Results by neighborhood", icon="🗺️"),
    st.Page("views/violations.py", title="Top violations", icon="📋"),
    st.Page("views/complaints_311.py", title="Food-safety 311", icon="📞"),
]

with st.sidebar:
    st.caption(f"BigQuery: `{project}.{dataset}`")
    if config.use_stub_inspections():
        st.caption("Inspections: **stub data** (`USE_STUB_INSPECTIONS=true`)")
    if st.button("Clear cache", help="Re-run BigQuery queries on the next page load"):
        st.cache_data.clear()

st.navigation(pages).run()
