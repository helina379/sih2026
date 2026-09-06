"""
Turn the continuous CWC water-level time series (cwc_hilly_water_levels.csv,
274 stations, ~3.79M hourly readings) into discrete FLOOD EVENTS, the same
shape as INDOFLOODS's own event table -- so they can be combined into one
larger, more station-diverse training set.

Threshold source per station (in priority order):
  1. Official INDOFLOODS danger/warning level, where the station could be
     matched by coordinates (see hilly_stations_with_official_thresholds.csv)
     -- highest confidence.
  2. Statistical proxy: 90th percentile of that station's own historical
     water level = "warning", 98th percentile = "danger". Lower confidence,
     but self-consistent per station and a standard bootstrapping approach
     when official reference levels aren't digitized/accessible.

Event detection: a flood event starts when water level crosses the warning
threshold and ends when it drops back below it. Peak level within that
window determines Flood vs Severe Flood (>= danger threshold).

Output: cwc_derived_flood_events.csv -- one row per detected event, with
columns matching INDOFLOODS's own event table as closely as possible
(GaugeID, peak level, start/end date, duration, Flood Type) plus a
threshold_source column ('official' or 'percentile_proxy') so you can filter
by confidence level later, or weight training rows accordingly.

Run:
    pip install pandas numpy --break-system-packages
    python detect_flood_events.py
"""

import pandas as pd
import numpy as np

WATER_LEVELS_CSV = "cwc_hilly_water_levels.csv"
STATIONS_CSV = "hilly_stations_with_official_thresholds.csv"

WARNING_PERCENTILE = 90
DANGER_PERCENTILE = 98

# An event needs to stay above warning level for at least this many hours to
# count -- filters out single noisy-reading blips that aren't real floods.
MIN_EVENT_HOURS = 6


def compute_thresholds(levels: pd.Series, official_danger, official_warning):
    """Return (warning_level, danger_level, source) for one station."""
    if pd.notna(official_danger) and pd.notna(official_warning):
        return official_warning, official_danger, "official"
    warning = np.percentile(levels.dropna(), WARNING_PERCENTILE)
    danger = np.percentile(levels.dropna(), DANGER_PERCENTILE)
    return warning, danger, "percentile_proxy"


def extract_events(df_station: pd.DataFrame, warning_level: float, danger_level: float):
    """df_station must be sorted by datetime, with a 'water_level' column.
    Returns a list of event dicts."""
    above = df_station["water_level"] >= warning_level
    # Identify contiguous True-blocks (runs) using a group id that increments
    # every time the boolean flips
    group_id = (above != above.shift()).cumsum()
    events = []
    for gid, block in df_station[above].groupby(group_id[above]):
        if len(block) < MIN_EVENT_HOURS:
            continue
        peak_row = block.loc[block["water_level"].idxmax()]
        events.append({
            "start_date": block["datetime"].iloc[0],
            "end_date": block["datetime"].iloc[-1],
            "duration_hours": len(block),
            "peak_level": peak_row["water_level"],
            "peak_date": peak_row["datetime"],
            "warning_level_used": warning_level,
            "danger_level_used": danger_level,
            "flood_type": "Severe Flood" if peak_row["water_level"] >= danger_level else "Flood",
        })
    return events


def main():
    print("Loading station thresholds...")
    stations = pd.read_csv(STATIONS_CSV)

    print("Loading water level data (this may take a minute, it's a large file)...")
    levels = pd.read_csv(WATER_LEVELS_CSV, parse_dates=["datetime"])
    print(f"Loaded {len(levels)} readings across {levels['station_code'].nunique()} stations")

    all_events = []
    n_official, n_proxy = 0, 0

    for _, srow in stations.iterrows():
        code = srow["code_id"]
        station_data = levels[levels["station_code"] == code].sort_values("datetime")
        if len(station_data) < 24:  # need at least a day of data to bother
            continue

        warning_level, danger_level, source = compute_thresholds(
            station_data["water_level"], srow.get("official_danger"), srow.get("official_warning")
        )
        if source == "official":
            n_official += 1
        else:
            n_proxy += 1

        events = extract_events(station_data, warning_level, danger_level)
        for e in events:
            e.update({
                "GaugeID": code,
                "station_name": srow["name"],
                "region": srow["region"],
                "threshold_source": source,
            })
            all_events.append(e)

    if not all_events:
        print("No events detected -- check MIN_EVENT_HOURS / percentile settings.")
        return

    out = pd.DataFrame(all_events)
    out.to_csv("cwc_derived_flood_events.csv", index=False)

    print(f"\nStations using OFFICIAL danger levels: {n_official}")
    print(f"Stations using PERCENTILE PROXY thresholds: {n_proxy}")
    print(f"\nTotal detected events: {len(out)}")
    print(out["flood_type"].value_counts())
    print(f"\nEvents by threshold source:")
    print(out["threshold_source"].value_counts())
    print(f"\nWrote cwc_derived_flood_events.csv")
    print(out.head(10).to_string())


if __name__ == "__main__":
    main()
