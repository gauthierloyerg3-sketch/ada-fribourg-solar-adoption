"""Stage 01: download the open data and write the Fribourg extracts.

Drafted with an AI assistant, see docs/ai_log.md.

This is the only stage that touches the network. Run from the repository root:
    python code/01_get_data.py                      # all sources
    python code/01_get_data.py plants_2026_09       # one source only

Sources: plants, buildings, roofs, plants_2026_09, tariffs. Buildings and roofs depend
on each other (roofs are filtered with the building list), so roofs needs buildings.
Tariffs keep the municipalities of buildings_fr.parquet, so they need that file.
A run of one source only rewrites its own outputs and updates its own entries in
sources.json.

Inputs (downloaded into data/raw/, skipped if already there):
    plants zip (SFOE), building register zip (FSO), roof GeoPackage zip (SFOE),
    older plants snapshot zip (SFOE, published 2026-09-16),
    electricity tariffs (ElCom, SPARQL query to LINDAS, answer saved as CSV).
Outputs (data/processed/):
    pv_fr.parquet, buildings_fr.parquet, roofs_fr.parquet, pv_fr_2026_09.parquet,
    tariffs_fr.parquet, sources.json.

Downloaded files are untrusted data: they are only read, never executed.
"""

import argparse
import hashlib
import json
import sqlite3
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import helpers
import pandas as pd

PLANTS_URL = (
    "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/"
    "ch.bfe.elektrizitaetsproduktionsanlagen.zip"
)
BUILDINGS_URL = "https://public.madd.bfs.admin.ch/fr.zip"
ROOFS_URL = (
    "https://data.geo.admin.ch/ch.bfe.solarenergie-eignung-daecher/"
    "solarenergie-eignung-daecher/solarenergie-eignung-daecher_2056.gpkg.zip"
)
# Older snapshot of the plant register (STAC asset, last updated 2026-09-16)
PLANTS_SEP_URL = (
    "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/"
    "elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip"
)
LINDAS_URL = "https://lindas.admin.ch/query"
SOURCES = ["plants", "buildings", "roofs", "plants_2026_09", "tariffs"]

# Tariffs of ElCom: category H4 (household, 4,500 kWh/year), standard product, 2020 to 2025.
# All municipalities of Switzerland are fetched; canton Fribourg is kept afterwards.
TARIFF_QUERY = """\
PREFIX d: <https://energy.ld.admin.ch/elcom/electricityprice/dimension/>
SELECT ?period ?operator ?municipality ?total ?energy ?gridusage ?charge ?aidfee
FROM <https://lindas.admin.ch/elcom/electricityprice>
WHERE {
  <https://energy.ld.admin.ch/elcom/electricityprice> <https://cube.link/observationSet> ?set .
  ?set <https://cube.link/observation> ?obs .
  ?obs d:period ?period ;
       d:category <https://energy.ld.admin.ch/elcom/electricityprice/category/H4> ;
       d:product <https://energy.ld.admin.ch/elcom/electricityprice/product/standard> ;
       d:operator ?operator ;
       d:municipality ?municipality ;
       d:total ?total ; d:energy ?energy ; d:gridusage ?gridusage ;
       d:charge ?charge ; d:aidfee ?aidfee .
  FILTER (STR(?period) >= "2020" && STR(?period) <= "2025")
}
"""
TARIFF_COLUMNS = ["total", "energy", "gridusage", "charge", "aidfee"]

PLANTS_CSV = "ElectricityProductionPlant.csv"
BUILDINGS_CSV = "gebaeude_batiment_edificio.csv"
ROOFS_GPKG = "SOLKAT_DACH.gpkg"
ROOFS_TABLE = "SOLKAT_CH_DACH"

# Roof columns kept (no geometry), with the names used in roofs_fr.parquet
ROOF_COLUMNS = {
    "objectid": "objectid",
    "DF_UID": "df_uid",
    "GWR_EGID": "egid",
    "FLAECHE": "flaeche",
    "KLASSE": "klasse",
    "NEIGUNG": "neigung",
    "AUSRICHTUNG": "ausrichtung",
    "MSTRAHLUNG": "mstrahlung",
    "GSTRAHLUNG": "gstrahlung",
    "STROMERTRAG": "stromertrag",
    "DATUM_ERSTELLUNG": "datum_erstellung",
    "DATUM_AENDERUNG": "datum_aenderung",
}


