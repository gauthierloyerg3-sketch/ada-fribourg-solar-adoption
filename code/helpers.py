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
# The only heating columns that may enter a model, and only through the explicit `extra`
# argument of `fit_features` (the heating sensitivity run, see docs/decisions.md)
HEATING_EXTRA_CATEGORICAL = ["heat_source"]
HEATING_EXTRA_FLAGS = ["heat_updated_after", "heat_date_missing"]
HEATING_EXTRA_ALL = HEATING_EXTRA_CATEGORICAL + HEATING_EXTRA_FLAGS
# Register codes of the main heating's energy source (GENH1, labels from the register's
# code list) grouped into coarse sources. Codes not listed here are "other".
HEAT_SOURCE_CODES = {
    7500: "none",
    7501: "heat_pump",  # air
    7510: "heat_pump",  # geothermal (generic), probe 7511, coil 7512
    7511: "heat_pump",
    7512: "heat_pump",
    7513: "heat_pump",  # water
    7520: "gas",
    7530: "oil",
    7540: "wood",  # generic, logs 7541, pellets 7542, chips 7543
    7541: "wood",
    7542: "wood",
    7543: "wood",
    7560: "electricity",
    7580: "district",  # generic, high 7581 and low 7582 temperature
    7581: "district",
    7582: "district",
    7598: "undetermined",
}  # fmt: skip
MIN_LEVEL_ROWS = 500  # building types (gklas) with fewer train rows are grouped as "other"
N_YIELD_BINS = 10


def _level_name(value):
    """Readable level label: 1020.0 -> "1020"."""
    return str(int(value))


def heat_source_group(genh1):
    """Coarse heating source of each GENH1 code (Series in, Series of str out).

    heat_pump (air, geothermal, water), oil, gas, wood, electricity, district,
    none, undetermined, other (waste heat, solar thermal, other); a missing code
    gives "missing".
    """
    codes = pd.Series(genh1)
    group = codes.map(HEAT_SOURCE_CODES).fillna("other")
    group[codes.isna()] = "missing"
    return group


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
    # Heating block, only for the sensitivity run (params["extra"] is empty for the main model)
    for name in params["extra"]:
        if name in HEATING_EXTRA_CATEGORICAL:
            for level in params["extra_levels"][name]:
                out[f"{name}_{level}"] = (df[name] == level).to_numpy(float)
        else:
            out[name] = df[name].to_numpy(float)
    return pd.DataFrame(out, index=df.index)


def _check_no_forbidden(columns, extra=()):
    """Raise if a heating column is among `columns`, except the names listed in `extra`.

    A column is allowed if it is one of `extra` or one level of it (`name_level`).
    """
    bad = [
        c
        for c in columns
        if str(c).lower().startswith(HEATING_PREFIXES)
        and not any(str(c) == e or str(c).startswith(f"{e}_") for e in extra)
    ]
    if bad:
        raise ValueError(f"heating columns are not allowed as features: {bad}")


def fit_features(train, extra=None):
    """Learn everything the feature matrix needs from the train rows only.

    `train` is the train part of `model_table`. Returns a dictionary of fitted
    parameters (decile edges of the yield, category levels, medians, and the
    mean and standard deviation of every column) to pass to `apply_features`.
    Columns that are constant on train are dropped. Heating columns raise an error,
    unless named in `extra` (the sensitivity run only): a list from
    `HEATING_EXTRA_ALL`; `heat_source` becomes one-hot columns (all levels kept),
    the flags enter as 0/1; all are standardised like the other columns. Any other
    heating column still raises.
    """
    extra = list(extra or [])
    unknown = [e for e in extra if e not in HEATING_EXTRA_ALL]
    if unknown:
        raise ValueError(f"not a heating extra column: {unknown}")
    _check_no_forbidden(train.columns, extra)
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
        "extra": extra,
        "extra_levels": {
            name: sorted(train[name].dropna().unique())
            for name in extra
            if name in HEATING_EXTRA_CATEGORICAL
        },
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
    Raises if any value is missing or if a heating column is present (except the
    ones the parameters were fitted with through `extra`).
    """
    _check_no_forbidden(df.columns, params["extra"])
    raw = _raw_features(df, params)[params["columns"]]
    features = (raw - params["mean"]) / params["std"]
    _check_no_forbidden(features.columns, params["extra"])
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


def cluster_bootstrap_indices(groups, n_boot, seed):
    """Row indices of cluster-bootstrap replicates (whole groups drawn with replacement).

    `groups` is an array-like with one group id per row (for example the
    municipality). Each replicate draws as many groups as there are distinct
    groups, with replacement; a group drawn k times contributes all its rows
    k times. Returns a list of `n_boot` integer arrays of positional row
    indices. Within a replicate the indices are in ascending row order, so the
    copies of a row sit next to each other and a stable sort by score breaks
    ties the same way as in the original data. Deterministic for a given seed
    (`numpy.random.default_rng`); the same call gives the same draws for any
    model scored on the same rows.
    """
    codes = pd.factorize(np.asarray(groups))[0]
    n_groups = codes.max() + 1
    rng = np.random.default_rng(seed)
    replicates = []
    for _ in range(n_boot):
        drawn = rng.integers(0, n_groups, size=n_groups)
        times_drawn = np.bincount(drawn, minlength=n_groups)
        replicates.append(np.repeat(np.arange(len(codes)), times_drawn[codes]))
    return replicates


def grid_cell(x, y, size):
    """Lower-left corner of the square grid cell holding each point.

    `x`, `y` are coordinates (LV95 metres) and `size` the cell side in metres.
    Returns two arrays: the corners are the coordinates floored to a multiple
    of `size`. A point on a cell's lower or left edge belongs to that cell.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    return np.floor(x / size) * size, np.floor(y / size) * size


