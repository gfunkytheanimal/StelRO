#!/usr/bin/env python3
"""Fetch surface rotation periods from photometric spot modulation for the
LEGACY / Hall 2021 asteroseismic sample.

The ``lit_spot_rots.csv`` file (from the malatium companion repo) contains
surface Prot from multiple photometric analyses:
  McQP  = McQuillan et al. 2014 (ApJS 211, 24)   — ACF-based, Kepler Q1-Q14
  SP    = Santos et al. (2019 or 2021)
  NP    = Nielsen et al. 2013 (A&A 557, L10)      — wavelet analysis
  jvsP  = van Saders & Pinsonneault 2013 / Ceillier et al.
  GP    = García et al. 2014 (A&A 572, A34)       — composite S_ph + ACF

These surface periods complement the asteroseismic Prot (from rotational
frequency splitting) and enable comparison of surface vs. core rotation.

Source: ojhall94/malatium companion repo ``data/lit_spot_rots.csv``.
Output: data/raw/lit_spot_rots.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import decode_bytes, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "lit_spot_rots.csv"

MIRROR_URL = (
    "https://raw.githubusercontent.com/ojhall94/malatium/master/"
    "data/lit_spot_rots.csv"
)

EXPECTED_KEY_COLUMNS = {"KIC", "McQP", "GP"}


def _fetch() -> pd.DataFrame:
    with urllib.request.urlopen(MIRROR_URL, timeout=60) as resp:
        buf = io.BytesIO(resp.read())
    df = pd.read_csv(buf)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    return df


def _validate(df: pd.DataFrame) -> None:
    missing = EXPECTED_KEY_COLUMNS - set(df.columns)
    if missing:
        print(f"[warn] expected columns not found: {missing}", file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    for col in ["McQP", "SP", "NP", "jvsP", "GP"]:
        vals = pd.to_numeric(df.get(col), errors="coerce")
        n = vals.notna().sum()
        if n:
            print(f"  {col}: {n} stars, range {vals.min():.2f} .. {vals.max():.2f} d")
        else:
            print(f"  {col}: 0 stars")
    flag = df.get("Flag")
    if flag is not None:
        print(f"\nFlag=1 (any spot Prot): {(flag == 1).sum()}")
        print(f"Flag=0 (no spot Prot):  {(flag == 0).sum()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()

    df = _fetch()
    df = decode_bytes(df)
    _validate(df)
    write_csv(df, OUT_CSV)
    print(f"Wrote:  {OUT_CSV.relative_to(REPO_ROOT)}  "
          f"({len(df)} rows, {len(df.columns)} cols)")
    print()
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
