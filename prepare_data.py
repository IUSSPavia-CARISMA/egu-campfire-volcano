#!/usr/bin/env python3
"""
Volcano Campfire — Data Preparation Script
==========================================
Fetches the Smithsonian GVP Holocene volcano list via their WFS GeoServer,
flags currently erupting volcanoes by scraping the GVP current eruptions page,
and writes a clean volcanoes.json for use by index.html.

Usage
-----
    pip install requests beautifulsoup4 lxml
    python prepare_data.py

Output
------
    volcanoes.json  — place next to index.html in your GitHub repo

Data sources
------------
    Volcanoes : Smithsonian GVP VOTW v5.x (volcano.si.edu)
    Eruptions : Smithsonian / USGS Weekly Volcanic Activity Report
                (volcano.si.edu/gvp_currenteruptions.cfm)
"""

import json
import re
import sys
import requests
from bs4 import BeautifulSoup

# ── Endpoints ─────────────────────────────────────────────────────────────────

WFS_URL = (
    "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows"
    "?service=WFS"
    "&version=2.0.0"
    "&request=GetFeature"
    "&typeName=GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes"
    "&outputFormat=application%2Fjson"
)

CURRENT_ERUPTIONS_URL = "https://volcano.si.edu/gvp_currenteruptions.cfm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ── Activity evidence → display status ───────────────────────────────────────
# GVP Activity Evidence field values mapped to simplified status labels
EVIDENCE_TO_STATUS = {
    "Historical":       "active",        # erupted in written historical record
    "Holocene":         "active",        # erupted in Holocene, no historical record
    "Anthropology":     "active",        # inferred from human artefacts / oral history
    "Radiocarbon":      "active",        # dated by 14C
    "Tephrochronology": "active",        # dated by tephra stratigraphy
    "Varve Count":      "active",
    "Ice Core":         "active",
    "Dendrochronology": "active",
    "Hydrothermal":     "hydrothermal",  # hot springs / geothermal, no confirmed eruption
    "Fumarolic":        "fumarolic",     # fumaroles only
    "Uncertain":        "uncertain",
}


# ── Step 1: fetch volcano list ────────────────────────────────────────────────

def fetch_volcanoes() -> list[dict]:
    """Download all Holocene volcanoes from the GVP WFS GeoServer endpoint."""
    print("Fetching volcano list from GVP WFS GeoServer…")
    try:
        r = requests.get(WFS_URL, headers=HEADERS, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"WFS request failed: {e}") from e

    data = r.json()
    features = data.get("features", [])
    if not features:
        raise RuntimeError("GeoJSON response contained no features.")

    volcanoes = []
    skipped = 0
    for f in features:
        p = f.get("properties", {})
        geom = f.get("geometry")

        # Skip entries with no coordinates (a small number in GVP data)
        if not geom or not geom.get("coordinates"):
            skipped += 1
            continue

        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        evidence = p.get("Activity_Evidence", "Uncertain")

        volcanoes.append({
            "id":            str(p.get("Volcano_Number", "")),
            "name":          p.get("Volcano_Name", "Unknown"),
            "country":       p.get("Country", ""),
            "type":          p.get("Primary_Volcano_Type", ""),
            "evidence":      evidence,
            "last_eruption": p.get("Last_Known_Eruption", "Unknown"),
            "region":        p.get("Region", ""),
            "subregion":     p.get("Subregion", ""),
            "elevation":     p.get("Elevation_m"),
            "lat":           round(float(lat), 5),
            "lon":           round(float(lon), 5),
            "status":        EVIDENCE_TO_STATUS.get(evidence, "uncertain"),
            "erupting":      False,   # will be updated in step 2
        })

    print(f"  → {len(volcanoes)} volcanoes loaded  ({skipped} skipped: no coordinates).")
    return volcanoes


# ── Step 2: fetch current eruptions ──────────────────────────────────────────

def fetch_erupting_ids() -> set[str]:
    """
    Scrape the GVP Current Eruptions page and return a set of 6-digit
    volcano numbers for volcanoes with confirmed ongoing activity.
    """
    print("Fetching current eruptions from GVP…")

    # Use a session to maintain cookies
    session = requests.Session()

    # Enhanced headers for this specific request
    eruption_headers = HEADERS.copy()
    eruption_headers["Referer"] = "https://volcano.si.edu/"
    eruption_headers["Sec-Fetch-Dest"] = "document"
    eruption_headers["Sec-Fetch-Mode"] = "navigate"
    eruption_headers["Sec-Fetch-Site"] = "same-origin"

    try:
        # First visit the main page to get cookies
        session.get("https://volcano.si.edu/", headers=HEADERS, timeout=30)

        # Add a small delay to look more human-like
        import time
        time.sleep(1)

        # Now request the eruptions page
        r = session.get(CURRENT_ERUPTIONS_URL, headers=eruption_headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Current eruptions request failed: {e}") from e

    soup = BeautifulSoup(r.text, "lxml")
    ids: set[str] = set()

    # GVP volcano links contain ?vnum=XXXXXX or volcano_no=XXXXXX
    for a in soup.find_all("a", href=True):
        m = re.search(r"(?:vnum|volcano_no)=(\d{6})", a["href"])
        if m:
            ids.add(m.group(1))

    # Also parse any plain-text 6-digit volcano numbers in table cells
    for td in soup.find_all("td"):
        m = re.fullmatch(r"\s*(\d{6})\s*", td.get_text())
        if m:
            ids.add(m.group(1))

    print(f"  → {len(ids)} currently erupting volcanoes identified.")
    return ids


# ── Step 3: merge and write ───────────────────────────────────────────────────

def main() -> None:
    # Fetch volcano list (required)
    try:
        volcanoes = fetch_volcanoes()
    except RuntimeError as e:
        print(f"\nFATAL: {e}")
        sys.exit(1)

    # Fetch current eruptions (optional — app still works without it)
    try:
        erupting_ids = fetch_erupting_ids()
        for v in volcanoes:
            if v["id"] in erupting_ids:
                v["status"] = "erupting"
                v["erupting"] = True
        n = sum(1 for v in volcanoes if v["erupting"])
        print(f"  → {n} volcanoes flagged as currently erupting.")
    except RuntimeError as e:
        print(f"\nWARNING: {e}")
        print("         Continuing without real-time eruption status.\n")

    # Write JSON (minified — reduces file size by ~30%)
    out_path = "volcanoes.json"
    payload = json.dumps(volcanoes, ensure_ascii=False, separators=(",", ":"))
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(payload)

    size_kb = len(payload.encode("utf-8")) / 1024
    n_erupting = sum(1 for v in volcanoes if v["erupting"])
    n_active    = sum(1 for v in volcanoes if v["status"] == "active")

    print(f"\n✓ Saved {out_path}")
    print(f"  Total volcanoes : {len(volcanoes)}")
    print(f"  Currently erupting : {n_erupting}")
    print(f"  Historically active : {n_active}")
    print(f"  File size : {size_kb:.0f} KB")
    print("\nNext step: copy volcanoes.json into your GitHub repo next to index.html.")


if __name__ == "__main__":
    main()
