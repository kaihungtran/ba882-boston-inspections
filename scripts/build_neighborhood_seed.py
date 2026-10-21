"""Build dbt/seeds/neighborhoods.csv from the city's neighborhood boundaries GeoJSON.

Run once (and again only if the city changes the boundaries), then commit the CSV:

    python3 scripts/build_neighborhood_seed.py

Source: data.boston.gov resource e5849875-a6f6-4c9c-9d8a-5048b0fbd03e (26 neighborhoods,
WGS84 lon/lat). Each shape is stored as a GeoJSON string; stg_neighborhoods turns it into a
GEOGRAPHY with st_geogfromgeojson(..., make_valid => true).

Coordinates are rounded to 5 decimals (about 1 m) and repeated points dropped, which keeps every
shape small enough for dbt's CSV reader.
"""

import csv
import json
import sys
import urllib.request
from pathlib import Path

RESOURCE_ID = "e5849875-a6f6-4c9c-9d8a-5048b0fbd03e"
CKAN = "https://data.boston.gov/api/3/action/resource_show?id="
OUT = Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "neighborhoods.csv"
MAX_FIELD = 120_000  # stay under Python's default CSV field limit (131,072)


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def clean_ring(ring, decimals):
    out = []
    for lon, lat, *_ in ring:
        pt = [round(lon, decimals), round(lat, decimals)]
        if not out or pt != out[-1]:
            out.append(pt)
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 4 else None


def clean_polygon(rings, decimals):
    cleaned = [r for r in (clean_ring(r, decimals) for r in rings) if r]
    return cleaned or None


def clean_geometry(geom, decimals):
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": clean_polygon(geom["coordinates"], decimals)}
    if geom["type"] == "MultiPolygon":
        polys = [p for p in (clean_polygon(p, decimals) for p in geom["coordinates"]) if p]
        return {"type": "MultiPolygon", "coordinates": polys}
    raise ValueError(f"Unexpected geometry type {geom['type']}")


def main():
    url = fetch_json(CKAN + RESOURCE_ID)["result"]["url"]
    print(f"Downloading {url}")
    features = fetch_json(url)["features"]

    rows = []
    for f in features:
        props = f["properties"]
        for decimals in (5, 4):
            geom = json.dumps(clean_geometry(f["geometry"], decimals), separators=(",", ":"))
            if len(geom) <= MAX_FIELD:
                break
        else:
            sys.exit(f"{props['name']}: shape still {len(geom):,} chars at 4 decimals; needs simplifying")
        rows.append({
            "neighborhood_id": str(props["neighborhood_id"]),
            "neighborhood": props["name"].strip(),
            "acres": props.get("acres"),
            "sqmiles": props.get("sqmiles"),
            "geometry_geojson": geom,
        })

    rows.sort(key=lambda r: int(r["neighborhood_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    biggest = max(rows, key=lambda r: len(r["geometry_geojson"]))
    print(f"Wrote {len(rows)} neighborhoods to {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"Largest shape: {biggest['neighborhood']} ({len(biggest['geometry_geojson']):,} chars)")


if __name__ == "__main__":
    main()
