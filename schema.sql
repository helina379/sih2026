-- schema.sql
-- SIH26192 Flash Flood Prediction — Database Schema

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Stations: every gauge station, old (INDOFLOODS) and new (CWC)
CREATE TABLE stations (
    station_id      TEXT PRIMARY KEY,
    name            TEXT,
    state           TEXT,
    location        GEOGRAPHY(Point, 4326),  -- lat/lon combined
    threshold_source TEXT CHECK (threshold_source IN ('official', 'percentile_proxy'))
);

-- 2. Readings: hourly water level time series (mainly from CWC data)
CREATE TABLE readings (
    id              SERIAL PRIMARY KEY,
    station_id      TEXT REFERENCES stations(station_id),
    reading_time    TIMESTAMP NOT NULL,
    water_level     NUMERIC
);

-- 3. Flood events: both INDOFLOODS historical events and CWC-derived events
CREATE TABLE flood_events (
    id                  SERIAL PRIMARY KEY,
    station_id          TEXT REFERENCES stations(station_id),
    event_start         TIMESTAMP,
    event_end           TIMESTAMP,
    peak_level          NUMERIC,
    danger_level        NUMERIC,
    severity_ratio      NUMERIC,   -- peak / danger level
    severity_label      TEXT,      -- e.g. 'Severe', 'Moderate'
    threshold_source    TEXT CHECK (threshold_source IN ('official', 'percentile_proxy')),
    source_dataset      TEXT       -- 'INDOFLOODS' or 'CWC_derived'
);

-- 4. Catchment features: terrain data, only available for INDOFLOODS's 167 events
CREATE TABLE catchment_features (
    station_id          TEXT PRIMARY KEY REFERENCES stations(station_id),
    drainage_density     NUMERIC,
    form_factor           NUMERIC,
    catchment_area        NUMERIC,
    -- add more terrain columns here as needed, all nullable by default
    notes                 TEXT
);

CREATE INDEX idx_readings_station_time ON readings(station_id, reading_time);
CREATE INDEX idx_events_station ON flood_events(station_id);