#!/usr/bin/env python3
"""Harmonize all raw rotation catalogs into a single analysis-ready table.

Reads everything in ``data/raw/*.csv`` that this script knows about, maps
cluster names to canonical labels + literature ages, keeps Teff and Prot as
the scientific payload, and writes ``data/processed/gyro_sample.csv`` with
the schema documented in ``README.md``.

Run the fetchers first (or only the ones you want):
    python scripts/fetch_curtis_2020.py            # t5 composite, 7 clusters
    python scripts/fetch_curtis_2020_rup147.py     # t1 Rup 147, 2.7 Gyr
    python scripts/fetch_godoy_rivera_2021.py      # 7 clusters, Gaia DR2
    python scripts/fetch_curtis_2019_psceri.py     # Pisces-Eridanus, 120 Myr
    python scripts/fetch_gruner_2023_m67.py        # M67, ~4 Gyr, Gaia DR3
    python scripts/fetch_hall_2021.py              # asteroseismic field stars, 1-13 Gyr
    python scripts/fetch_silva_aguirre_2017.py     # LEGACY ages/masses (66 stars)
    python scripts/fetch_nielsen_2017.py           # seismic Prot (literature)
    python scripts/fetch_mcquillan_2014.py         # surface spot Prot
    python scripts/build_legacy_sample.py          # -> legacy_assembled.csv
    python scripts/fetch_garcia_2014.py            # García spot Prot, 293 stars
    python scripts/fetch_chaplin_2014.py           # Chaplin ages, 518 stars
    python scripts/build_garcia_sample.py          # -> garcia_assembled.csv
    python scripts/build_gyro_sample.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
OUT = REPO_ROOT / "data" / "processed" / "gyro_sample.csv"

# Canonical cluster name -> adopted age [Gyr]. Ages follow the source papers
# and standard compilations; see README for per-cluster references.
CLUSTER_AGE_GYR: dict[str, float] = {
    "NGC 2547": 0.035,
    "Pleiades": 0.120,
    "Pisces-Eridanus": 0.120,
    "M50": 0.130,
    "NGC 2516": 0.150,
    "M37": 0.500,
    "Praesepe": 0.670,
    "NGC 6811": 1.000,
    "NGC 752": 1.400,
    "NGC 6819": 2.500,
    "Ruprecht 147": 2.700,
    "M67": 4.000,
}

# Raw cluster label (as it appears in each source catalog) -> canonical label.
CLUSTER_ALIASES: dict[str, str] = {
    # Curtis 2020 Table 5 already uses canonical names.
    "Pleiades": "Pleiades",
    "Praesepe": "Praesepe",
    "NGC 6811": "NGC 6811",
    "NGC 6819": "NGC 6819",
    "NGC 752": "NGC 752",
    "Ruprecht 147": "Ruprecht 147",
    # Godoy-Rivera 2021 drops the space between "NGC" and the number.
    "NGC2516": "NGC 2516",
    "NGC2547": "NGC 2547",
    "NGC6811": "NGC 6811",
    "M37": "M37",
    "M50": "M50",
}

UNIFIED_COLUMNS = [
    "source_catalog",
    "cluster",
    "cluster_age_gyr",
    "gaia_dr2",
    "gaia_dr3",
    "kic",
    "teff_k",
    "teff_source",       # 'catalog' or 'derived_bp_rp'
    "bp_rp_0",           # dereddened Gaia BP-RP, where published
    "prot_d",
    "prot_source",       # 'spot_modulation' | 'asteroseismic_splitting' | per-paper label
    "ra_deg",
    "dec_deg",
    # Age columns — populated for all rows in the final output.
    "age_gyr",           # adopted age (cluster_age_gyr for cluster stars, asteroseismic for field)
    "age_source",        # 'cluster' | 'asteroseismic_hall_2021' | 'asteroseismic_legacy'
    "age_unc_gyr",       # symmetric uncertainty in age (null for cluster stars)
    # Model parameters — populated for asteroseismic catalogs with BASTA results.
    "mass_msun",
    "mass_unc_msun",
    "mass_source",       # 'basta' | 'mist_isochrone' | null
    "feh",
    "logg",
    "radius_rsun",
]


def _norm_cluster(raw: str) -> str:
    key = str(raw).strip()
    return CLUSTER_ALIASES.get(key, key)


def _empty_frame(n: int) -> pd.DataFrame:
    """Return a DataFrame with the unified schema and `n` blank rows."""
    data = {c: pd.Series([pd.NA] * n, dtype="object") for c in UNIFIED_COLUMNS}
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Per-catalog loaders: each returns a DataFrame with UNIFIED_COLUMNS.
# ---------------------------------------------------------------------------

def _load_curtis_2020() -> pd.DataFrame:
    df = pd.read_csv(RAW / "curtis_2020_table5.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "curtis_2020"
    out["cluster"] = df["Cluster"].map(_norm_cluster)
    out["cluster_age_gyr"] = pd.to_numeric(df["Age"], errors="coerce")
    out["gaia_dr2"] = df["GaiaDR2"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["bp_rp_0"] = pd.to_numeric(df.get("__BP-RP_0"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["Prot"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    out["ra_deg"] = pd.to_numeric(df["RA_ICRS"], errors="coerce")
    out["dec_deg"] = pd.to_numeric(df["DE_ICRS"], errors="coerce")
    return out


def _load_curtis_2020_rup147() -> pd.DataFrame:
    df = pd.read_csv(RAW / "curtis_2020_rup147.csv")
    prot = pd.to_numeric(df["Prot"], errors="coerce")
    mask = prot > 0
    df = df.loc[mask].reset_index(drop=True)
    out = _empty_frame(len(df))
    out["source_catalog"] = "curtis_2020_rup147"
    out["cluster"] = "Ruprecht 147"
    out["cluster_age_gyr"] = CLUSTER_AGE_GYR["Ruprecht 147"]
    out["gaia_dr2"] = df["GaiaDR2"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["bp_rp_0"] = pd.to_numeric(df.get("BP-RP"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["Prot"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    out["ra_deg"] = pd.to_numeric(df["RA_ICRS"], errors="coerce")
    out["dec_deg"] = pd.to_numeric(df["DE_ICRS"], errors="coerce")
    return out


def _load_godoy_rivera_2021() -> pd.DataFrame:
    df = pd.read_csv(RAW / "godoy_rivera_2021.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "godoy_rivera_2021"
    out["cluster"] = df["Cluster"].map(_norm_cluster)
    out["cluster_age_gyr"] = out["cluster"].map(CLUSTER_AGE_GYR)
    out["gaia_dr2"] = df["GaiaDR2"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["bp_rp_0"] = pd.to_numeric(df.get("BP-RP"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["Period"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    out["ra_deg"] = pd.to_numeric(df["RA_ICRS"], errors="coerce")
    out["dec_deg"] = pd.to_numeric(df["DE_ICRS"], errors="coerce")
    return out


def _load_curtis_2019_psceri() -> pd.DataFrame:
    df = pd.read_csv(RAW / "curtis_2019_psceri.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "curtis_2019_psceri"
    out["cluster"] = "Pisces-Eridanus"
    out["cluster_age_gyr"] = CLUSTER_AGE_GYR["Pisces-Eridanus"]
    out["gaia_dr2"] = df["Source"].astype("string").str.strip()
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["bp_rp_0"] = pd.to_numeric(df.get("GBP-GRP"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["Prot"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    return out


def _load_gruner_2023_m67() -> pd.DataFrame:
    df = pd.read_csv(RAW / "gruner_2023_m67.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "gruner_2023_m67"
    out["cluster"] = "M67"
    out["cluster_age_gyr"] = CLUSTER_AGE_GYR["M67"]
    out["gaia_dr3"] = df["dr3_source_id"].astype("Int64").astype("string")
    out["teff_k"] = pd.NA          # filled later by Teff derivation
    out["teff_source"] = pd.NA
    out["bp_rp_0"] = pd.to_numeric(df.get("(BP-RP)0"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["period"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    return out


def _load_hall_2021() -> pd.DataFrame:
    df = pd.read_csv(RAW / "hall_2021.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "hall_2021"
    # Field stars — no cluster association.
    out["cluster"] = pd.NA
    out["cluster_age_gyr"] = pd.NA
    out["kic"] = df["KIC"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["prot_d"] = pd.to_numeric(df["P"], errors="coerce")
    out["prot_source"] = "asteroseismic_splitting"
    # Asteroseismic individual ages.
    out["age_gyr"] = pd.to_numeric(df["age"], errors="coerce")
    out["age_source"] = "asteroseismic_hall_2021"
    lo = pd.to_numeric(df["loage"], errors="coerce")
    up = pd.to_numeric(df["upage"], errors="coerce")
    out["age_unc_gyr"] = (lo + up) / 2.0
    # Model parameters from Hall 2021.
    out["mass_msun"] = pd.to_numeric(df.get("modmass"), errors="coerce")
    out["mass_source"] = out["mass_msun"].where(out["mass_msun"].isna(), "basta")
    out["feh"] = pd.to_numeric(df.get("feh"), errors="coerce")
    out["logg"] = pd.to_numeric(df.get("modlogg"), errors="coerce")
    out["radius_rsun"] = pd.to_numeric(df.get("modrad"), errors="coerce")
    return out


def _load_legacy_2017() -> pd.DataFrame:
    """Load the assembled LEGACY sample (SA2017 + surface Prot crossmatch)."""
    path = REPO_ROOT / "data" / "processed" / "legacy_assembled.csv"
    df = pd.read_csv(path)
    out = _empty_frame(len(df))
    out["source_catalog"] = "legacy_2017"
    out["cluster"] = pd.NA
    out["cluster_age_gyr"] = pd.NA
    out["kic"] = df["KIC"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["Teff"], errors="coerce")
    out["teff_source"] = "catalog"
    out["bp_rp_0"] = pd.to_numeric(df.get("bprp"), errors="coerce")
    out["prot_d"] = pd.to_numeric(df["prot_d"], errors="coerce")
    out["prot_source"] = df["prot_source"]
    # Asteroseismic individual ages from BASTA.
    out["age_gyr"] = pd.to_numeric(df["age"], errors="coerce")
    out["age_source"] = "asteroseismic_legacy"
    lo = pd.to_numeric(df["loage"], errors="coerce")
    up = pd.to_numeric(df["upage"], errors="coerce")
    out["age_unc_gyr"] = (lo + up) / 2.0
    # BASTA model parameters.
    out["mass_msun"] = pd.to_numeric(df["modmass"], errors="coerce")
    out["mass_source"] = out["mass_msun"].where(out["mass_msun"].isna(), "basta")
    out["feh"] = pd.to_numeric(df["feh"], errors="coerce")
    out["logg"] = pd.to_numeric(df["modlogg"], errors="coerce")
    out["radius_rsun"] = pd.to_numeric(df["modrad"], errors="coerce")
    return out


def _load_garcia_2014() -> pd.DataFrame:
    """Load García 2014 rotation periods + Chaplin 2014 asteroseismic properties."""
    df = pd.read_csv(RAW / "garcia_assembled.csv")
    out = _empty_frame(len(df))
    out["source_catalog"] = "garcia_2014"
    out["cluster"] = pd.NA
    out["cluster_age_gyr"] = pd.NA
    out["kic"] = df["KIC"].astype("Int64").astype("string")
    out["teff_k"] = pd.to_numeric(df["teff_k"], errors="coerce")
    out["teff_source"] = "catalog"
    out["prot_d"] = pd.to_numeric(df["prot_d"], errors="coerce")
    out["prot_source"] = "spot_modulation"
    out["age_gyr"] = pd.to_numeric(df["age_gyr"], errors="coerce")
    out["age_source"] = "asteroseismic_garcia2014"
    out["age_unc_gyr"] = pd.to_numeric(df["age_unc_gyr"], errors="coerce")
    out["mass_msun"] = pd.to_numeric(df["mass_msun"], errors="coerce")
    out["mass_source"] = out["mass_msun"].where(out["mass_msun"].isna(), "basta")
    out["feh"] = pd.to_numeric(df["feh"], errors="coerce")
    out["logg"] = pd.to_numeric(df["logg"], errors="coerce")
    out["radius_rsun"] = pd.to_numeric(df["radius_rsun"], errors="coerce")
    return out


LOADERS = {
    "curtis_2020":          _load_curtis_2020,
    "curtis_2020_rup147":   _load_curtis_2020_rup147,
    "godoy_rivera_2021":    _load_godoy_rivera_2021,
    "curtis_2019_psceri":   _load_curtis_2019_psceri,
    "gruner_2023_m67":      _load_gruner_2023_m67,
    "hall_2021":            _load_hall_2021,
    "legacy_2017":          _load_legacy_2017,
    "garcia_2014":          _load_garcia_2014,
}


# ---------------------------------------------------------------------------
# Teff derivation for catalogs that publish only colour.
# ---------------------------------------------------------------------------

def _fit_bprp_to_teff(reference: pd.DataFrame, deg: int = 4) -> np.poly1d:
    """Fit a polynomial Teff = f((BP-RP)_0) to a reference catalog.

    We use the Curtis 2020 Table 5 composite as the reference because it
    spans 120 Myr to 2.7 Gyr with both Teff and (BP-RP)_0 published, and
    it is the catalog whose Teff scale the downstream analyses already
    adopt. The fit is restricted to the well-populated colour range
    (0.5 <= BP-RP <= 2.6) to avoid polynomial extrapolation artefacts.
    """
    bprp = pd.to_numeric(reference["bp_rp_0"], errors="coerce")
    teff = pd.to_numeric(reference["teff_k"], errors="coerce")
    m = bprp.between(0.5, 2.6) & teff.notna() & bprp.notna()
    coeffs = np.polyfit(bprp[m].to_numpy(), teff[m].to_numpy(), deg)
    return np.poly1d(coeffs)


def _derive_missing_teff(sample: pd.DataFrame) -> pd.DataFrame:
    reference = sample[sample["source_catalog"] == "curtis_2020"]
    if len(reference) == 0:
        return sample  # nothing to fit with
    poly = _fit_bprp_to_teff(reference)

    sample = sample.copy()
    need = sample["teff_k"].isna() & sample["bp_rp_0"].notna()
    derived = poly(pd.to_numeric(sample.loc[need, "bp_rp_0"]).to_numpy())
    sample.loc[need, "teff_k"] = derived
    sample.loc[need, "teff_source"] = "derived_bp_rp"
    sample.loc[~need & sample["teff_source"].isna() & sample["teff_k"].notna(),
               "teff_source"] = "catalog"
    return sample


# ---------------------------------------------------------------------------
# Populate age_gyr / age_source for cluster stars.
# ---------------------------------------------------------------------------

def _populate_age_columns(sample: pd.DataFrame) -> pd.DataFrame:
    """Fill age_gyr and age_source for every row.

    Cluster stars: age_gyr = cluster_age_gyr, age_source = "cluster",
    age_unc_gyr = null (cluster ages are point estimates in this schema).
    Field-star catalogs (e.g. Hall 2021) set these columns in their loader.
    """
    sample = sample.copy()
    is_cluster = sample["cluster"].notna() & sample["age_gyr"].isna()
    sample.loc[is_cluster, "age_gyr"] = pd.to_numeric(
        sample.loc[is_cluster, "cluster_age_gyr"], errors="coerce"
    )
    sample.loc[is_cluster, "age_source"] = "cluster"
    # age_unc_gyr stays NA for cluster stars (point estimates).
    return sample


# ---------------------------------------------------------------------------
# MIST isochrone masses for cluster stars (graceful: warn if missing).
# ---------------------------------------------------------------------------

MIST_MASSES_PATH = RAW / "cluster_masses_mist.csv"


def _merge_mist_masses(sample: pd.DataFrame) -> pd.DataFrame:
    """Join MIST-interpolated masses onto cluster stars lacking mass_msun.

    Reads ``data/raw/cluster_masses_mist.csv`` if it exists; otherwise
    prints a warning and returns the sample unchanged.
    """
    if not MIST_MASSES_PATH.exists():
        n_missing = (
            sample["cluster"].notna()
            & sample["mass_msun"].isna()
            & sample["teff_k"].notna()
            & sample["prot_d"].notna()
        ).sum()
        print(f"[warn] {MIST_MASSES_PATH.relative_to(REPO_ROOT)} not found — "
              f"{n_missing} cluster stars will lack mass_msun.",
              file=sys.stderr)
        print("  Run: python scripts/interpolate_cluster_masses.py",
              file=sys.stderr)
        return sample

    mist = pd.read_csv(MIST_MASSES_PATH)
    print(f"[info] loading MIST masses: {len(mist)} rows from "
          f"{MIST_MASSES_PATH.relative_to(REPO_ROOT)}")

    sample = sample.copy()
    need = (
        sample["cluster"].notna()
        & sample["mass_msun"].isna()
        & sample["teff_k"].notna()
    )

    for idx in sample.index[need]:
        row = sample.loc[idx]
        dr2 = row.get("gaia_dr2")
        dr3 = row.get("gaia_dr3")

        match = pd.DataFrame()
        if pd.notna(dr2):
            match = mist[mist["gaia_dr2"].astype(str) == str(dr2)]
        if match.empty and pd.notna(dr3):
            match = mist[mist["gaia_dr3"].astype(str) == str(dr3)]

        if match.empty:
            continue

        m = match.iloc[0]
        sample.at[idx, "mass_msun"] = m["mass_msun_mist"]
        sample.at[idx, "mass_unc_msun"] = m["mass_unc_msun_mist"]
        sample.at[idx, "mass_source"] = "mist_isochrone"
        if pd.isna(row.get("feh")):
            sample.at[idx, "feh"] = m["feh_adopted"]

    n_filled = (sample["mass_source"] == "mist_isochrone").sum()
    print(f"  Filled {n_filled} cluster stars with MIST masses.")
    return sample


# ---------------------------------------------------------------------------
# Cross-catalog duplicate flagging.
# ---------------------------------------------------------------------------

def _flag_cross_catalog_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mark Gaia IDs (DR2 *or* DR3) or KIC IDs that appear in more than one catalog.

    Duplicate rows are kept so downstream analysis can pick a preferred
    source per star rather than having the choice baked in here.
    """
    df = df.copy()
    flag = pd.Series(False, index=df.index)

    for col in ("gaia_dr2", "gaia_dr3", "kic"):
        ids = df[col].fillna("")
        non_empty = ids != ""
        cat_per_id = (df.loc[non_empty]
                        .assign(_id=ids[non_empty])
                        .groupby("_id")["source_catalog"].nunique())
        dup_ids = set(cat_per_id[cat_per_id > 1].index)
        flag |= ids.isin(dup_ids) & non_empty

    df["is_cross_catalog_duplicate"] = flag
    return df