# Readable names for tables and figures (identifiers stay in the CSV files).
# Drafted with an AI assistant, see docs/ai_log.md.
MODEL_LABELS = {
    "random": "Random",
    "roof_yield": "Roof yield",
    "nbr_share": "Neighbour PV share",
    "lasso": "LASSO",
    "mlp": "Neural net (16)",
    "mlp_wide": "Neural net (32, 16)",
    "lasso_heat_source": "LASSO + heating source",
    "lasso_heat_date": "LASSO + heating source and date",
}

# Register code lists (kodes_codes_codici.csv in the register download), wording shortened.
# GKAT: building category. GKLAS: building class. GBAUP: construction period.
GKAT_LABELS = {
    1020: "Residential only",
    1030: "Residential with ancillary use",
    1040: "Partly residential",
}
GKLAS_LABELS = {
    1110: "One dwelling",
    1121: "Two dwellings",
    1122: "Three or more dwellings",
    1130: "Communal housing",
}
GBAUP_LABELS = {
    8011: "before 1919",
    8012: "1919 to 1945",
    8013: "1946 to 1960",
    8014: "1961 to 1970",
    8015: "1971 to 1980",
    8016: "1981 to 1985",
    8017: "1986 to 1990",
    8018: "1991 to 1995",
    8019: "1996 to 2000",
    8020: "2001 to 2005",
    8021: "2006 to 2010",
    8022: "2011 to 2015",
    8023: "after 2015",
}

# Feature columns that are not one level of a categorical variable
FEATURE_LABELS = {
    "log_suitable_area": "Log suitable roof area",
    "log_suitable_area_sq": "Log suitable roof area, squared",
    "suitable_share": "Suitable share of roof area",
    "dwellings_1": "Dwelling count: 1",
    "dwellings_2": "Dwelling count: 2",
    "dwellings_3": "Dwelling count: 3",
    "dwellings_4plus": "Dwelling count: 4 or more",
    "dwellings_missing": "Dwelling count not recorded",
    "gbaup_missing": "Construction period not recorded",
    "gklas_other": "Other building class",
    "gklas_missing": "Building class not recorded",
    "floors": "Floors",
    "floors_missing": "Floors not recorded",
    "log_footprint": "Log footprint",
    "footprint_missing": "Footprint not recorded",
    "nbr_pv_share_100": "Neighbour PV share, 100 m",
    "nbr_pv_share_250": "Neighbour PV share, 250 m",
    "log1p_nbr_n_250": "Log (1 + buildings within 250 m)",
    "tariff_dev": "Tariff minus canton median",
    "heat_updated_after": "Heating record updated after cut-off",
    "heat_date_missing": "Heating record date missing",
}


