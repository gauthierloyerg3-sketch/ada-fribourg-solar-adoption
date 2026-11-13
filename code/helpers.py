"""Shared functions for the pipeline stages.

Drafted with an AI assistant, see docs/ai_log.md.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupKFold

# Folders, relative to the repository root, so that code works from any working directory
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"

# Cut-offs T of the two splits (see SPEC.md)
CUTOFFS = {"train": "2021-12-31", "test": "2023-12-31"}
HORIZON_YEARS = 2

# Pool rules
MIN_SUITABLE_ROOF_M2 = 20
SUITABLE_CLASS_MIN = 3
NEW_BUILD_FROM_YEAR = 2020
NEW_BUILD_PERIOD_CODE = 8023  # GWR construction period "after 2015" (GBAUP)


def capture_at_k(y, score, k):
    """Share of all positives captured in the top fraction k of the ranking.

    Observations are ranked by `score` descending. The top `ceil(k * n)` are
    selected, and the result is the number of positives (y == 1) among them
    divided by the number of positives overall. Ties are broken by original
    order (stable sort), so the result is deterministic. A random ranking
    gives k in expectation.

    `y` and `score` are array-likes of equal length; 0 < k <= 1.
    Raises ValueError on unequal lengths, k outside (0, 1], or no positives.
    """
    y = np.asarray(y)
    score = np.asarray(score)
    if y.shape != score.shape or y.ndim != 1:
        raise ValueError("y and score must be 1-D arrays of equal length")
    if not 0 < k <= 1:
        raise ValueError("k must be in (0, 1]")
    positives = y == 1
    n_pos = int(positives.sum())
    if n_pos == 0:
        raise ValueError("y has no positives")
    n_top = math.ceil(k * len(y))
    order = np.argsort(-score, kind="stable")
    return float(positives[order[:n_top]].sum() / n_pos)


def first_pv_date(pv):
    """Earliest PV start date per building.

    `pv` is a DataFrame with columns `egid` and `start_date`. Plants without an
    egid or without a start date are dropped (they cannot be dated or linked
    to a building). Returns a Series indexed by egid, named `first_pv_date`.
    """
    dated = pv.dropna(subset=["egid", "start_date"])
    first = dated.groupby("egid")["start_date"].min()
    first.name = "first_pv_date"
    return first


def lookup_first_pv(egids, first_pv):
    """First PV date for each id in `egids` (NaT if the building has no PV).

    Returns a datetime Series with the same index as `egids`.
    """
    egids = pd.Series(egids)
    dates = first_pv.reindex(egids.to_numpy()).to_numpy()
    return pd.Series(dates, index=egids.index)


def pool_status(buildings, first_pv, cutoff):
    """Why each building is in or out of the pool at the cut-off.

    `buildings` and `first_pv` are as in `build_pool`. Returns a Series (same
    index) with one of: "has_pv", "new_build", "no_roof", "small_roof", "pool".
    A building gets the first reason that applies, in this order: PV start date
    <= cutoff (a PV dated exactly on the cut-off counts, one dated after does
    not); new build (known year >= 2020, or period 8023 with the year missing);
    no roof record (suitable_area_m2 missing); suitable roof under 20 m2.
    """
    cutoff = pd.Timestamp(cutoff)
    first = lookup_first_pv(buildings["egid"], first_pv)
    has_pv = first <= cutoff
    new_year = buildings["gbauj"] >= NEW_BUILD_FROM_YEAR
    new_period = (buildings["gbaup"] == NEW_BUILD_PERIOD_CODE) & buildings["gbauj"].isna()
    new_build = new_year | new_period
    area = buildings["suitable_area_m2"]
    status = pd.Series("pool", index=buildings.index)
    # Assign in reverse priority so that the highest-priority reason wins
    status[area < MIN_SUITABLE_ROOF_M2] = "small_roof"
    status[area.isna()] = "no_roof"
    status[new_build] = "new_build"
    status[has_pv] = "has_pv"
    return status


def build_pool(buildings, first_pv, cutoff):
    """Buildings that can still adopt at the cut-off date.

    `buildings` has one row per building with columns `egid`, `gbauj`
    (construction year, may be missing), `gbaup` (construction period code)
    and `suitable_area_m2` (missing if the building has no roof record).
    `first_pv` is the output of `first_pv_date`. A building stays in the pool
    if all three hold (see `pool_status`):
    (a) it has no PV start date <= cutoff,
    (b) it is not a new build: not (gbauj >= 2020), and not (gbaup == 8023
        with gbauj missing),
    (c) suitable_area_m2 >= 20 (a missing value fails this test).
    """
    status = pool_status(buildings, first_pv, cutoff)
    return buildings[status == "pool"].copy()


def make_label(egids, first_pv, start, end):
    """Adoption label: 1 if the building's first PV start date is in (start, end].

    `start` is exclusive and `end` is inclusive. Buildings without any PV get 0.
    `egids` is a Series (or array-like) of building ids; the result is an
    integer Series with the same index.
    """
    egids = pd.Series(egids)
    first = lookup_first_pv(egids, first_pv)
    adopted = (first > pd.Timestamp(start)) & (first <= pd.Timestamp(end))
    return adopted.astype(int)


def has_pv_by(egids, first_pv, cutoff):
    """True where the building's first PV start date is <= cutoff (boolean array).

    The same rule as in `build_pool`: a PV dated exactly on the cut-off counts,
    one dated after it does not. Buildings without PV give False.
    """
    first = lookup_first_pv(egids, first_pv)
    return (first <= pd.Timestamp(cutoff)).to_numpy()


def neighbour_pv_share(xy, has_pv, radius):
    """Number of neighbours and share of them with PV, per point.

    `xy` is an (n, 2) array of coordinates in metres, `has_pv` a boolean array
    of length n, `radius` in metres. The neighbours of a point are all OTHER
    points at distance <= radius (the point itself is excluded; a different
    point at identical coordinates is a neighbour). Returns `(count, share)`:
    `count` is an integer array, `share` a float array with the fraction of the
    neighbours whose `has_pv` is True, and 0.0 when there is no neighbour.
    """
    xy = np.asarray(xy, dtype=float)
    has_pv = np.asarray(has_pv, dtype=bool)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(has_pv) != len(xy):
        raise ValueError("xy must be (n, 2) and has_pv of length n")
    # Neighbours within the radius, counted on all points and on PV points only;
    # both counts include the point itself when it is in the tree
    n_all = cKDTree(xy).query_ball_point(xy, radius, return_length=True)
    n_pv = cKDTree(xy[has_pv]).query_ball_point(xy, radius, return_length=True)
    # Remove the point itself (always in the first tree, in the second only if it has PV)
    count = np.asarray(n_all, dtype=np.int64) - 1
    n_pv = np.asarray(n_pv, dtype=np.int64) - has_pv
    share = np.divide(n_pv, count, out=np.zeros(len(xy)), where=count > 0)
    return count, share


# Columns that must never reach a model: ids, labels, split markers, raw tariff level and
# fill flag (only the deviation is used), and every heating variable (leakage, see SPEC.md)
NOT_FEATURES = [
    "egid", "cutoff", "split", "y", "y_2024", "ggdenr", "gkode", "gkodn",
    "tariff_total", "tariff_filled",
]  # fmt: skip
HEATING_PREFIXES = ("genh", "gwaer", "heat")
MIN_LEVEL_ROWS = 500  # building types (gklas) with fewer train rows are grouped as "other"
N_YIELD_BINS = 10


def _level_name(value):
    """Readable level label: 1020.0 -> "1020"."""
    return str(int(value))


def _raw_features(df, params):
    """Unstandardised feature columns of `df`, using the levels and fills in `params`."""
    out = {}
    # Roof: yield decile dummies (end bins catch values outside the train range)
    yield_bin = np.searchsorted(params["yield_edges"], df["yield_kwh"].to_numpy(), side="right")
    for i in range(params["n_yield_bins"]):
        out[f"yield_d{i + 1}"] = (yield_bin == i).astype(float)
    log_area = np.log(df["suitable_area_m2"].to_numpy())
    out["log_suitable_area"] = log_area
    out["log_suitable_area_sq"] = log_area**2
    out["suitable_share"] = (df["suitable_area_m2"] / df["roof_area_m2"]).to_numpy()
    for level in params["best_class_levels"]:
        out[f"best_class_{_level_name(level)}"] = (df["best_class"] == level).to_numpy(float)
    # Building: dwellings in bins 1, 2, 3, 4 or more, plus missing
    dwellings = df["ganzwhg"]
    for level in [1, 2, 3]:
        out[f"dwellings_{level}"] = (dwellings == level).to_numpy(float)
    out["dwellings_4plus"] = (dwellings >= 4).to_numpy(float)
    out["dwellings_missing"] = dwellings.isna().to_numpy(float)
    for level in params["gkat_levels"]:
        out[f"gkat_{_level_name(level)}"] = (df["gkat"] == level).to_numpy(float)
    for level in params["gbaup_levels"]:
        out[f"gbaup_{_level_name(level)}"] = (df["gbaup"] == level).to_numpy(float)
    out["gbaup_missing"] = df["gbaup"].isna().to_numpy(float)
    gklas = df["gklas"]
    for level in params["gklas_levels"]:
        out[f"gklas_{_level_name(level)}"] = (gklas == level).to_numpy(float)
    known = gklas.isin(params["gklas_levels"])
    out["gklas_other"] = (~known & gklas.notna()).to_numpy(float)
    out["gklas_missing"] = gklas.isna().to_numpy(float)
    out["floors"] = df["gastw"].fillna(params["gastw_median"]).to_numpy(float)
    out["floors_missing"] = df["gastw"].isna().to_numpy(float)
    out["log_footprint"] = np.log(df["garea"].fillna(params["garea_median"]).to_numpy(float))
    out["footprint_missing"] = df["garea"].isna().to_numpy(float)
    # Neighbours and tariff
    out["nbr_pv_share_100"] = df["nbr_pv_share_100"].to_numpy(float)
    out["nbr_pv_share_250"] = df["nbr_pv_share_250"].to_numpy(float)
    out["log1p_nbr_n_250"] = np.log1p(df["nbr_n_250"].to_numpy(float))
    out["tariff_dev"] = df["tariff_dev"].to_numpy(float)
    return pd.DataFrame(out, index=df.index)


def _check_no_forbidden(columns):
    """Raise if a heating column is among `columns`."""
    bad = [c for c in columns if str(c).lower().startswith(HEATING_PREFIXES)]
    if bad:
        raise ValueError(f"heating columns are not allowed as features: {bad}")


def fit_features(train):
    """Learn everything the feature matrix needs from the train rows only.

    `train` is the train part of `model_table`. Returns a dictionary of fitted
    parameters (decile edges of the yield, category levels, medians, and the
    mean and standard deviation of every column) to pass to `apply_features`.
    Columns that are constant on train are dropped. Heating columns raise an error.
    """
    _check_no_forbidden(train.columns)
    # Interior decile edges of the yield; duplicates collapse so bins stay non-empty
    quantiles = np.arange(1, N_YIELD_BINS) / N_YIELD_BINS
    edges = np.unique(train["yield_kwh"].quantile(quantiles).to_numpy())
    gklas_counts = train["gklas"].value_counts()
    params = {
        "yield_edges": edges,
        "n_yield_bins": len(edges) + 1,
        "best_class_levels": sorted(train["best_class"].dropna().unique()),
        "gkat_levels": sorted(train["gkat"].dropna().unique()),
        "gbaup_levels": sorted(train["gbaup"].dropna().unique()),
        "gklas_levels": sorted(gklas_counts[gklas_counts >= MIN_LEVEL_ROWS].index),
        "gastw_median": float(train["gastw"].median()),
        "garea_median": float(train["garea"].median()),
    }
    raw = _raw_features(train, params)
    mean = raw.mean()
    std = raw.std(ddof=0)
    keep = std[std > 0].index
    params["columns"] = list(keep)
    params["mean"] = mean[keep]
    params["std"] = std[keep]
    return params


def apply_features(df, params):
    """Standardised feature matrix of `df` with the parameters fitted on train.

    Returns a float DataFrame with readable column names, same index as `df`.
    Raises if any value is missing or if a heating column is present.
    """
    _check_no_forbidden(df.columns)
    raw = _raw_features(df, params)[params["columns"]]
    features = (raw - params["mean"]) / params["std"]
    _check_no_forbidden(features.columns)
    if features.isna().any().any():
        raise ValueError("missing values in the feature matrix")
    return features


def grouped_cv(groups, n_splits=5):
    """Cross-validation folds in which no group (municipality) is split.

    `groups` is an array-like with one group id per row. Returns a list of
    `(fit_index, validation_index)` pairs of positional row indices from
    `GroupKFold` (deterministic, no shuffling): each group appears in the
    validation part of exactly one fold.
    """
    groups = np.asarray(groups)
    folds = GroupKFold(n_splits=n_splits).split(np.zeros(len(groups)), groups=groups)
    return list(folds)
