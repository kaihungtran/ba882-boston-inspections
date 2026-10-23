"""STUB inspection data. Fake, randomly generated rows for building the UI before
raw.food_inspections lands in BigQuery. Controlled by USE_STUB_INSPECTIONS in .env.

make_inspections() returns rows shaped like stg_food_inspections on origin/dbt/11-staging-models
(one row per violation; an inspection with no violations keeps one row with NULL violation fields).
The aggregate functions mirror the SQL in queries.py so the pages don't care which source is used.
"""

import numpy as np
import pandas as pd

SEED = 882

# Names match stg_neighborhoods; lat/lon are rough centroids from the neighborhoods seed.
NEIGHBORHOODS = {
    "Allston": (42.3633, -71.1215, 5), "Back Bay": (42.3526, -71.0820, 9),
    "Bay Village": (42.3493, -71.0690, 1), "Beacon Hill": (42.3579, -71.0710, 3),
    "Brighton": (42.3604, -71.1518, 6), "Charlestown": (42.3811, -71.0603, 3),
    "Chinatown": (42.3494, -71.0608, 6), "Dorchester": (42.2934, -71.0494, 10),
    "Downtown": (42.3525, -71.0581, 12), "East Boston": (42.3794, -71.0198, 7),
    "Fenway": (42.3497, -71.0994, 6), "Harbor Islands": (42.3291, -70.9569, 0.2),
    "Hyde Park": (42.2616, -71.1211, 3), "Jamaica Plain": (42.3045, -71.1123, 5),
    "Leather District": (42.3511, -71.0583, 1), "Longwood": (42.3386, -71.1056, 2),
    "Mattapan": (42.2747, -71.0931, 3), "Mission Hill": (42.3305, -71.1037, 2),
    "North End": (42.3665, -71.0535, 5), "Roslindale": (42.2841, -71.1284, 3),
    "Roxbury": (42.3163, -71.0893, 5), "South Boston": (42.3349, -71.0294, 6),
    "South Boston Waterfront": (42.3472, -71.0385, 4), "South End": (42.3420, -71.0754, 6),
    "West End": (42.3664, -71.0661, 2), "West Roxbury": (42.2804, -71.1447, 3),
}

LICENSE_CATEGORIES = {
    "FS": ("Eating & Drinking", 0.55),
    "FT": ("Eating & Drinking w/ Take Out", 0.30),
    "RF": ("Retail Food", 0.10),
    "MFW": ("Mobile Food Walk On", 0.05),
}

# (code, description, level, weight)
VIOLATIONS = [
    ("6-501.111-C", "Insects Rodents Animals", "***", 8),
    ("3-501.16-P", "PHF's Properly Thawed", "***", 5),
    ("3-501.16-P", "Cold Holding", "***", 7),
    ("3-501.16-P", "Hot Holding", "***", 4),
    ("2-301.12-P", "Hand Cleaning Procedure", "***", 3),
    ("4-601.11-PF", "Food Contact Surfaces Clean", "**", 9),
    ("4-302.12-PF", "Thermometers Provided & Accurate", "**", 5),
    ("2-102.12-C", "Certified Food Protection Manager", "**", 4),
    ("3-305.11-C", "Food Protection", "*", 7),
    ("6-501.12-C", "Non-Food Contact Surfaces Clean", "*", 12),
    ("6-201.11-C", "Floors Walls Ceilings Clean", "*", 11),
    ("2-402.11-C", "Clean Cloths Hair Restraint", "*", 6),
    ("5-205.15-C", "Plumbing Maintained", "*", 5),
    ("6-501.114-C", "Premises Maintained", "*", 5),
    ("M-1001", "Inadequate Lighting", "*", 2),
]

START = pd.Timestamp("2022-01-01")
END = pd.Timestamp("2026-10-15")


