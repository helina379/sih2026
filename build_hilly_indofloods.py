"""
Build a hilly-region subset of INDOFLOODS for the Flash Flood Prediction project (SIH26192).

What it does:
1. Downloads the 4 INDOFLOODS CSVs from Zenodo (record 14584655).
2. Filters gauge stations (metadata) to hilly/Himalayan regions:
   - Himachal Pradesh, Uttarakhand (core Himalaya)
   - West Bengal gauges on Teesta / Torsa / Jaldhaka / Raidak / Sankosh
     (sub-Himalayan Dooars foothill rivers, still hill-fed flash-flood-prone)
   You can edit HILL_STATES / HILL_RIVER_KEYWORDS below to widen/narrow this.
3. Joins flood events + catchment characteristics + precipitation variables
   onto that filtered gauge list (all keyed on GaugeID).
4. Writes one combined CSV: hilly_indofloods_combined.csv

Run:
    pip install pandas requests --break-system-packages   # if not already installed
    python build_hilly_indofloods.py

Output columns include: everything from metadata (lat/lon, river, state,
catchment area) + flood event fields (Flood Type is your classification
target) + catchment characteristics (geomorphology/climate/land cover/soil/
lithology) + precipitation variables. One row per flood event.
"""

import pandas as pd
import requests
from io import StringIO

BASE = "https://zenodo.org/records/14584655/files"
FILES = {
    "metadata": f"{BASE}/metadata_indofloods.csv?download=1",
    "floodevents": f"{BASE}/floodevents_indofloods.csv?download=1",
    "catchment": f"{BASE}/catchment_characteristics_indofloods.csv?download=1",
    "precipitation": f"{BASE}/precipitation_variables_indofloods.csv?download=1",
}

HILL_STATES = {
    "Himachal Pradesh", "Uttarakhand",
    # Northeast India hill states/UTs -- genuinely hilly, flash-flood-prone
    # terrain, added to widen station diversity beyond the original ~15-20
    # HP/Uttarakhand/Dooars gauges (see chat: small-sample generalization issue)
    "Assam", "Arunachal Pradesh", "Sikkim", "Meghalaya",
    "Manipur", "Mizoram", "Tripura", "Nagaland",
}
HILL_RIVER_KEYWORDS = ["Teesta", "Torsa", "Jaldhaka", "Raidak", "Sankosh"]


def fetch_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    df.columns = [c.strip() for c in df.columns]  # guard against stray whitespace in headers
    return df


def gauge_id_from_event_id(series: pd.Series) -> pd.Series:
    # EventID format: INDOFLOODS-gauge-118-10  ->  GaugeID: INDOFLOODS-gauge-118
    return series.str.rsplit("-", n=1).str[0]


def main():
    print("Downloading metadata...")
    meta = fetch_csv(FILES["metadata"])
    print("metadata columns:", list(meta.columns))

    is_hill_state = meta["State"].isin(HILL_STATES)
    is_hill_river = meta["River Name/ Tributory/ SubTributory"].fillna("").apply(
        lambda s: any(k in s for k in HILL_RIVER_KEYWORDS)
    )
    hilly_meta = meta[is_hill_state | is_hill_river].copy()
    print(f"Hilly-region gauges selected: {len(hilly_meta)}")
    print(hilly_meta[["GaugeID", "Station", "State", "River Name/ Tributory/ SubTributory"]])

    hill_ids = set(hilly_meta["GaugeID"])

    print("Downloading flood events...")
    events = fetch_csv(FILES["floodevents"])
    print("floodevents columns:", list(events.columns))
    if "GaugeID" not in events.columns:
        events["GaugeID"] = gauge_id_from_event_id(events["EventID"])
    events_hilly = events[events["GaugeID"].isin(hill_ids)].copy()
    print(f"Flood events in hilly gauges: {len(events_hilly)}")

    print("Downloading catchment characteristics...")
    catchment = fetch_csv(FILES["catchment"])
    print("catchment columns:", list(catchment.columns))
    if "GaugeID" not in catchment.columns:
        # fall back: find any column containing 'gauge' (case-insensitive)
        gcol = next((c for c in catchment.columns if "gauge" in c.lower()), None)
        if gcol:
            catchment = catchment.rename(columns={gcol: "GaugeID"})
    catchment_hilly = catchment[catchment["GaugeID"].isin(hill_ids)] if "GaugeID" in catchment.columns else catchment

    print("Downloading precipitation variables...")
    precip = fetch_csv(FILES["precipitation"])
    print("precipitation columns:", list(precip.columns))

    # Join: events (one row per flood) -> station metadata -> catchment chars
    combined = events_hilly.merge(hilly_meta, on="GaugeID", how="left")
    combined = combined.merge(catchment_hilly, on="GaugeID", how="left", suffixes=("", "_catchment"))

    # Precipitation is event-scale: key on EventID if present, else fall back to GaugeID
    if "EventID" in precip.columns:
        combined = combined.merge(precip, on="EventID", how="left", suffixes=("", "_precip"))
    elif "GaugeID" in precip.columns:
        precip_hilly = precip[precip["GaugeID"].isin(hill_ids)]
        combined = combined.merge(precip_hilly, on="GaugeID", how="left", suffixes=("", "_precip"))
    else:
        print("WARNING: could not find EventID or GaugeID in precipitation file — skipping that join.")
        print("Inspect the printed 'precipitation columns' above and merge it in manually if needed.")

    out_path = "hilly_indofloods_combined.csv"
    combined.to_csv(out_path, index=False)
    print(f"\nWrote {out_path}: {combined.shape[0]} rows x {combined.shape[1]} columns")
    print("Target column for classification: 'Flood Type' (Flood / Severe Flood)")


if __name__ == "__main__":
    main()
