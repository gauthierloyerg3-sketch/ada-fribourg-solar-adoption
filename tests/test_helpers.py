import numpy as np
import pandas as pd
import pytest
from helpers import (
    apply_features,
    build_pool,
    capture_at_k,
    cluster_bootstrap_indices,
    feature_label,
    first_pv_date,
    fit_features,
    format_interval,
    grid_cell,
    grouped_cv,
    has_pv_by,
    heat_source_group,
    latex_escape,
    make_label,
    neighbour_pv_share,
    pool_status,
)


def test_capture_perfect_ranking_at_base_rate():
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    score = [0.9, 0.8, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01]
    assert capture_at_k(y, score, 0.2) == 1.0


def test_capture_worst_ranking():
    y = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1]
    score = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05]
    assert capture_at_k(y, score, 0.2) == 0.0


def test_capture_k_one_is_one():
    assert capture_at_k([0, 1, 0, 1, 0], [0.3, 0.1, 0.9, 0.2, 0.5], 1) == 1.0


def test_capture_mixed_example():
    # ranking by score: idx 2 (0), idx 0 (1), idx 4 (0), idx 1 (1), idx 3 (0)
    y = [1, 1, 0, 0, 0]
    score = [0.8, 0.4, 0.9, 0.1, 0.5]
    # top ceil(0.4 * 5) = 2 -> idx 2, 0 -> one of two positives
    assert capture_at_k(y, score, 0.4) == 0.5
    # top ceil(0.8 * 5) = 4 -> idx 2, 0, 4, 1 -> both positives
    assert capture_at_k(y, score, 0.8) == 1.0


def test_capture_ties_broken_by_original_order():
    y = [0, 1, 0, 1]
    score = [1.0, 1.0, 1.0, 1.0]
    assert capture_at_k(y, score, 0.5) == 0.5  # top two are idx 0, 1
    y2 = [1, 0, 0, 1]
    assert capture_at_k(y2, score, 0.25) == 0.5  # top one is idx 0


def test_capture_length_mismatch():
    with pytest.raises(ValueError):
        capture_at_k([1, 0, 0], [0.1, 0.2], 0.5)


@pytest.mark.parametrize("k", [0, -0.1, 1.5])
def test_capture_bad_k(k):
    with pytest.raises(ValueError):
        capture_at_k([1, 0, 0], [0.3, 0.2, 0.1], k)


def test_capture_no_positives():
    with pytest.raises(ValueError):
        capture_at_k([0, 0, 0], [0.3, 0.2, 0.1], 0.5)


def make_pv():
    # Building 1 has two plants (earliest counts), building 2 has one, one plant has no egid
    return pd.DataFrame(
        {
            "egid": pd.array([1, 1, 2, None], dtype="Int64"),
            "start_date": pd.to_datetime(["2022-05-01", "2020-03-01", "2024-01-01", "2019-01-01"]),
        }
    )


def make_buildings(**overrides):
    # One clean building; tests change one column at a time
    row = {"egid": 10, "gbauj": 1980.0, "gbaup": 8015.0, "suitable_area_m2": 50.0}
    row.update(overrides)
    return pd.DataFrame([row])


def test_first_pv_date_takes_earliest_and_drops_no_egid():
    first = first_pv_date(make_pv())
    assert list(first.index) == [1, 2]
    assert first[1] == pd.Timestamp("2020-03-01")
    assert first[2] == pd.Timestamp("2024-01-01")


def test_build_pool_keeps_clean_building():
    pool = build_pool(make_buildings(), first_pv_date(make_pv().iloc[0:0]), "2021-12-31")
    assert list(pool["egid"]) == [10]


def test_build_pool_excludes_pv_on_or_before_cutoff():
    first = pd.Series([pd.Timestamp("2021-12-31")], index=[10])
    assert build_pool(make_buildings(), first, "2021-12-31").empty
    earlier = pd.Series([pd.Timestamp("2015-06-01")], index=[10])
    assert build_pool(make_buildings(), earlier, "2021-12-31").empty


def test_build_pool_keeps_pv_after_cutoff():
    first = pd.Series([pd.Timestamp("2022-01-01")], index=[10])
    assert list(build_pool(make_buildings(), first, "2021-12-31")["egid"]) == [10]


def test_build_pool_excludes_new_build_by_year():
    no_pv = pd.Series([], dtype="datetime64[ns]")
    assert build_pool(make_buildings(gbauj=2020.0), no_pv, "2021-12-31").empty
    assert not build_pool(make_buildings(gbauj=2019.0), no_pv, "2021-12-31").empty