def make_inspections() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    hood_names = list(NEIGHBORHOODS)
    hood_w = np.array([v[2] for v in NEIGHBORHOODS.values()], dtype=float)
    cats = list(LICENSE_CATEGORIES)
    cat_w = np.array([v[1] for v in LICENSE_CATEGORIES.values()])
    viol_w = np.array([v[3] for v in VIOLATIONS], dtype=float)
    days = (END - START).days

    rows = []
    row_id = 100_000
    for i in range(1500):
        hood = hood_names[rng.choice(len(hood_names), p=hood_w / hood_w.sum())]
        lat0, lon0, _ = NEIGHBORHOODS[hood]
        has_coords = rng.random() > 0.13  # ~13% of real establishments have no coordinates
        cat = cats[rng.choice(len(cats), p=cat_w)]
        establishment = {
            "license_number": f"{rng.integers(10_000, 99_999)}{i:04d}",
            "business_name": f"Stub Eatery {i:04d}",
            "license_category": cat,
            "license_description": LICENSE_CATEGORIES[cat][0],
            "license_status": "Active" if rng.random() > 0.2 else "Inactive",
            "license_issued_at": START - pd.Timedelta(days=int(rng.integers(0, 3650))),
            "address": f"{rng.integers(1, 999)} Stub St",
            "city": hood.upper(),
            "state": "MA",
            "zip": f"021{rng.integers(0, 99):02d}",
            "property_id": str(rng.integers(100_000, 999_999)),
            "latitude": lat0 + rng.normal(0, 0.003) if has_coords else np.nan,
            "longitude": lon0 + rng.normal(0, 0.003) if has_coords else np.nan,
        }
        establishment["license_expires_at"] = END + pd.Timedelta(days=int(rng.integers(30, 365)))
        risk = rng.beta(2, 4)  # per-establishment baseline failure risk

        day = int(rng.integers(0, 180))
        while day < days:
            inspected_at = START + pd.Timedelta(days=day, hours=int(rng.integers(8, 17)))
            summer = 0.08 if inspected_at.month in (6, 7, 8) else 0.0
            failed = rng.random() < min(risk + summer, 0.95)
            result = rng.choice(["HE_Fail", "HE_FailExt"]) if failed else rng.choice(["HE_Pass", "HE_Filed"], p=[0.8, 0.2])
            n_viol = rng.poisson(3.0 if failed else 0.8)
            picks = rng.choice(len(VIOLATIONS), size=n_viol, p=viol_w / viol_w.sum()) if n_viol else [None]
            for p in picks:
                row_id += 1
                base = {
                    **establishment,
                    "source_row_id": row_id,
                    "result_code": result,
                    "result_fail": "fail" in result.lower(),
                    "inspected_at": inspected_at,
                    "inspection_date": inspected_at.date(),
                }
                if p is None:
                    base.update(violation_code=None, violation_code_system=None, fda_severity=None,
                                violation_level=None, violation_description=None, violation_at=None,
                                violation_status=None, inspector_comments=None)
                else:
                    code, desc, level, _ = VIOLATIONS[p]
                    base.update(
                        violation_code=code,
                        violation_code_system="fda",
                        fda_severity="M" if code.startswith("M-") else code.rsplit("-", 1)[-1],
                        violation_level=level,
                        violation_description=desc,
                        violation_at=inspected_at,
                        violation_status="Fail" if failed else rng.choice(["Pass", "Fail"]),
                        inspector_comments="STUB comment.",
                    )
                rows.append(base)
            day += int(rng.integers(120, 300))

    df = pd.DataFrame(rows)
    df["_load_date"] = END.date()
    return df


def _inspection_level(df: pd.DataFrame) -> pd.DataFrame:
    """Mirror of the inspections CTE in queries.py."""
    return (
        df.groupby(["license_number", "inspection_date"], as_index=False)
        .agg(license_category=("license_category", "first"),
             failed=("result_fail", "any"),
             city=("city", "first"))
    )


def inspections_monthly(df: pd.DataFrame) -> pd.DataFrame:
    insp = _inspection_level(df)
    insp["month"] = pd.to_datetime(insp["inspection_date"]).dt.to_period("M").dt.to_timestamp()
    return (
        insp.groupby(["month", "license_category"], as_index=False)
        .agg(n_inspections=("failed", "size"), n_failed=("failed", "sum"))
        .sort_values("month")
    )


def inspections_by_neighborhood(df: pd.DataFrame) -> pd.DataFrame:
    insp = _inspection_level(df)
    by_upper = {name.upper(): name for name in NEIGHBORHOODS}
    insp["neighborhood"] = insp["city"].map(by_upper).fillna("Unmatched")
    insp["year"] = pd.to_datetime(insp["inspection_date"]).dt.year
    return insp.groupby(["neighborhood", "year"], as_index=False).agg(
        n_inspections=("failed", "size"),
        n_failed=("failed", "sum"),
        n_establishments=("license_number", "nunique"),
    )


def violations_by_type(df: pd.DataFrame) -> pd.DataFrame:
    v = df[df["violation_level"].notna() & df["violation_description"].notna()].copy()
    v["year"] = pd.to_datetime(v["inspection_date"]).dt.year
    return (
        v.groupby(["violation_description", "violation_level", "year"], as_index=False)
        .size()
        .rename(columns={"size": "n_violations"})
    )
