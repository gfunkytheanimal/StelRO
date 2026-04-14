#!/usr/bin/env python3
"""Fetch Curtis et al. 2019 (AJ 158, 77) — rotation periods for the
Pisces-Eridanus stellar stream (~120 Myr), Table 2 (101 rows).

Primary path: VizieR TAP catalog `J/AJ/158/77`, table `table2`.
Fallback:     FITS mirror in lgbouma/gyro-interp.

Output: data/raw/curtis_2019_psceri.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import CatalogSpec, decode_bytes, fetch_catalog, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "curtis_2019_psceri.csv"

SPEC = CatalogSpec(
    name="curtis_2019_psceri",
    vizier_table="J/AJ/158/77/table2",
    mirror_url=(
        "https://raw.githubusercontent.com/lgbouma/gyro-interp/main/"
        "gyrointerp/data/literature/Curtis_2019_PscEri_table2_101rows.fits"
    ),
)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    teff = pd.to_numeric(df.get("Teff"), errors="coerce")
    prot = pd.to_numeric(df.get("Prot"), errors="coerce")
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(median {teff.median():.1f}, N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f}, N={prot.notna().sum()})")
    if "Note" in df.columns:
        print()
        print("Temperature-class tags (Note):")
        for tag, n in df["Note"].value_counts().sort_index().items():
            print(f"  {tag or '(none)':<10s}  {n:>4d}")


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
