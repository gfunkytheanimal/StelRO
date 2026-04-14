#!/usr/bin/env python3
"""Fetch Curtis et al. 2020 (ApJ 904, 140) **Table 1** — the full
Ruprecht 147 membership catalog with 440 rows, ~155 of which carry a
measured rotation period. This expands the Ruprecht 147 (2.7 Gyr)
rotator sample well beyond the 35 Rup-147 entries in Table 5 (the
composite).

Primary path: VizieR TAP catalog `J/ApJ/904/140`, table `table1`.
Fallback:     FITS mirror in lgbouma/gyro-interp.

Output: data/raw/curtis_2020_rup147.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import CatalogSpec, decode_bytes, fetch_catalog, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "curtis_2020_rup147.csv"

SPEC = CatalogSpec(
    name="curtis_2020_rup147",
    vizier_table="J/ApJ/904/140/table1",
    mirror_url=(
        "https://raw.githubusercontent.com/lgbouma/gyro-interp/main/"
        "gyrointerp/data/literature/Curtis_2020_t1_ruprecht147_440_rows.fits"
    ),
)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    teff = pd.to_numeric(df.get("Teff"), errors="coerce")
    prot_raw = pd.to_numeric(df.get("Prot"), errors="coerce")
    prot = prot_raw.where(prot_raw > 0)  # published table uses <=0 as flag
    print(f"Rows with Prot > 0:  {prot.notna().sum()}")
    print(f"Rows with Teff:      {teff.notna().sum()}")
    print(f"Teff range [K]:      {teff.min():.1f} .. {teff.max():.1f} "
          f"(median {teff.median():.1f})")
    print(f"Prot range [d]:      {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f})")


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