def now_utc():
    """Current UTC time as an ISO string without microseconds."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_of(path):
    """SHA-256 of a file, read in 1 MB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def last_modified(url):
    """HTTP Last-Modified header of a URL (HEAD request), or None."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.headers.get("Last-Modified")
    except OSError:
        return None


def download(url, dest):
    """Download `url` to `dest` and return its source record.

    Skips the download if `dest` exists. Otherwise streams to `dest + ".part"`
    and renames when complete. The record holds url, size, sha256,
    last_modified and the UTC time of the download.
    """
    dest = str(dest)
    modified = None
    downloaded = None
    if not Path(dest).exists():
        with urllib.request.urlopen(url, timeout=120) as response:
            modified = response.headers.get("Last-Modified")
            with open(dest + ".part", "wb") as out:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        Path(dest + ".part").rename(dest)
        downloaded = now_utc()
    else:
        # File was already there (for example downloaded by hand): use its mtime
        mtime = Path(dest).stat().st_mtime
        downloaded = datetime.fromtimestamp(mtime, UTC).replace(microsecond=0).isoformat()
        modified = last_modified(url)
    return {
        "url": url,
        "size_bytes": Path(dest).stat().st_size,
        "sha256": sha256_of(dest),
        "last_modified": modified,
        "downloaded_utc": downloaded,
    }


def report(path):
    """Print one line for an output file: name, rows, size in MB."""
    frame = pd.read_parquet(path)
    megabytes = path.stat().st_size / 1e6
    print(f"{path.name}: {len(frame)} rows, {megabytes:.1f} MB")


def write_plants(zip_path, name="pv_fr.parquet"):
    """Photovoltaic plants in Fribourg, without address, postcode or coordinates."""
    with zipfile.ZipFile(zip_path) as z, z.open(PLANTS_CSV) as f:
        plants = pd.read_csv(f, encoding="utf-8-sig", dtype=str)
    # Photovoltaic is sub-category 2, canton Fribourg is FR
    plants = plants[(plants["SubCategory"] == "subcat_2") & (plants["Canton"] == "FR")]
    out = pd.DataFrame(
        {
            "xtf_id": pd.to_numeric(plants["xtf_id"]).astype("int64"),
            "egid": pd.to_numeric(plants["EGID"]).astype("Int64"),
            "start_date": pd.to_datetime(plants["BeginningOfOperation"], errors="coerce"),
            "initial_power_kw": pd.to_numeric(plants["InitialPower"]),
            "total_power_kw": pd.to_numeric(plants["TotalPower"]),
            "plant_category": plants["PlantCategory"],
        }
    ).reset_index(drop=True)
    path = helpers.PROCESSED / name
    out.to_parquet(path, index=False)
    report(path)


def write_buildings(zip_path):
    """All GWR buildings in Fribourg, all columns as read (strings), no cleaning."""
    with zipfile.ZipFile(zip_path) as z, z.open(BUILDINGS_CSV) as f:
        buildings = pd.read_csv(f, sep="\t", dtype=str)
    buildings.columns = [c.lower() for c in buildings.columns]
    path = helpers.PROCESSED / "buildings_fr.parquet"
    buildings.to_parquet(path, index=False)
    report(path)
    return buildings


def write_roofs(zip_path, buildings):
    """Roof surfaces of buildings in buildings_fr, attributes only (no geometry)."""
    gpkg_path = helpers.RAW / ROOFS_GPKG
    if not gpkg_path.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extract(ROOFS_GPKG, helpers.RAW)
    # Open read-only; a GeoPackage is a SQLite file
    con = sqlite3.connect(f"file:{gpkg_path}?mode=ro", uri=True)
    # Load the EGID set into a temporary table and filter with a subquery
    egids = pd.to_numeric(buildings["egid"]).dropna().astype("int64").unique()
    con.execute("CREATE TEMP TABLE fr_egid (egid INTEGER PRIMARY KEY)")
    con.executemany("INSERT INTO fr_egid VALUES (?)", [(int(e),) for e in egids])
    columns = ", ".join(ROOF_COLUMNS)
    query = (
        f"SELECT {columns} FROM {ROOFS_TABLE} "
        "WHERE GWR_EGID IN (SELECT egid FROM fr_egid) ORDER BY objectid"
    )
    roofs = pd.read_sql_query(query, con)
    n_total = con.execute(f"SELECT COUNT(*) FROM {ROOFS_TABLE}").fetchone()[0]
    con.close()
    print(f"roof table {ROOFS_TABLE}: {n_total} rows in total, {len(roofs)} kept for FR")
    roofs = roofs.rename(columns=ROOF_COLUMNS)
    # Dates are ISO strings in the GeoPackage
    for column in ["datum_erstellung", "datum_aenderung"]:
        roofs[column] = pd.to_datetime(roofs[column], errors="coerce", utc=True).dt.tz_localize(
            None
        )
    path = helpers.PROCESSED / "roofs_fr.parquet"
    roofs.to_parquet(path, index=False)
    report(path)


def fetch_tariffs(dest):
    """POST TARIFF_QUERY to LINDAS and save the CSV answer to `dest`; return its source record.

    Skips the request if `dest` exists. The record holds the endpoint, the SHA-256 of the
    query text, size and SHA-256 of the answer and the UTC time of the request.
    """
    if not Path(dest).exists():
        request = urllib.request.Request(
            LINDAS_URL,
            data=TARIFF_QUERY.encode(),
            headers={"Accept": "text/csv", "Content-Type": "application/sparql-query"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            body = response.read()
        Path(dest).write_bytes(body)
        downloaded = now_utc()
    else:
        mtime = Path(dest).stat().st_mtime
        downloaded = datetime.fromtimestamp(mtime, UTC).replace(microsecond=0).isoformat()
    return {
        "url": LINDAS_URL,
        "query_sha256": hashlib.sha256(TARIFF_QUERY.encode()).hexdigest(),
        "size_bytes": Path(dest).stat().st_size,
        "sha256": sha256_of(dest),
        "downloaded_utc": downloaded,
    }


def write_tariffs(csv_path):
    """Tariffs of the municipalities in buildings_fr, one row per municipality and year."""
    raw = pd.read_csv(csv_path)
    # Municipality number is the last part of https://ld.admin.ch/municipality/<BFS>
    raw["bfs_nr"] = raw["municipality"].str.rsplit("/", n=1).str[-1].astype("int64")
    raw = raw.rename(columns={"period": "year"})
    # Keep the municipalities of the building register (all of canton Fribourg)
    buildings = pd.read_parquet(helpers.PROCESSED / "buildings_fr.parquet", columns=["ggdenr"])
    raw = raw[raw["bfs_nr"].isin(pd.to_numeric(buildings["ggdenr"]).dropna().astype("int64"))]
    # Unit is inferred to be Rp/kWh (2024 median about 32.4); not stated in the answer.
    # Where a municipality has several operators in a year, take the mean of each price.
    grouped = raw.groupby(["bfs_nr", "year"])
    out = grouped[TARIFF_COLUMNS].mean()
    out["n_operators"] = grouped["operator"].nunique()
    out = out.reset_index().sort_values(["bfs_nr", "year"]).reset_index(drop=True)
    out = out.astype({"bfs_nr": "int64", "year": "int64", "n_operators": "int64"})
    path = helpers.PROCESSED / "tariffs_fr.parquet"
    out.to_parquet(path, index=False)
    report(path)


def main(selected):
    helpers.RAW.mkdir(parents=True, exist_ok=True)
    helpers.PROCESSED.mkdir(parents=True, exist_ok=True)

    # Keep the records of sources that are not run now
    sources_path = helpers.PROCESSED / "sources.json"
    sources = {}
    if sources_path.exists():
        with open(sources_path) as f:
            sources = json.load(f)

    # Raw file names (the older snapshot gets a distinct name)
    plants_zip = helpers.RAW / "ch.bfe.elektrizitaetsproduktionsanlagen.zip"
    plants_sep_zip = helpers.RAW / "elektrizitaetsproduktionsanlagen_2026_09.csv.zip"
    buildings_zip = helpers.RAW / "fr.zip"
    roofs_zip = helpers.RAW / "solarenergie-eignung-daecher_2056.gpkg.zip"

    # Download what is needed, record where it came from, write the extracts
    if "plants" in selected:
        sources[plants_zip.name] = download(PLANTS_URL, plants_zip)
        write_plants(plants_zip)
    if "plants_2026_09" in selected:
        sources[plants_sep_zip.name] = download(PLANTS_SEP_URL, plants_sep_zip)
        write_plants(plants_sep_zip, "pv_fr_2026_09.parquet")
    if "buildings" in selected or "roofs" in selected:
        sources[buildings_zip.name] = download(BUILDINGS_URL, buildings_zip)
        buildings = write_buildings(buildings_zip)
    if "roofs" in selected:
        sources[roofs_zip.name] = download(ROOFS_URL, roofs_zip)
        write_roofs(roofs_zip, buildings)
    # Tariffs come last: they are filtered with the building list written above
    if "tariffs" in selected:
        tariffs_csv = helpers.RAW / "tariffs_h4_standard_2020_2025.csv"
        sources[tariffs_csv.name] = fetch_tariffs(tariffs_csv)
        write_tariffs(tariffs_csv)

    with open(sources_path, "w") as f:
        json.dump(sources, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"{sources_path.name}: {len(sources)} sources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "sources",
        nargs="*",
        choices=SOURCES,
        default=SOURCES,
        help="sources to run (default: all)",
    )
    main(parser.parse_args().sources)
