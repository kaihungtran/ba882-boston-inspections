"""Settings, read from the repo-root .env locally or from Streamlit secrets when deployed
(Community Cloud has no .env). Never hardcode project or dataset names."""

import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

# BigQuery identifiers are interpolated into SQL, so only allow safe characters.
_PROJECT_RE = re.compile(r"^[a-z][a-z0-9\-]{4,61}[a-z0-9]$")
_DATASET_RE = re.compile(r"^[A-Za-z0-9_]{1,1024}$")


class ConfigError(RuntimeError):
    pass


def _setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        try:
            value = st.secrets.get(name)  # deployed: Settings → Secrets
        except Exception:  # noqa: BLE001 - no secrets file locally
            value = None
    return str(value if value is not None else default).strip()


def _require(name: str, pattern: re.Pattern) -> str:
    value = _setting(name)
    if not value:
        raise ConfigError(
            f"{name} is not set. Add it to .env in the repo root (see .env.example), "
            "or to the app's secrets when deployed."
        )
    if not pattern.match(value):
        raise ConfigError(f"{name}={value!r} is not a valid BigQuery identifier.")
    return value


def project_id() -> str:
    return _require("GCP_PROJECT_ID", _PROJECT_RE)


def staging_dataset() -> str:
    return _require("BQ_STAGING_DATASET", _DATASET_RE)


def use_stub_inspections() -> bool:
    return _setting("USE_STUB_INSPECTIONS", "true").lower() in {"1", "true", "yes", "on"}


def table(name: str) -> str:
    """Fully qualified, backtick-quoted staging table, e.g. `proj.dataset.stg_311_requests`."""
    return f"`{project_id()}.{staging_dataset()}.{name}`"
