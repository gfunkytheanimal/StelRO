#!/usr/bin/env python3
"""Fetch asteroseismic rotation periods from the literature for the LEGACY
sample — aggregated by Hall et al. 2021 in the malatium companion repo.

The ``literature_seismo.csv`` file contains seismic Prot from four
independent splitting analyses of Kepler asteroseismic targets:
  C15 = Corsaro et al. 2015 (A&A 579, A83)
  D16 = Davies et al. 2015 (MNRAS 456, 2183)
  N15 = Nielsen et al. 2015 (MNRAS 452, 2654)
  B18 = Benomar et al. 2018 (Science 361, 1231)

These are NOT the same as the Hall 2021 ``P`` column (which is an
ensemble average); these are per-pipeline values useful for uncertainty
cross-checking.

Source: ojhall94/malatium companion repo ``data/literature_seismo.csv``.
Output: data/raw/literature_seismo.csv
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
OUT_CSV = REPO_ROOT / "data" / "raw" / "literature_seismo.csv"

MIRROR_URL = (
    "https://raw.githubusercontent.com/ojhall94/malatium/master/"
    "data/literature_seismo.csv"
)

EXPECTED_ROWS = 94
EXPECTED_KEY_COLUMNS = {"KIC", "B18_P_rot"}


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
    if len(df) != EXPECTED_ROWS:
        print(f"[warn] expected {EXPECTED_ROWS} rows, got {len(df)}",
              file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    for col in ["C15_P_rot", "D16_P_rot", "N15_P_rot", "B18_P_rot"]:
        vals = pd.to_numeric(df.get(col), errors="coerce")
        n = vals.notna().sum()
        if n:
            print(f"  {col}: {n} stars, range {vals.min():.2f} .. {vals.max():.2f} d")
        else:
            print(f"  {col}: 0 stars")


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
