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
    "ra_deg",
    "dec_deg",
    # Age columns — populated for all rows in the final output.
    "age_gyr",           # adopted age (cluster_age_gyr for cluster stars, asteroseismic for field)
    "age_source",        # 'cluster' | 'asteroseismic_hall_2021' | (future values)
    "age_unc_gyr",       # symmetric uncertainty in age (null for cluster stars)
]

# TODO: Phase 2 — add Kepler LEGACY asteroseismic sample (Lund et al. 2017 /
# Silva Aguirre et al. 2017, ~66 dwarfs with high-precision ages but no
# published Prot — needs cross-match with McQuillan 2014). The age_source
# value "asteroseismic_legacy" is reserved for this addition.


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
    # Asteroseismic individual ages.
    out["age_gyr"] = pd.to_numeric(df["age"], errors="coerce")
    out["age_source"] = "asteroseismic_hall_2021"
    lo = pd.to_numeric(df["loage"], errors="coerce")
    up = pd.to_numeric(df["upage"], errors="coerce")
    out["age_unc_gyr"] = (lo + up) / 2.0
    return out


LOADERS = {
    "curtis_2020":          _load_curtis_2020,
    "curtis_2020_rup147":   _load_curtis_2020_rup147,
    "godoy_rivera_2021":    _load_godoy_rivera_2021,
    "curtis_2019_psceri":   _load_curtis_2019_psceri,
    "gruner_2023_m67":      _load_gruner_2023_m67,
    "hall_2021":            _load_hall_2021,
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
# Cross-catalog duplicate flagging.
# ---------------------------------------------------------------------------

def _flag_cross_catalog_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mark Gaia IDs (DR2 *or* DR3) that appear in more than one catalog.

    Duplicate rows are kept so downstream analysis can pick a preferred
    source per star rather than having the choice baked in here.
    """
    df = df.copy()
    flag = pd.Series(False, index=df.index)

    for col in ("gaia_dr2", "gaia_dr3"):
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
    print(f"Rows sharing a Gaia DR2/DR3 ID across catalogs: {dup}")
    teff = sample["teff_k"]
    prot = sample["prot_d"]
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(N={prot.notna().sum()})")
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
    sample = _flag_cross_catalog_duplicates(sample)

    # Numeric coercion for final output (avoids object dtypes from _empty_frame).
    for col in ("cluster_age_gyr", "teff_k", "bp_rp_0", "prot_d", "ra_deg",
                "dec_deg", "age_gyr", "age_unc_gyr"):
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