def test_build_pool_excludes_new_build_by_period_when_year_missing():
    no_pv = pd.Series([], dtype="datetime64[ns]")
    new_period = make_buildings(gbauj=float("nan"), gbaup=8023.0)
    assert build_pool(new_period, no_pv, "2021-12-31").empty
    # Period 8023 with a known old year is not a new build
    assert not build_pool(make_buildings(gbauj=2010.0, gbaup=8023.0), no_pv, "2021-12-31").empty
    # Missing year and another period is kept
    assert not build_pool(make_buildings(gbauj=float("nan")), no_pv, "2021-12-31").empty


def test_build_pool_excludes_small_or_missing_roof():
    no_pv = pd.Series([], dtype="datetime64[ns]")
    assert build_pool(make_buildings(suitable_area_m2=19.9), no_pv, "2021-12-31").empty
    assert build_pool(make_buildings(suitable_area_m2=float("nan")), no_pv, "2021-12-31").empty
    assert not build_pool(make_buildings(suitable_area_m2=20.0), no_pv, "2021-12-31").empty


def test_pool_status_reasons_and_priority():
    no_pv = pd.Series([], dtype="datetime64[ns]")
    status = lambda **kw: pool_status(make_buildings(**kw), no_pv, "2021-12-31").iloc[0]  # noqa: E731
    assert status() == "pool"
    assert status(gbauj=2021.0) == "new_build"
    assert status(suitable_area_m2=float("nan")) == "no_roof"
    assert status(suitable_area_m2=5.0) == "small_roof"
    # New build wins over a missing roof, no roof wins over nothing else
    assert status(gbauj=2021.0, suitable_area_m2=float("nan")) == "new_build"
    # A PV on or before the cut-off wins over everything
    first = pd.Series([pd.Timestamp("2021-12-31")], index=[10])
    both = make_buildings(gbauj=2021.0, suitable_area_m2=5.0)
    assert pool_status(both, first, "2021-12-31").iloc[0] == "has_pv"


def test_make_label_start_exclusive_end_inclusive():
    first = pd.Series(
        pd.to_datetime(["2021-12-31", "2022-01-01", "2023-12-31", "2024-01-01"]),
        index=[1, 2, 3, 4],
    )
    label = make_label([1, 2, 3, 4, 5], first, "2021-12-31", "2023-12-31")
    assert list(label) == [0, 1, 1, 0, 0]
    assert label.dtype.kind == "i"


# Neighbour share: points on a line (metres), point 0 is the one under test
LINE = np.array([[0.0, 0.0], [60.0, 0.0], [100.0, 0.0], [100.1, 0.0], [500.0, 0.0]])


def test_neighbours_exclude_self_and_include_radius_boundary():
    count, share = neighbour_pv_share(LINE, np.array([True, True, True, True, False]), 100)
    # point 0: points 1 and 2 (exactly 100 m) are neighbours, point 3 (100.1 m) is not
    assert count[0] == 2
    assert share[0] == 1.0
    # the isolated point has no neighbour
    assert count[4] == 0


def test_share_is_zero_without_neighbours():
    count, share = neighbour_pv_share(LINE, np.ones(5, dtype=bool), 0.05)
    assert (count == 0).all()
    assert (share == 0.0).all()


def test_own_pv_does_not_count():
    # two points, only the first has PV: the first sees no PV, the second sees one of one
    xy = np.array([[0.0, 0.0], [10.0, 0.0]])
    count, share = neighbour_pv_share(xy, np.array([True, False]), 50)
    assert count.tolist() == [1, 1]
    assert share.tolist() == [0.0, 1.0]


def test_share_is_a_fraction_of_neighbours():
    # point 0 has three neighbours within 100 m (30, 40 and 100 m), one with PV
    xy = np.array([[0.0, 0.0], [30.0, 0.0], [0.0, 40.0], [60.0, 80.0]])
    count, share = neighbour_pv_share(xy, np.array([False, True, False, False]), 100)
    assert count[0] == 3
    assert share[0] == pytest.approx(1 / 3)


def test_identical_coordinates_are_neighbours():
    xy = np.array([[5.0, 5.0], [5.0, 5.0], [900.0, 900.0]])
    count, share = neighbour_pv_share(xy, np.array([False, True, False]), 1)
    assert count.tolist() == [1, 1, 0]
    assert share.tolist() == [1.0, 0.0, 0.0]


def test_neighbour_pv_dated_at_cutoff_counts_and_after_does_not():
    cutoff = "2021-12-31"
    pv = pd.DataFrame(
        {
            "egid": [2, 3],
            "start_date": pd.to_datetime(["2021-12-31", "2022-01-01"]),
        }
    )
    first = first_pv_date(pv)
    egids = pd.Series([1, 2, 3])
    has_pv = has_pv_by(egids, first, cutoff)
    assert has_pv.tolist() == [False, True, False]
    xy = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    count, share = neighbour_pv_share(xy, has_pv, 50)
    # building 1 sees building 2 (dated T, counted) and building 3 (T + 1 day, not counted)
    assert count[0] == 2
    assert share[0] == 0.5