def feature_label(name):
    """Readable label of a feature column of `apply_features`; unknown names come back unchanged.

    Categorical levels keep their register code in brackets, for example
    "Built 1919 to 1945 (gbaup 8012)". Roof classes and yield bins are named by their level.
    """
    if name in FEATURE_LABELS:
        return FEATURE_LABELS[name]
    if name.startswith("yield_d"):
        return f"Roof yield, train decile {name.removeprefix('yield_d')}"
    if name.startswith("heat_source_"):
        return f"Heating source: {name.removeprefix('heat_source_').replace('_', ' ')}"
    prefix, _, level = name.rpartition("_")
    if prefix == "best_class":
        return f"Best roof class {level}"
    tables = {"gkat": GKAT_LABELS, "gklas": GKLAS_LABELS, "gbaup": GBAUP_LABELS}
    if prefix in tables and level.isdigit() and int(level) in tables[prefix]:
        text = tables[prefix][int(level)]
        if prefix == "gbaup":
            text = f"Built {text}"
        return f"{text} ({prefix} {level})"
    return name


def latex_escape(text):
    """Escape the characters of `text` that LaTeX reads as commands (&, %, #, underscore)."""
    for char in "&%#_":
        text = text.replace(char, "\\" + char)
    return text


def format_interval(value, low=None, high=None, digits=3):
    """`value [low, high]` with fixed decimals; the interval is left out if `low` is missing."""
    text = f"{value:.{digits}f}"
    if low is None or high is None or pd.isna(low) or pd.isna(high):
        return text
    return f"{text} [{low:.{digits}f}, {high:.{digits}f}]"


# ---------------------------------------------------------------------------
# Results report (written by 05_figures.ipynb to figures/report.md).
# Pure functions: DataFrames in, one Markdown string out, no file access.
# Drafted with an AI assistant, see docs/ai_log.md.
# ---------------------------------------------------------------------------

REPORT_MAIN_MODELS = ["random", "roof_yield", "nbr_share", "lasso", "mlp", "mlp_wide"]
REPORT_HEAT_MODELS = ["lasso_heat_source", "lasso_heat_date"]
REPORT_NETS = ["mlp", "mlp_wide"]
REPORT_METRIC_NAMES = {
    "capture_5": "capture at 5%",
    "capture_10": "capture at 10%",
    "roc_auc": "ROC AUC",
    "avg_precision": "average precision",
}
REPORT_MODEL_DESCRIPTIONS = {
    "random": "reference: a random ranking (expected values, no fitting)",
    "roof_yield": "baseline 1: rank by the yearly electricity yield of the suitable roof",
    "nbr_share": "baseline 2: rank by the share of buildings within 250 m that already have PV",
    "lasso": "L1-penalised logistic regression, class weights, penalty chosen by "
    "cross-validation grouped by municipality (the headline model)",
    "mlp": "small neural net (scikit-learn MLP, one hidden layer of 16) on the LASSO features",
    "mlp_wide": "small neural net (hidden layers 32 and 16) on the LASSO features",
    "lasso_heat_source": "sensitivity run: LASSO plus the heating source (leakage-contaminated)",
    "lasso_heat_date": "sensitivity run: LASSO plus heating source and record date "
    "(leakage-contaminated)",
}
SPATIAL_P_THRESHOLD = 0.05


def gap_verdict(lo, hi):
    """Verdict on a paired gap (first minus second) from its interval [lo, hi].

    "beats" if the whole interval lies above 0, "is below" if it lies below 0,
    otherwise "no detectable difference".
    """
    if lo > 0:
        return "beats"
    if hi < 0:
        return "is below"
    return "no detectable difference"


def spatial_verdict(p):
    """ "no detectable spatial structure" when the permutation p is >= 0.05, else "detectable"."""
    return "no detectable spatial structure" if p >= SPATIAL_P_THRESHOLD else "detectable"


def hit_rate_and_lift(capture_10, positives, n, base_rate):
    """Hit rate among the ceil(0.10 n) buildings ranked first, and its lift over the base rate."""
    hit = capture_10 * positives / math.ceil(0.10 * n)
    return hit, hit / base_rate


def _pct(x, digits=1):
    return f"{100 * x:.{digits}f}%"


