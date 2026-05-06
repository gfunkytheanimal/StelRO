#!/usr/bin/env python3
"""Fetch Hall et al. 2021 (Nature Astronomy 5, 707) Table 1 — asteroseismic
rotation rates for 94 Kepler main-sequence and subgiant stars with seismic
ages, the largest seismic-rotation catalog on the main sequence to date.

IMPORTANT: the rotation period column `P` in this catalog is derived from
asteroseismic rotational frequency splitting (not surface spot modulation).
For main-sequence solar-type stars this is approximately the surface
rotation rate; for subgiants (hrclass="SG") core and surface rates can
decouple.

Primary path: VizieR TAP catalog `J/NatAs/5/707`, table `table1`.
Fallback:     author's GitHub repo (ojhall94/halletal2021).

Output: data/raw/hall_2021.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import CatalogSpec, decode_bytes, fetch_catalog, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "hall_2021.csv"

SPEC = CatalogSpec(
    name="hall_2021",
    vizier_table="J/other/NatAs/5.707/table1",
    mirror_url=(
        "https://raw.githubusercontent.com/ojhall94/halletal2021/main/"
        "data/table1.csv"
    ),
    mirror_format="csv",
)

EXPECTED_ROWS = 94
EXPECTED_KEY_COLUMNS = {"KIC", "Teff", "age", "P", "modmass", "feh", "flag"}


def _validate(df: pd.DataFrame) -> None:
    """Surface unexpected schema changes rather than silently coercing."""
    missing = EXPECTED_KEY_COLUMNS - set(df.columns)
    if missing:
        print(f"[warn] expected columns not found: {missing}", file=sys.stderr)
    if len(df) != EXPECTED_ROWS:
        print(f"[warn] expected {EXPECTED_ROWS} rows, got {len(df)}",
              file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    age = pd.to_numeric(df.get("age"), errors="coerce")
    prot = pd.to_numeric(df.get("P"), errors="coerce")
    teff = pd.to_numeric(df.get("Teff"), errors="coerce")
    print(f"Age  range [Gyr]: {age.min():.3f} .. {age.max():.3f} "
          f"(median {age.median():.3f}, N={age.notna().sum()})")
    print(f"Prot range [d]:   {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f}, N={prot.notna().sum()})")
    print(f"Teff range [K]:   {teff.min():.0f} .. {teff.max():.0f} "
          f"(median {teff.median():.0f}, N={teff.notna().sum()})")
    print()
    if "hrclass" in df.columns:
        print("HR class breakdown:")
        for cls, n in df["hrclass"].value_counts().sort_index().items():
            print(f"  {cls:<4s}  {n:>3d}")
    if "flag" in df.columns:
        print()
        print("Quality flag breakdown (0 = good):")
        for flag, n in df["flag"].value_counts().sort_index().items():
            print(f"  flag={flag}  {n:>3d}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true",
                    help="skip TAP and fetch the GitHub mirror directly")
    args = ap.parse_args()

    df, source = fetch_catalog(SPEC, use_mirror=args.mirror)
    df = decode_bytes(df)
    _validate(df)
    write_csv(df, OUT_CSV)
    print(f"Source: {source}")
    print(f"Wrote:  {OUT_CSV.relative_to(REPO_ROOT)}  "
          f"({len(df)} rows, {len(df.columns)} cols)")
    print()
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
