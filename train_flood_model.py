"""
Train a flood severity REGRESSOR on the hilly-region INDOFLOODS subset
(hilly_indofloods_combined.csv, produced by build_hilly_indofloods.py).

Target: SeverityRatio = Peak Flood Level / Danger Level for that station.
  - < 1.0  -> peak stayed below the danger threshold
  - >= 1.0 -> peak crossed the danger threshold ("severe" in INDOFLOODS' own terms)

Why regression instead of the earlier binary classifier:
  - More useful for a warning system: "72% of danger level, rising" beats a
    bare yes/no flag.
  - Squeezes more signal out of a small dataset -- a continuous target uses
    every event's exact severity instead of collapsing it to one bit.
  - Sidesteps the class-imbalance issue entirely (no majority-class bias to
    correct for).

Still uses GROUP-aware cross-validation (grouped by GaugeID) so stations
never leak between train and test -- the honest test of "does this
generalize to a river station the model hasn't seen," which is the real
deployment scenario for a hilly-region flash flood system.

Run:
    pip install xgboost scikit-learn pandas joblib --break-system-packages
    python train_flood_model.py
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
import joblib

INPUT_CSV = "hilly_indofloods_combined.csv"

# Hand-picked, physically-meaningful feature set -- edit freely once you've
# looked at the printed column list. Recent-rainfall + catchment-shape +
# land/soil features cover the main flood-generation drivers without
# dragging in 100+ near-duplicate columns for a ~200-row dataset.
CANDIDATE_FEATURES = [
    # recent rainfall leading up to the event (event-scale precipitation)
    "T1d", "T2d", "T3d", "T4d", "T5d", "T6d", "T7d", "T8d", "T9d", "T10d",
    # catchment shape / drainage
    "Catchment Area", "Catchment Length", "Relief Ratio", "Drainage Density",
    "Drainage Texture", "Form Factor", "Elongation Ratio", "Compactness Coefficient",
    # climate normals
    "Annual Precipitation", "Annual Mean Temperature",
    # land / soil / lithology / climate class
    "Land cover", "Soil type", "lithology type", "KoppenGeiger Climate Type",
    # human footprint
    "Population Density", "Urban percentage", "Road Density",
]


def find_column(df, keywords, exclude=()):
    """Find the first column whose name contains ALL keywords (case-insensitive)
    and none of the excluded substrings. Returns None if nothing matches."""
    for c in df.columns:
        lc = c.lower()
        if all(k in lc for k in keywords) and not any(e in lc for e in exclude):
            return c
    return None


def build_severity_ratio(df):
    peak_col = find_column(df, ["peak"], exclude=["discharge", "date", "time"])
    danger_col = find_column(df, ["danger"])

    if peak_col is None or danger_col is None:
        raise SystemExit(
            f"Couldn't auto-detect peak-level / danger-level columns "
            f"(found peak={peak_col!r}, danger={danger_col!r}).\n"
            f"Columns available:\n{list(df.columns)}\n"
            f"Edit find_column() calls above to match the real names."
        )

    print(f"Using '{peak_col}' as peak level and '{danger_col}' as danger level.")
    df = df.copy()
    df["SeverityRatio"] = df[peak_col] / df[danger_col]
    return df


def main():
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {INPUT_CSV}: {df.shape[0]} rows x {df.shape[1]} columns")
    print("All columns:", list(df.columns))

    df = build_severity_ratio(df)
    y = df["SeverityRatio"].copy()

    print(f"\nSeverityRatio stats: min={y.min():.2f}  median={y.median():.2f}  "
          f"max={y.max():.2f}  (>=1.0 means peak crossed danger level)")
    print(f"Share of events >= 1.0 (i.e. 'severe' in INDOFLOODS' own terms): "
          f"{(y >= 1.0).mean():.0%}")

    features = [c for c in CANDIDATE_FEATURES if c in df.columns]
    missing = [c for c in CANDIDATE_FEATURES if c not in df.columns]
    if missing:
        print(f"\nNote: these candidate columns weren't found and are skipped: {missing}")
    print(f"\nUsing {len(features)} features: {features}")

    X = df[features].copy()

    cat_cols = X.select_dtypes(include="object").columns
    for c in cat_cols:
        X[c] = X[c].fillna("Unknown")
        X[c] = LabelEncoder().fit_transform(X[c].astype(str))

    num_cols = X.select_dtypes(include=np.number).columns
    X[num_cols] = X[num_cols].fillna(X[num_cols].median())

    # Drop rows with no valid target (missing peak or danger level)
    valid = y.notna()
    if (~valid).any():
        print(f"\nDropping {(~valid).sum()} rows with missing peak/danger level.")
    X, y, df = X[valid], y[valid], df[valid]

    if "GaugeID" not in df.columns:
        raise SystemExit("No GaugeID column found -- can't do group-aware CV. "
                          "Check the combined CSV came from build_hilly_indofloods.py.")
    groups = df["GaugeID"]
    n_stations = groups.nunique()
    print(f"\n{n_stations} distinct stations across {len(df)} events.")

    try:
        from xgboost import XGBRegressor
        model = XGBRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.1, random_state=42,
        )
        model_name = "XGBoost"
    except ImportError:
        print("\nxgboost not installed, falling back to RandomForestRegressor.")
        model = RandomForestRegressor(n_estimators=300, max_depth=5, random_state=42)
        model_name = "RandomForest"

    n_splits = min(5, n_stations)
    if n_splits < 2:
        raise SystemExit("Need events from at least 2 different stations to cross-validate.")
    cv = GroupKFold(n_splits=n_splits)
    y_pred = cross_val_predict(model, X, y, cv=cv, groups=groups)

    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    # A naive baseline: always predict the overall mean severity ratio.
    # If the model doesn't clearly beat this, it isn't adding real value yet.
    baseline_pred = np.full_like(y, y.mean(), dtype=float)
    baseline_mae = mean_absolute_error(y, baseline_pred)

    print(f"\n=== {model_name}, {n_splits}-fold, grouped by GaugeID (no station leakage) ===")
    print(f"MAE:  {mae:.3f}   (naive 'always predict the mean' MAE: {baseline_mae:.3f})")
    print(f"RMSE: {rmse:.3f}")
    print(f"R^2:  {r2:.3f}   (0 = no better than predicting the mean, 1 = perfect)")

    # Also report the binary "did it cross danger level" view for comparability
    # with the earlier classifier, using 1.0 as the decision threshold
    from sklearn.metrics import classification_report
    y_true_bin = (y >= 1.0).astype(int)
    y_pred_bin = (y_pred >= 1.0).astype(int)
    print("\nFor reference, thresholding predictions at 1.0 (severe vs not):")
    print(classification_report(y_true_bin, y_pred_bin, target_names=["Flood", "Severe Flood"]))

    model.fit(X, y)
    if hasattr(model, "feature_importances_"):
        importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
        print("\nTop features by importance:")
        print(importances.head(15))

    joblib.dump({"model": model, "features": features}, "flood_model.joblib")
    print("\nSaved trained model -> flood_model.joblib")
    print("Load it in backend.py with: joblib.load('flood_model.joblib')")
    print("model.predict(...) now returns a continuous SeverityRatio, e.g. 0.83 or 1.24")


if __name__ == "__main__":
    main()
