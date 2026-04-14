#!/usr/bin/env python3
"""Harmonize all raw rotation catalogs into a single analysis-ready table.

Reads everything in ``data/raw/*.csv`` that this script knows about, maps
cluster names to canonical labels + literature ages, keeps Teff and Prot as
the scientific payload, and writes ``data/processed/gyro_sample.csv`` with
the schema documented in ``README.md``.

Run the fetchers first:
    python scripts/fetch_curtis_2020.py
    python scripts/fetch_godoy_rivera_2021.py
    python scripts/fetch_curtis_2019_psceri.py
    python scripts/build_gyro_sample.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
OUT = REPO_ROOT / "data" / "processed" / "gyro_sample.csv"

# Canonical cluster name -> adopted age [Gyr]. Ages are taken from the
# original papers where possible; see docstring references in README.
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
}

# Raw cluster label (as it appears in each source catalog) -> canonical label.
CLUSTER_ALIASES: dict[str, str] = {
    # Curtis 2020 Table 5 already uses canonical names; listed for clarity.
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


def _norm_cluster(raw: str) -> str:
    key = str(raw).strip()
    return CLUSTER_ALIASES.get(key, key)


def _load_curtis_2020() -> pd.DataFrame:
    path = RAW / "curtis_2020_table5.csv"
    df = pd.read_csv(path)
    out = pd.DataFrame({
        "source_catalog": "curtis_2020",
        "cluster": df["Cluster"].map(_norm_cluster),
        "cluster_age_gyr": pd.to_numeric(df["Age"], errors="coerce"),
        "gaia_dr2": df["GaiaDR2"].astype("Int64").astype("string"),
        "teff_k": pd.to_numeric(df["Teff"], errors="coerce"),
        "prot_d": pd.to_numeric(df["Prot"], errors="coerce"),
        "ra_deg": pd.to_numeric(df["RA_ICRS"], errors="coerce"),
        "dec_deg": pd.to_numeric(df["DE_ICRS"], errors="coerce"),
    })
    return out


def _load_godoy_rivera_2021() -> pd.DataFrame:
    path = RAW / "godoy_rivera_2021.csv"
    df = pd.read_csv(path)
    cluster = df["Cluster"].map(_norm_cluster)
    out = pd.DataFrame({
        "source_catalog": "godoy_rivera_2021",
        "cluster": cluster,
        "cluster_age_gyr": cluster.map(CLUSTER_AGE_GYR),
        "gaia_dr2": df["GaiaDR2"].astype("Int64").astype("string"),
        "teff_k": pd.to_numeric(df["Teff"], errors="coerce"),
        "prot_d": pd.to_numeric(df["Period"], errors="coerce"),
        "ra_deg": pd.to_numeric(df["RA_ICRS"], errors="coerce"),
        "dec_deg": pd.to_numeric(df["DE_ICRS"], errors="coerce"),
    })
    return out


def _load_curtis_2019_psceri() -> pd.DataFrame:
    path = RAW / "curtis_2019_psceri.csv"
    df = pd.read_csv(path)
    # Source column holds the Gaia DR2 ID as a string.
    out = pd.DataFrame({
        "source_catalog": "curtis_2019_psceri",
        "cluster": "Pisces-Eridanus",
        "cluster_age_gyr": CLUSTER_AGE_GYR["Pisces-Eridanus"],
        "gaia_dr2": df["Source"].astype("string").str.strip(),
        "teff_k": pd.to_numeric(df["Teff"], errors="coerce"),
        "prot_d": pd.to_numeric(df["Prot"], errors="coerce"),
        "ra_deg": pd.NA,
        "dec_deg": pd.NA,
    })
    return out


LOADERS = {
    "curtis_2020": _load_curtis_2020,
    "godoy_rivera_2021": _load_godoy_rivera_2021,
    "curtis_2019_psceri": _load_curtis_2019_psceri,
}


def _flag_cross_catalog_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Mark Gaia DR2 IDs that appear in more than one source catalog.

    We keep every row (different catalogs may disagree on Prot/Teff and
    that disagreement is scientifically interesting), but add a column so
    downstream code can pick a single "preferred" row per star.
    """
    gaia = df["gaia_dr2"].fillna("")
    catalog_count = (
        df.assign(_g=gaia)
          .query("_g != ''")
          .groupby("_g")["source_catalog"]
          .nunique()
    )
    dup_ids = set(catalog_count[catalog_count > 1].index)
    df = df.copy()
    df["is_cross_catalog_duplicate"] = gaia.isin(dup_ids)
    return df


def main() -> int:
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for slug, loader in LOADERS.items():
        try:
            frames.append(loader())
        except FileNotFoundError:
            missing.append(slug)
    if missing:
        print(f"[error] missing raw inputs for: {', '.join(missing)}", file=sys.stderr)
        print("Run the corresponding scripts/fetch_*.py first.", file=sys.stderr)
        return 1

    sample = pd.concat(frames, ignore_index=True)
    sample = _flag_cross_catalog_duplicates(sample)
    sample = sample.sort_values(
        ["cluster_age_gyr", "cluster", "source_catalog", "teff_k"],
        kind="mergesort",
    ).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False)

    print(f"Wrote {OUT.relative_to(REPO_ROOT)}  "
          f"({len(sample)} rows, {len(sample.columns)} cols)")
    print()

    print("Per-source counts:")
    for src, n in sample["source_catalog"].value_counts().sort_index().items():
        print(f"  {src:<22s}  {n:>5d}")
    print()

    print("Per-cluster counts (age-ordered):")
    cluster_order = (sample.groupby("cluster")["cluster_age_gyr"]
                           .first().sort_values().index)
    width = max(len(c) for c in cluster_order)
    for cluster in cluster_order:
        sub = sample[sample["cluster"] == cluster]
        age = sub["cluster_age_gyr"].iloc[0]
        print(f"  {cluster:<{width}s}  {age:>5.3f} Gyr  n={len(sub):>5d}  "
              f"({sub['teff_k'].notna().sum()} with Teff, "
              f"{sub['prot_d'].notna().sum()} with Prot)")
    print()

    dup = int(sample["is_cross_catalog_duplicate"].sum())
    print(f"Rows sharing a Gaia DR2 ID across catalogs: {dup}")
    teff = sample["teff_k"]
    prot = sample["prot_d"]
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(N={prot.notna().sum()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
