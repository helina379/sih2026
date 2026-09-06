"""
load_data.py — loads the SIH26192 flood CSVs into PostgreSQL/PostGIS
"""
import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:mypassword123@localhost/sih_floods")

# ---------- 1. STATIONS ----------
stations_official = pd.read_csv("hilly_stations_with_official_thresholds.csv")
stations_official = stations_official.rename(columns={
    "code_id": "station_id", "name": "name", "region": "state"
})
stations_official["station_id"] = stations_official["station_id"].astype(str).str.strip()

stations_official = stations_official.drop_duplicates(subset="station_id", keep="first")

cwc_events = pd.read_csv("cwc_derived_flood_events.csv")
cwc_stations = cwc_events[["GaugeID", "station_name", "region", "threshold_source"]].drop_duplicates()
cwc_stations = cwc_stations.rename(columns={"GaugeID": "station_id", "station_name": "name", "region": "state"})
cwc_stations["station_id"] = cwc_stations["station_id"].astype(str).str.strip()
cwc_stations = cwc_stations.drop_duplicates(subset="station_id", keep="first")

all_stations = pd.concat([ stations_official[["station_id", "name", "state"]], cwc_stations[["station_id", "name", "state"]] ])
all_stations = all_stations.drop_duplicates(subset="station_id", keep="first").dropna(subset=["station_id"])

print(f"Total unique stations to insert: {len(all_stations)}")

with engine.begin() as conn:
    for _, row in all_stations.iterrows():
        conn.execute(text(""" INSERT INTO stations (station_id, name, state) VALUES (:station_id, :name, :state) ON CONFLICT (station_id) DO NOTHING """), dict(row))
print("Stations loaded (duplicates skipped safely).")

# ---------- 2. FLOOD EVENTS (from CWC-derived) ----------
cwc_events_clean = cwc_events.rename(columns={
    "GaugeID": "station_id", "start_date": "event_start", "end_date": "event_end",
    "peak_level": "peak_level", "danger_level_used": "danger_level",
    "flood_type": "severity_label", "threshold_source": "threshold_source"
})
cwc_events_clean["station_id"] = cwc_events_clean["station_id"].astype(str).str.strip()
cwc_events_clean["severity_ratio"] = cwc_events_clean["peak_level"] / cwc_events_clean["danger_level"]
cwc_events_clean["source_dataset"] = "CWC_derived"

cols_needed = ["station_id", "event_start", "event_end", "peak_level",
               "danger_level", "severity_ratio", "severity_label",
               "threshold_source", "source_dataset"]
cwc_events_clean[cols_needed].to_sql("flood_events", engine, if_exists="append", index=False)
print(f"Loaded {len(cwc_events_clean)} CWC flood events")

# ---------- 2.5 Add missing INDOFLOODS stations ----------
indofloods_raw = pd.read_csv("hilly_indofloods_combined.csv")
indofloods_station_names = indofloods_raw["Station"].dropna().astype(str).str.strip().unique()

with engine.begin() as conn:
    for sid in indofloods_station_names:
        conn.execute(text(""" INSERT INTO stations (station_id, name, state) VALUES (:sid, :sid, NULL) ON CONFLICT (station_id) DO NOTHING """), {"sid": sid})
print(f"Ensured {len(indofloods_station_names)} INDOFLOODS stations exist in stations table")

# ---------- 3. INDOFLOODS EVENTS (167 historical events) ----------
indofloods_clean = indofloods_raw.rename(columns={
    "Station": "station_id", "Start Date": "event_start", "End Date": "event_end",
    "Peak Flood Level (m)": "peak_level", "Danger Level": "danger_level"
})
indofloods_clean["station_id"] = indofloods_clean["station_id"].astype(str).str.strip()
indofloods_clean["severity_ratio"] = indofloods_clean["peak_level"] / indofloods_clean["danger_level"]
indofloods_clean["severity_label"] = None
indofloods_clean["threshold_source"] = "official"
indofloods_clean["source_dataset"] = "INDOFLOODS"

indofloods_clean[cols_needed].to_sql("flood_events", engine, if_exists="append", index=False)
print(f"Loaded {len(indofloods_clean)} INDOFLOODS events")

print("Done.")