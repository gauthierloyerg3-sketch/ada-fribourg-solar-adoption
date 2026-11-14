"""Checks on the committed files in data/processed/. A test is skipped if its file is missing.

Drafted with an AI assistant, see docs/ai_log.md.
"""

import helpers
import numpy as np
import pandas as pd
import pytest

HEATING_COLUMNS = ["genh1", "gwaerzh1", "gwaerdath1"]


def load(name):
    path = helpers.PROCESSED / name
    if not path.exists():
        pytest.skip(f"{name} is missing")
    return pd.read_parquet(path)


def test_model_table_key_is_unique():
    table = load("model_table.parquet")
    assert not table.duplicated(["egid", "cutoff"]).any()


def test_label_is_binary():
    table = load("model_table.parquet")
    assert set(table["y"].unique()) <= {0, 1}


def test_pool_has_no_pv_up_to_cutoff():
    table = load("model_table.parquet")
    first = helpers.first_pv_date(load("pv_fr.parquet"))
    first_dates = helpers.lookup_first_pv(table["egid"], first)
    assert not (first_dates <= pd.to_datetime(table["cutoff"])).any()


def test_positives_have_first_pv_inside_window():
    table = load("model_table.parquet")
    first = helpers.first_pv_date(load("pv_fr.parquet"))
    positives = table[table["y"] == 1]
    first_dates = helpers.lookup_first_pv(positives["egid"], first)
    start = pd.to_datetime(positives["cutoff"])
    end = start + pd.DateOffset(years=helpers.HORIZON_YEARS)
    assert first_dates.notna().all()
    assert ((first_dates > start) & (first_dates <= end)).all()


def test_no_heating_columns():
    for name in ["buildings_clean.parquet", "model_table.parquet"]:
        columns = load(name).columns
        assert not set(HEATING_COLUMNS) & set(columns)


def test_heating_features_have_the_keys_of_the_model_table():
    table = load("model_table.parquet")
    heating = load("heating_features.parquet")
    keys = ["egid", "cutoff"]
    assert not heating.duplicated(keys).any()
    merged = table[keys].merge(heating[keys], on=keys, how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()
    assert heating["heat_source"].notna().all()
    assert set(heating["heat_updated_after"].unique()) <= {0, 1}
    assert set(heating["heat_date_missing"].unique()) <= {0, 1}
    # No date means not updated after the cut-off
    assert (heating.loc[heating["heat_date_missing"] == 1, "heat_updated_after"] == 0).all()


def test_heating_clean_has_one_row_per_population_building():
    heating = load("heating_clean.parquet")
    clean = load("buildings_clean.parquet")
    assert heating["egid"].is_unique
    assert set(heating["egid"]) == set(clean["egid"])
    assert {"genh1", "gwaerzh1", "gwaerdath1"} <= set(heating.columns)


def test_main_tables_keep_heating_out_of_the_model_features():
    # The heating block lives in its own files; the model table has no heating-like column
    for name in ["buildings_clean.parquet", "model_table.parquet"]:
        columns = load(name).columns
        assert not [c for c in columns if str(c).startswith(helpers.HEATING_PREFIXES)]


def test_predictions_cover_model_table_once_per_model():
    table = load("model_table.parquet")
    predictions = load("predictions.parquet")
    keys = ["egid", "cutoff"]
    for _, part in predictions.groupby("model"):
        assert not part.duplicated(keys).any()
        merged = table[keys].merge(part[keys], on=keys, how="outer", indicator=True)
        assert (merged["_merge"] == "both").all()


def test_september_snapshot_has_same_schema_as_current_plants():
    current = load("pv_fr.parquet")
    snapshot = load("pv_fr_2026_09.parquet")
    assert list(snapshot.columns) == list(current.columns)
    assert snapshot.dtypes.astype(str).to_dict() == current.dtypes.astype(str).to_dict()


def test_september_snapshot_plant_key_is_unique():
    snapshot = load("pv_fr_2026_09.parquet")
    assert snapshot["xtf_id"].is_unique


def test_tariff_key_is_unique():
    tariffs = load("tariffs_fr.parquet")
    assert not tariffs.duplicated(["bfs_nr", "year"]).any()


def test_tariff_years_2022_and_2024_present():
    tariffs = load("tariffs_fr.parquet")
    assert {2022, 2024} <= set(tariffs["year"])


def test_tariff_total_has_no_missing_value():
    tariffs = load("tariffs_fr.parquet")
    assert tariffs["total"].notna().all()


def test_neighbour_features_match_brute_force():
    table = load("model_table.parquet")
    buildings = load("buildings_clean.parquet")
    first = helpers.first_pv_date(load("pv_fr.parquet"))
    xy = buildings[["gkode", "gkodn"]].to_numpy()
    egids = buildings["egid"].to_numpy()
    new_columns = ["nbr_n_100", "nbr_pv_share_100", "nbr_n_250", "nbr_pv_share_250"]
    # no missing values, shares are fractions
    assert not table[new_columns].isna().any().any()
    for radius in [100, 250]:
        assert table[f"nbr_pv_share_{radius}"].between(0, 1).all()
    rng = np.random.default_rng(0)
    for cutoff, part in table.groupby("cutoff"):
        has_pv = helpers.has_pv_by(buildings["egid"], first, cutoff)
        for row in part.iloc[rng.choice(len(part), 100, replace=False)].itertuples():
            # plain distances to all population buildings, the building itself excluded
            dist = np.hypot(*(xy - xy[egids == row.egid][0]).T)
            near = (dist <= 250) & (egids != row.egid)
            assert row.nbr_n_250 == near.sum()
            expected = has_pv[near].mean() if near.any() else 0.0
            assert abs(row.nbr_pv_share_250 - expected) < 1e-12


def test_tariff_columns_are_complete_and_consistent():
    table = load("model_table.parquet")
    assert table[["tariff_total", "tariff_dev"]].notna().all().all()
    # Filled municipalities sit at the canton median by construction
    assert (table.loc[table["tariff_filled"] == 1, "tariff_dev"] == 0).all()
    # One tariff per municipality and cut-off
    assert (table.groupby(["cutoff", "ggdenr"])["tariff_total"].nunique() == 1).all()


def test_id_columns_have_no_missing_values():
    table = load("model_table.parquet")
    assert table[["ggdenr", "gkode", "gkodn"]].notna().all().all()


def test_gp_cells_are_complete_and_large_enough():
    cells = load("gp_cells.parquet")
    assert (cells["n"] >= 10).all()
    assert not cells.isna().any().any()
    assert not cells.duplicated(["split", "cell_x", "cell_y"]).any()