def _pvalue(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _label(model):
    return MODEL_LABELS.get(model, model)


def _gap_rows(gaps, label):
    """Gap rows of one label as {(first, second, metric): (point, lo, hi)}, in input order."""
    out = {}
    for row in gaps[gaps["label"] == label].itertuples(index=False):
        first, second = row.pair.split(" minus ")
        out[(first, second, row.metric)] = (row.point, row.lo, row.hi)
    return out


def _gap_clause(first, second, metric, values):
    """One sentence fragment: the verdict on `metric` with the gap and its interval."""
    point, lo, hi = values
    verdict = gap_verdict(lo, hi)
    name = REPORT_METRIC_NAMES[metric]
    gap = f"gap {format_interval(point, lo, hi)}"
    a, b = _label(first), _label(second)
    if verdict == "no detectable difference":
        return f"no detectable difference between {a} and {b} on {name} ({gap})"
    return f"{a} {verdict} {b} on {name} ({gap})"


def _cap(text):
    return text[:1].upper() + text[1:]


def _pair_bullet(first, second, rows):
    clauses = [
        _gap_clause(first, second, m, rows[(first, second, m)])
        for m in REPORT_METRIC_NAMES
        if (first, second, m) in rows
    ]
    return "- " + _cap("; ".join(clauses)) + "." if clauses else None


def _pairs(rows):
    seen = []
    for first, second, _ in rows:
        if (first, second) not in seen:
            seen.append((first, second))
    return seen


def _net_summary(rows):
    verdicts = [
        gap_verdict(v[1], v[2])
        for (first, second, _), v in rows.items()
        if first in REPORT_NETS and second == "lasso"
    ]
    beats, below = "beats" in verdicts, "is below" in verdicts
    if beats and below:
        return "Mixed: a network wins on one metric and loses on another."
    if beats:
        return "At least one network improves on the LASSO: interactions add something here."
    if below:
        return (
            "The networks are below the LASSO: interactions add nothing, "
            "and the extra capacity costs ranking quality."
        )
    return "Interactions add nothing detectable over the LASSO."


def _metric_row(metrics, model, split, label):
    sel = metrics[
        (metrics["model"] == model) & (metrics["split"] == split) & (metrics["label"] == label)
    ]
    return sel.iloc[0] if len(sel) else None


def _headline_table(metrics):
    lines = [
        "| Model | Capture at 5% | Capture at 10% | ROC AUC | Average precision "
        "| Hit rate, top 10% | Lift, top 10% |",
        "|---|---|---|---|---|---|---|",
    ]
    for model in REPORT_MAIN_MODELS + REPORT_HEAT_MODELS:
        row = _metric_row(metrics, model, "test", "y")
        if row is None:
            continue
        cells = [
            format_interval(row[m], row[f"{m}_lo"], row[f"{m}_hi"]) for m in REPORT_METRIC_NAMES
        ]
        hit, lift = hit_rate_and_lift(
            row["capture_10"], row["positives"], row["n"], row["base_rate"]
        )
        name = _label(model)
        if model in REPORT_HEAT_MODELS:
            name += " (leakage, upper bound)"
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {_pct(hit)} | {lift:.2f} |")
    return lines


def _conclusion(metrics, gaps, gp_summary):
    out = []
    rows = _gap_rows(gaps, "y")
    # 1. LASSO against the baselines
    verdicts = {
        (b, m): gap_verdict(rows[("lasso", b, m)][1], rows[("lasso", b, m)][2])
        for b in ("roof_yield", "nbr_share")
        for m in ("capture_10", "roc_auc")
        if ("lasso", b, m) in rows
    }
    if verdicts:
        if all(v == "beats" for v in verdicts.values()) and len(verdicts) == 4:
            out.append(
                "The LASSO beats both baselines on capture at 10% and ROC AUC "
                "(paired intervals above 0)."
            )
        elif not any(v == "beats" for v in verdicts.values()):
            out.append(
                "The LASSO does not beat the baselines: no paired gap against roof yield or "
                "neighbour share has an interval above 0. This is a valid result."
            )
        else:
            wins = [
                f"{_label(b)} on {REPORT_METRIC_NAMES[m]}"
                for (b, m), v in verdicts.items()
                if v == "beats"
            ]
            rest = [
                f"{_label(b)} on {REPORT_METRIC_NAMES[m]}"
                for (b, m), v in verdicts.items()
                if v != "beats"
            ]
            out.append(
                "The LASSO beats the baselines only partly: it beats "
                + ", ".join(wins)
                + "; it does not beat "
                + ", ".join(rest)
                + "."
            )
    # 2. Lift of the LASSO
    lasso = _metric_row(metrics, "lasso", "test", "y")
    if lasso is not None:
        hit, lift = hit_rate_and_lift(
            lasso["capture_10"], lasso["positives"], lasso["n"], lasso["base_rate"]
        )
        out.append(
            f"In the top 10% of the LASSO ranking the hit rate is {_pct(hit)} against a base rate "
            f"of {_pct(lasso['base_rate'])}: lift {lift:.2f} (random: 1.00), capture "
            f"{_pct(lasso['capture_10'])} of the adopters."
        )
    # 3. Networks
    if any(m in set(metrics["model"]) for m in REPORT_NETS):
        out.append(_net_summary(rows))
    # 4. Spatial structure
    gp = _gp_frame(gp_summary)
    if "test" in gp.index:
        p = gp.loc["test", "neighbour_corr_p"]
        verdict = spatial_verdict(p)
        if verdict == "detectable":
            out.append(
                f"Spatial structure is detectable in the LASSO residuals on the test split "
                f"(neighbour correlation {gp.loc['test', 'neighbour_corr']:.3f}, p {_pvalue(p)}): "
                "the features do not capture all of the geography."
            )
        else:
            out.append(
                f"No detectable spatial structure is left in the LASSO residuals on the test split "
                f"(p {_pvalue(p)}, threshold {SPATIAL_P_THRESHOLD})."
            )
    # 5. Heating upper bound
    heat = [(m, _metric_row(metrics, m, "test", "y")) for m in REPORT_HEAT_MODELS]
    heat = [(m, r) for m, r in heat if r is not None]
    if heat and lasso is not None:
        best = max(heat, key=lambda t: t[1]["roc_auc"])
        out.append(
            f"The heating sensitivity runs reach ROC AUC {best[1]['roc_auc']:.3f} at best against "
            f"{lasso['roc_auc']:.3f} for the LASSO; this is a leakage-contaminated upper bound, "
            "not a result."
        )
    return out


def _gp_frame(gp_summary):
    gp = gp_summary if "split" in gp_summary.columns else gp_summary.reset_index()
    return gp.set_index("split")


def build_report(metrics, gaps, gp_summary, segments_summary, lasso_cv, n_boot, seed,
                 cutoffs=None, horizon_years=None):  # fmt: skip
    """Plain-language run report as one Markdown string (pure: no file access).

    `metrics`: as figures/metrics.csv. `gaps`: columns label, pair ("a minus b" with model
    identifiers), metric, point, lo, hi. `gp_summary`: as figures/gp_summary.csv.
    `segments_summary`: as figures/segments_summary.csv. `lasso_cv`: as figures/lasso_cv.csv.
    Every number comes from the arguments; sentences are templates that depend on the numbers.
    """
    cutoffs = CUTOFFS if cutoffs is None else cutoffs
    horizon = HORIZON_YEARS if horizon_years is None else horizon_years
    present = set(metrics["model"])
    L = []

    L += [
        "# Results report",
        "",
        "Generated by `code/05_figures.ipynb`; do not edit by hand. Template drafted with an AI "
        "assistant (see `docs/ai_log.md`). Aggregated results only, no per-building output. "
        "This is a run report, not paper text.",
        "",
    ]

    # --- What was run
    L += ["## What was run", ""]
    for split in ("train", "test"):
        row = _metric_row(metrics, "random", split, "y")
        start = pd.Timestamp(cutoffs[split]) + pd.Timedelta(days=1)
        end = pd.Timestamp(cutoffs[split]) + pd.DateOffset(years=horizon)
        L.append(
            f"- {split.capitalize()} pool, cut-off {cutoffs[split]}: {int(row['n']):,} buildings, "
            f"{int(row['positives']):,} adopters (first PV {start.date()} to {end.date()}), "
            f"base rate {_pct(row['base_rate'])}."
        )
    row24 = _metric_row(metrics, "random", "test", "y_2024")
    if row24 is not None:
        start = pd.Timestamp(cutoffs["test"]) + pd.Timedelta(days=1)
        L.append(
            f"- Robustness label `y_2024`: same test pool and ranking, first PV in {start.year}: "
            f"{int(row24['positives']):,} adopters, base rate {_pct(row24['base_rate'])}."
        )
    L.append("- Models:")
    for model in REPORT_MAIN_MODELS + REPORT_HEAT_MODELS:
        if model in present:
            L.append(f"  - `{model}` ({_label(model)}): {REPORT_MODEL_DESCRIPTIONS[model]}.")
    L += [
        f"- Intervals: 95% percentile intervals from a cluster bootstrap that resamples whole "
        f"municipalities, B = {n_boot}, seed {seed}; the same draws serve every model, so gaps "
        "between models are paired.",
        "",
    ]

    # --- Headline results
    L += [
        "## Headline results",
        "",
        "Test pool, label `y` (first PV after the test cut-off). Cells are `value [95% interval]`.",
        "",
    ]
    L += _headline_table(metrics)
    L.append("")

    # --- How to read the metrics
    L += [
        "## How to read the metrics",
        "",
        "- Capture at k: share of all adopters found in the top k of the ranking. Random gives k.",
        "- ROC AUC: probability that a random adopter is ranked above a random non-adopter. "
        "Random gives 0.5.",
        "- Average precision: area under the precision-recall curve. Random gives the base rate.",
        "- Hit rate (top 10%): share of adopters among the buildings ranked in the top 10%. "
        "Lift: hit rate divided by the base rate; random gives 1.",
        "",
    ]

    # --- What the numbers say
    rows_y = _gap_rows(gaps, "y")
    L += [
        "## What the numbers say",
        "",
        "Test, label `y`. Gaps are first minus second, paired bootstrap.",
        "",
    ]
    for first, second in _pairs(rows_y):
        if first in REPORT_HEAT_MODELS or first in REPORT_NETS:
            continue
        bullet = _pair_bullet(first, second, rows_y)
        if bullet:
            L.append(bullet)
    roof = _metric_row(metrics, "roof_yield", "test", "y")
    if roof is not None:
        lo, hi = roof["roc_auc_lo"], roof["roc_auc_hi"]
        if hi < 0.5:
            says = "is below random: the interval lies below 0.5"
        elif lo > 0.5:
            says = "is above random: the interval lies above 0.5"
        else:
            says = "is not distinguishable from random: the interval contains 0.5"
        L.append(
            f"- The roof-yield baseline {says} "
            f"(ROC AUC {format_interval(roof['roc_auc'], lo, hi)})."
        )
    parts = []
    for model in ["lasso"] + REPORT_NETS:
        tr = _metric_row(metrics, model, "train", "y")
        te = _metric_row(metrics, model, "test", "y")
        if tr is not None and te is not None:
            parts.append(
                f"{_label(model)} {tr['roc_auc']:.3f} to {te['roc_auc']:.3f} "
                f"({te['roc_auc'] - tr['roc_auc']:+.3f})"
            )
    if parts:
        L.append(
            "- ROC AUC, train (in-sample) to test (out-of-time): " + "; ".join(parts) + ". "
            "The train value is fitted on the same buildings; the test value is the one to trust."
        )
    net_bullet = [
        _gap_clause(a, b, m, rows_y[(a, b, m)])
        for (a, b, m) in rows_y
        if a in REPORT_NETS and b == "lasso"
    ]
    if net_bullet:
        L.append(
            "- Neural nets against the LASSO: "
            + "; ".join(net_bullet)
            + ". "
            + _net_summary(rows_y)
        )
    L.append("")

    # --- Robustness
    rows_24 = _gap_rows(gaps, "y_2024")
    L += ["## Robustness, 2024 only", "", "Label `y_2024`, same test pool and ranking.", ""]
    for first, second in _pairs(rows_24):
        if first in REPORT_HEAT_MODELS:
            continue
        bullet = _pair_bullet(first, second, rows_24)
        if bullet:
            L.append(bullet)
    common = [k for k in rows_y if k in rows_24]
    differ = [
        k for k in common
        if gap_verdict(rows_y[k][1], rows_y[k][2]) != gap_verdict(rows_24[k][1], rows_24[k][2])
    ]  # fmt: skip
    if not common:
        L.append("")
    elif not differ:
        L += ["", f"All {len(common)} verdicts agree with the headline label."]
    else:
        names = "; ".join(
            f"{_label(a)} vs {_label(b)} on {REPORT_METRIC_NAMES[m]}" for a, b, m in differ
        )
        L += [
            "",
            f"{len(differ)} of {len(common)} verdicts differ from the headline label: {names}.",
        ]
    L.append("")

    # --- Heating sensitivity
    L += [
        "## Heating sensitivity",
        "",
        "Warning: these runs use today's register snapshot, are contaminated by leakage "
        "(a heating record dated after the cut-off tells the outcome) and are an upper bound, "
        "never a candidate model.",
        "",
    ]
    lasso_test = _metric_row(metrics, "lasso", "test", "y")
    for model in REPORT_HEAT_MODELS:
        row = _metric_row(metrics, model, "test", "y")
        if row is None or lasso_test is None:
            continue
        clauses = [
            _gap_clause(model, "lasso", m, rows_y[(model, "lasso", m)])
            for m in ("capture_10", "roc_auc")
            if (model, "lasso", m) in rows_y
        ]
        L.append(
            f"- {_label(model)}: ROC AUC {row['roc_auc']:.3f} against {lasso_test['roc_auc']:.3f} "
            f"for the LASSO, capture at 10% {_pct(row['capture_10'])} against "
            f"{_pct(lasso_test['capture_10'])}"
            + (": " + "; ".join(clauses) if clauses else "")
            + "."
        )
    L.append("")

    # --- Gaussian process
    gp = _gp_frame(gp_summary)
    L += [
        "## Spatial structure left (Gaussian process)",
        "",
        "Gaussian process on the LASSO residuals averaged per grid cell. Verdict rule: "
        f"permutation p of the neighbour correlation >= {SPATIAL_P_THRESHOLD} means no detectable "
        "spatial structure, otherwise detectable.",
        "",
    ]
    for split in ("train", "test"):
        if split not in gp.index:
            continue
        r = gp.loc[split]
        L.append(
            f"- {split.capitalize()}: {int(r['cells_kept']):,} cells of "
            f"{int(r['cell_size_m'])} m kept; log marginal likelihood gain over the null "
            f"{r['log_ml_diff']:.2f}; neighbour correlation {r['neighbour_corr']:.3f} "
            f"(permutation p {_pvalue(r['neighbour_corr_p'])}): "
            f"{spatial_verdict(r['neighbour_corr_p'])}."
        )
    L += [
        "- The train split is in-sample (the LASSO was fitted on it); the test split is the "
        "out-of-time check.",
        "",
    ]

    # --- Segments
    seg = segments_summary
    L += [
        "## Segments",
        "",
        f"k = {len(seg)} segments (PCA and k-means fitted on the train pool). Segments are "
        "descriptive only: no claim of causes or of predictive value.",
        "",
        "| Segment | Train buildings | Train adoption | Test buildings | Test adoption |",
        "|---|---|---|---|---|",
    ]
    for r in seg.itertuples(index=False):
        L.append(
            f"| {int(r.segment)} | {int(r.train_n):,} | {_pct(r.train_rate)} "
            f"| {int(r.test_n):,} | {_pct(r.test_rate)} |"
        )
    L.append("")

    # --- LASSO penalty
    best = lasso_cv.loc[lasso_cv["mean_auc"].idxmax()]
    grid = lasso_cv["C"]
    if best["C"] == grid.max():
        edge = "at the upper edge of the grid (weakest penalty tested)"
    elif best["C"] == grid.min():
        edge = "at the lower edge of the grid (strongest penalty tested)"
    else:
        edge = "inside the grid, not at an edge"
    L += [
        "## LASSO penalty",
        "",
        f"Chosen C = {best['C']:.3g} with mean grouped-CV ROC AUC {best['mean_auc']:.3f} "
        f"(SE {best['se_auc']:.3f}), {edge}; grid of {len(lasso_cv)} values from "
        f"{grid.min():.3g} to {grid.max():.3g}.",
        "",
    ]

    # --- Limits
    L += [
        "## Limits",
        "",
        "- Register lag: 2025 is not fully registered, so the 2024-2025 label is understated "
        "for the last months; `y_2024` is the check.",
        "- Roof coverage: the roof file is the 2023 release; buildings without a roof record "
        "are dropped from the pool and adopt less.",
        "- Snapshot register: attributes are today's values; demolished buildings are missing.",
        "- Same buildings in train and test: out-of-time test, not out-of-sample across buildings.",
        "- Tariff and heating effects are not identified.",
        "- No causal claims.",
        "",
    ]

    # --- Conclusion
    L += ["## Conclusion", ""]
    L += [f"- {s}" for s in _conclusion(metrics, gaps, gp_summary)]
    L.append("")

    # --- Where things are
    L += [
        "## Where things are",
        "",
        "- `figures/README.md`: index of every file in `figures/`.",
        "- `figures/metrics.csv`: all metrics with intervals.",
        "- `docs/decisions.md`: decisions and their reasons.",
        "",
    ]
    return "\n".join(L)
