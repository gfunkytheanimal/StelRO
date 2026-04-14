#!/usr/bin/env python3
"""Fetch Godoy-Rivera, Pinsonneault & Rebull 2021 (ApJS 257, 46) —
a homogeneous Gaia-DR2 based rotation sample across seven open clusters
(NGC 2547, NGC 2516, M50, M37, Pleiades, Praesepe, NGC 6811; 3492 rows).

Primary path: VizieR TAP catalog `J/ApJS/257/46`, table `table2`.
Fallback:     FITS mirror in lgbouma/gyro-interp.

Output: data/raw/godoy_rivera_2021.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import CatalogSpec, decode_bytes, fetch_catalog, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "godoy_rivera_2021.csv"

SPEC = CatalogSpec(
    name="godoy_rivera_2021",
    vizier_table="J/ApJS/257/46/table2",
    mirror_url=(
        "https://raw.githubusercontent.com/lgbouma/gyro-interp/main/"
        "gyrointerp/data/literature/"
        "Godoy-Rivera_2021_M37_M50_NGC2516_NGC2547_NGC6811_Pleiades_Praesepe.fits"
    ),
)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    print()
    print("Per-cluster counts:")
    counts = df["Cluster"].value_counts().sort_index()
    width = max(len(str(c)) for c in counts.index)
    for cluster, n in counts.items():
        print(f"  {cluster:<{width}}  {n:>4d}")
    print()
    teff = pd.to_numeric(df.get("Teff"), errors="coerce")
    prot = pd.to_numeric(df.get("Period"), errors="coerce")
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(median {teff.median():.1f}, N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f}, N={prot.notna().sum()})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true",
                    help="skip TAP and fetch the FITS mirror directly")
    args = ap.parse_args()

    df, source = fetch_catalog(SPEC, use_mirror=args.mirror)
    df = decode_bytes(df)
    write_csv(df, OUT_CSV)
    print(f"Source: {source}")
    print(f"Wrote:  {OUT_CSV.relative_to(REPO_ROOT)}  "
          f"({len(df)} rows, {len(df.columns)} cols)")
    print()
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