# ---------------------------------------------------------------------------
# Summary reporting.
# ---------------------------------------------------------------------------

def _print_summary(sample: pd.DataFrame) -> None:
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}  "
          f"({len(sample)} rows, {len(sample.columns)} cols)")
    print()

    print("Per-source counts:")
    for src, n in sample["source_catalog"].value_counts().sort_index().items():
        print(f"  {src:<22s}  {n:>5d}")
    print()

    cluster_stars = sample[sample["cluster"].notna()]
    field_stars = sample[sample["cluster"].isna()]
    print(f"Cluster stars: {len(cluster_stars)}  |  "
          f"Field stars: {len(field_stars)}")
    print()

    if len(cluster_stars):
        print("Per-cluster counts (age-ordered):")
        cluster_order = (cluster_stars.groupby("cluster")["cluster_age_gyr"]
                                      .first().sort_values().index)
        width = max(len(c) for c in cluster_order)
        for cluster in cluster_order:
            sub = cluster_stars[cluster_stars["cluster"] == cluster]
            age = sub["cluster_age_gyr"].iloc[0]
            print(f"  {cluster:<{width}s}  {age:>5.3f} Gyr  n={len(sub):>5d}  "
                  f"({sub['teff_k'].notna().sum()} with Teff, "
                  f"{sub['prot_d'].notna().sum()} with Prot)")
        print()

    print("Teff source breakdown:")
    for src, n in sample["teff_source"].value_counts(dropna=False).items():
        print(f"  {src!s:<16s}  {n:>5d}")
    print()

    dup = int(sample["is_cross_catalog_duplicate"].sum())
    print(f"Rows flagged as cross-catalog duplicates: {dup}")

    # García / Hall overlap report.
    garcia = sample[sample["source_catalog"] == "garcia_2014"]
    hall = sample[sample["source_catalog"] == "hall_2021"]
    if len(garcia) and len(hall):
        garcia_kics = set(garcia["kic"].dropna())
        hall_kics = set(hall["kic"].dropna())
        overlap = garcia_kics & hall_kics
        print(f"García–Hall KIC overlap: {len(overlap)} stars "
              f"(García-only: {len(garcia_kics - hall_kics)}, "
              f"Hall-only: {len(hall_kics - garcia_kics)})")
    teff = sample["teff_k"]
    prot = sample["prot_d"]
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(N={prot.notna().sum()})")
    print()

    print("Prot source breakdown:")
    for src, n in sample["prot_source"].value_counts(dropna=False).items():
        print(f"  {src!s:<32s}  {n:>5d}")
    print()

    mass = sample["mass_msun"]
    print(f"Stars with mass_msun: {mass.notna().sum()}")
    if "mass_source" in sample.columns:
        for src, n in sample["mass_source"].value_counts(dropna=False).items():
            label = src if pd.notna(src) else "(no mass)"
            print(f"  {label:<20s}  {n:>5d}")
    print(f"Stars with feh:       {sample['feh'].notna().sum()}")
    print(f"Stars with logg:      {sample['logg'].notna().sum()}")
    print(f"Stars with radius:    {sample['radius_rsun'].notna().sum()}")
    print()

    # Age histogram in 1-Gyr bins from 0 to 14 Gyr.
    age = pd.to_numeric(sample["age_gyr"], errors="coerce")
    bins = range(0, 15)
    counts, edges = np.histogram(age.dropna().to_numpy(), bins=bins)
    print("Age histogram (1-Gyr bins, all sources):")
    for lo, hi, n in zip(edges[:-1], edges[1:], counts):
        bar = "#" * n
        print(f"  {lo:>2d}-{hi:>2d} Gyr  {n:>5d}  {bar}")
    print()

    # Stall-regime G-dwarf count.
    g_band = sample[(teff >= 5200) & (teff <= 5900)]
    old_g = g_band[pd.to_numeric(g_band["age_gyr"], errors="coerce") > 2]
    print(f"G dwarfs (5200-5900 K) with age > 2 Gyr: {len(old_g)}  "
          f"<-- stall-regime sample size")
    by_src = old_g["age_source"].value_counts()
    for src, n in by_src.items():
        print(f"  {src:<30s}  {n:>4d}")
    old_g_modeling = old_g[old_g["prot_d"].notna() & old_g["mass_msun"].notna()]
    print(f"\nModeling-ready (age>2, G-dwarf, non-null Prot AND mass): "
          f"{len(old_g_modeling)}")
    for src, n in old_g_modeling["age_source"].value_counts().items():
        print(f"  {src:<30s}  {n:>4d}")


# ---------------------------------------------------------------------------

def main() -> int:
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for slug, loader in LOADERS.items():
        try:
            frames.append(loader())
        except FileNotFoundError:
            missing.append(slug)
    if not frames:
        print("[error] no raw catalogs found. Run scripts/fetch_*.py first.",
              file=sys.stderr)
        return 1
    if missing:
        print(f"[warn] skipping catalogs without raw inputs: {', '.join(missing)}",
              file=sys.stderr)

    sample = pd.concat(frames, ignore_index=True)
    sample = _derive_missing_teff(sample)
    sample = _populate_age_columns(sample)
    sample = _merge_mist_masses(sample)
    sample = _flag_cross_catalog_duplicates(sample)

    # Numeric coercion for final output (avoids object dtypes from _empty_frame).
    for col in ("cluster_age_gyr", "teff_k", "bp_rp_0", "prot_d", "ra_deg",
                "dec_deg", "age_gyr", "age_unc_gyr",
                "mass_msun", "mass_unc_msun", "feh", "logg", "radius_rsun"):
        sample[col] = pd.to_numeric(sample[col], errors="coerce")

    sample = sample.sort_values(
        ["age_gyr", "cluster", "source_catalog", "teff_k"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False)

    _print_summary(sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
