import pandas as pd
import pytest
from helpers import build_pool, capture_at_k, first_pv_date, make_label


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


def test_make_label_start_exclusive_end_inclusive():
    first = pd.Series(
        pd.to_datetime(["2021-12-31", "2022-01-01", "2023-12-31", "2024-01-01"]),
        index=[1, 2, 3, 4],
    )
    label = make_label([1, 2, 3, 4, 5], first, "2021-12-31", "2023-12-31")
    assert list(label) == [0, 1, 1, 0, 0]
    assert label.dtype.kind == "i"