def make_model_table(n=1200, seed=0):
    """Small synthetic model table with the columns the feature builder reads."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "egid": np.arange(n),
            "yield_kwh": rng.uniform(1000, 50000, n),
            "suitable_area_m2": rng.uniform(20, 300, n),
            "roof_area_m2": rng.uniform(300, 400, n),
            "best_class": rng.choice([3.0, 4.0, 5.0], n),
            "gkat": rng.choice([1020, 1030, 1040], n),
            "gklas": rng.choice([1110.0, 1121.0, 1130.0], n, p=[0.6, 0.38, 0.02]),
            "gbaup": rng.choice([8011.0, 8012.0], n),
            "garea": rng.uniform(40, 200, n),
            "gastw": rng.integers(1, 5, n).astype(float),
            "ganzwhg": rng.integers(1, 8, n).astype(float),
            "nbr_n_100": rng.integers(0, 30, n),
            "nbr_pv_share_100": rng.uniform(0, 1, n),
            "nbr_n_250": rng.integers(0, 100, n),
            "nbr_pv_share_250": rng.uniform(0, 1, n),
            "tariff_dev": rng.choice([0.0, 0.5, -0.5], n),
        }
    )
    df.loc[:9, "gastw"] = np.nan
    df.loc[10:19, "garea"] = np.nan
    df.loc[20:29, "ganzwhg"] = np.nan
    df.loc[30:39, "gklas"] = np.nan
    return df


def test_features_standardised_on_train_and_complete():
    train = make_model_table()
    params = fit_features(train)
    x = apply_features(train, params)
    assert not x.isna().any().any()
    assert np.allclose(x.mean(), 0, atol=1e-9)
    assert np.allclose(x.std(ddof=0), 1)
    assert {"gklas_other", "gklas_missing", "dwellings_missing", "floors_missing"} <= set(x.columns)
    assert "dwellings_4plus" in x.columns and "yield_d1" in x.columns


def test_features_use_train_parameters_only():
    train = make_model_table()
    test = make_model_table(seed=1)
    test["yield_kwh"] = 1e6  # far above the train range
    params = fit_features(train)
    x = apply_features(test, params)
    # Values above the train range land in the top decile bin
    assert (x["yield_d10"] > 0).all()
    assert x["yield_d1"].min() == x["yield_d1"].max()


def test_features_drop_constant_column_and_group_rare_levels():
    train = make_model_table()
    train["tariff_dev"] = 0.0
    params = fit_features(train)
    x = apply_features(train, params)
    assert "tariff_dev" not in x.columns
    # gklas 1130 is rare (under 500 rows), so it has no level of its own
    assert "gklas_1130" not in x.columns


def test_features_have_no_forbidden_or_heating_columns():
    train = make_model_table()
    x = apply_features(train, fit_features(train))
    forbidden = {"egid", "cutoff", "split", "y", "y_2024", "ggdenr", "gkode", "gkodn"}
    forbidden |= {"tariff_total", "tariff_filled"}
    assert not forbidden & set(x.columns)
    assert not any(c.startswith(("genh", "gwaer", "heat")) for c in x.columns)
    with pytest.raises(ValueError):
        fit_features(train.assign(genh1=7400))
    params = fit_features(train)
    with pytest.raises(ValueError):
        apply_features(train.assign(gwaerzh1=7500), params)


def test_grouped_cv_never_splits_a_group():
    groups = np.repeat(np.arange(23), np.arange(1, 24))  # 23 groups of unequal size
    folds = grouped_cv(groups, n_splits=5)
    assert len(folds) == 5
    seen = []
    for fit, val in folds:
        assert not set(groups[fit]) & set(groups[val])
        assert len(set(fit) | set(val)) == len(groups)
        seen.append(set(groups[val]))
    # Each group is in the validation part of exactly one fold
    assert sum(len(s) for s in seen) == 23
    assert set.union(*seen) == set(groups)


def test_cluster_bootstrap_is_reproducible_and_seed_dependent():
    groups = np.repeat(np.arange(30), 3)
    a = cluster_bootstrap_indices(groups, 5, seed=0)
    b = cluster_bootstrap_indices(groups, 5, seed=0)
    c = cluster_bootstrap_indices(groups, 5, seed=1)
    assert all(np.array_equal(x, y) for x, y in zip(a, b, strict=True))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c, strict=True))
    assert len(a) == 5


def test_cluster_bootstrap_draws_whole_groups_k_times():
    groups = np.repeat(np.arange(20), np.arange(1, 21))  # groups of unequal size
    sizes = np.bincount(groups)
    for idx in cluster_bootstrap_indices(groups, 10, seed=3):
        counts = np.bincount(groups[idx], minlength=20)
        times_drawn = counts / sizes
        # Each group appears an integer number of times its size, in total 20 draws
        assert np.array_equal(times_drawn, times_drawn.astype(int))
        assert times_drawn.sum() == 20
        # Each row of a group is repeated exactly as often as the group was drawn
        rows = np.bincount(idx, minlength=len(groups))
        assert np.array_equal(rows, times_drawn.astype(int)[groups])
        # Ascending order: copies of a row are adjacent
        assert np.all(np.diff(idx) >= 0)


def add_heating(df, seed=1):
    """Add the heating columns the sensitivity run reads to a synthetic model table."""
    rng = np.random.default_rng(seed)
    out = df.copy()
    out["heat_source"] = rng.choice(["oil", "gas", "heat_pump", "missing"], len(df))
    out["heat_updated_after"] = rng.integers(0, 2, len(df))
    out["heat_date_missing"] = rng.integers(0, 2, len(df))
    return out


def test_main_path_still_refuses_heating_columns_in_the_extended_table():
    train = add_heating(make_model_table())
    # Without `extra`, any heating column raises, including the new ones
    with pytest.raises(ValueError):
        fit_features(train)
    params = fit_features(
        train.drop(columns=["heat_source", "heat_updated_after", "heat_date_missing"])
    )
    with pytest.raises(ValueError):
        apply_features(train, params)


def test_sensitivity_path_accepts_only_the_named_heating_columns():
    train = add_heating(make_model_table())
    names = ["heat_source", "heat_updated_after", "heat_date_missing"]
    params = fit_features(train, extra=names)
    x = apply_features(train, params)
    assert {"heat_source_oil", "heat_source_gas", "heat_updated_after"} <= set(x.columns)
    main = apply_features(train.drop(columns=names), fit_features(train.drop(columns=names)))
    # The main columns are unchanged by the extra block
    assert np.allclose(x[main.columns].to_numpy(), main.to_numpy())
    assert x.shape[1] == main.shape[1] + 4 + 2
    # A raw register column is refused even on the sensitivity path
    with pytest.raises(ValueError):
        fit_features(train.assign(genh1=7530), extra=names)
    with pytest.raises(ValueError):
        apply_features(train.assign(gwaerzh1=7430), params)
    # Only the listed names are accepted as extras
    with pytest.raises(ValueError):
        fit_features(train, extra=["genh1"])


def test_heat_source_group_maps_codes():
    codes = pd.Series(
        [7501, 7511, 7513, 7530, 7520, 7542, 7560, 7582, 7500, 7598, 7570, 7550, None]
    )
    expected = [
        "heat_pump",
        "heat_pump",
        "heat_pump",
        "oil",
        "gas",
        "wood",
        "electricity",
        "district",
        "none",
        "undetermined",
        "other",
        "other",
        "missing",
    ]
    assert heat_source_group(codes).tolist() == expected


def test_grid_cell_floors_to_the_cell_corner():
    # Points inside one 500 m cell share a corner; the lower and left edges belong to the cell
    cx, cy = grid_cell(
        [2575000.0, 2575499.9, 2575500.0, 2574999.9],
        [1180000.0, 1180499.9, 1180000.0, 1180250.0],
        500,
    )
    assert list(cx) == [2575000.0, 2575000.0, 2575500.0, 2574500.0]
    assert list(cy) == [1180000.0, 1180000.0, 1180000.0, 1180000.0]
    # A 1,000 m grid merges neighbouring 500 m cells
    cx, cy = grid_cell([2575000.0, 2575500.0], [1180000.0, 1180500.0], 1000)
    assert list(cx) == [2575000.0, 2575000.0] and list(cy) == [1180000.0, 1180000.0]


def test_feature_label_names_levels_from_the_register_code_lists():
    assert feature_label("gklas_1122") == "Three or more dwellings (gklas 1122)"
    assert feature_label("gkat_1040") == "Partly residential (gkat 1040)"
    assert feature_label("gbaup_8011") == "Built before 1919 (gbaup 8011)"
    assert feature_label("gbaup_8012") == "Built 1919 to 1945 (gbaup 8012)"
    assert feature_label("yield_d3") == "Roof yield, train decile 3"
    assert feature_label("best_class_5") == "Best roof class 5"
    assert feature_label("heat_source_heat_pump") == "Heating source: heat pump"
    assert feature_label("tariff_dev") == "Tariff minus canton median"
    # Unknown names come back unchanged, so a missing label is visible
    assert feature_label("gbaup_9999") == "gbaup_9999"


def test_format_interval_and_latex_escape():
    assert format_interval(0.19453, 0.17922, 0.2142) == "0.195 [0.179, 0.214]"
    assert format_interval(0.05) == "0.050"
    assert format_interval(0.5, np.nan, np.nan) == "0.500"
    assert latex_escape("a_b & 5%") == "a\\_b \\& 5\\%"
