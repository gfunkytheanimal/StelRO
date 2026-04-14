#!/usr/bin/env python3
"""Fetch Gruner, Barnes & Weingrill 2023 (A&A 675, A180) Table C2 —
47 rotation periods for G/K dwarfs in the old open cluster M67 (~4 Gyr).

Notable for this workspace: M67 extends the age baseline from the
current 2.7 Gyr (Ruprecht 147) ceiling out to ~4 Gyr, which is where
Skumanich and any asymptotic-ridge model diverge most strongly.

Caveats preserved by this fetcher (no massaging at this stage):
- IDs are Gaia DR3 (`dr3_source_id`), not DR2. The unifier carries both
  as separate columns.
- No Teff is published; (BP-RP)_0 colour is available and is the basis
  for a self-consistent Teff derivation in `build_gyro_sample.py`.

Primary path: VizieR TAP catalog `J/A+A/675/A180`, table `tablec2`.
Fallback:     CSV mirror in lgbouma/gyro-interp.

Output: data/raw/gruner_2023_m67.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import CatalogSpec, decode_bytes, fetch_catalog, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "gruner_2023_m67.csv"

SPEC = CatalogSpec(
    name="gruner_2023_m67",
    vizier_table="J/A+A/675/A180/tablec2",
    mirror_url=(
        "https://raw.githubusercontent.com/lgbouma/gyro-interp/main/"
        "gyrointerp/data/literature/Gruner_Barnes_Weingrill_2023_M67_tableC2.csv"
    ),
    mirror_format="csv",
)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    prot = pd.to_numeric(df.get("period"), errors="coerce")
    bprp = pd.to_numeric(df.get("(BP-RP)0"), errors="coerce")
    print(f"Prot range [d]:     {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f}, N={prot.notna().sum()})")
    print(f"(BP-RP)_0 range:    {bprp.min():.3f} .. {bprp.max():.3f} "
          f"(median {bprp.median():.3f}, N={bprp.notna().sum()})")
    print("Note: Teff is not published in this table; it will be derived "
          "from (BP-RP)_0 in build_gyro_sample.py.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true",
                    help="skip TAP and fetch the CSV mirror directly")
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
