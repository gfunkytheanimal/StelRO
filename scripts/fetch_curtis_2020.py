#!/usr/bin/env python3
"""Fetch Curtis et al. 2020 (ApJ 904, 140) Table 5 via the VizieR TAP service.

Primary path: query VizieR TAP (catalog J/ApJ/904/140, table `table5`).
Fallback path: if TAP is unreachable (e.g. in a sandbox that blocks CDS),
pass `--mirror` to pull the identical 923-row table from the
lgbouma/gyro-interp GitHub mirror (Curtis_2020_t5_composite_923_rows.fits).

Output: data/raw/curtis_2020_table5.csv
Summary: per-cluster counts plus global Teff and Prot ranges.
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

VIZIER_TAP_URL = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap"
VIZIER_TABLE = '"J/ApJ/904/140/table5"'
MIRROR_URL = (
    "https://raw.githubusercontent.com/lgbouma/gyro-interp/main/"
    "gyrointerp/data/literature/Curtis_2020_t5_composite_923_rows.fits"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "curtis_2020_table5.csv"


def fetch_via_tap() -> pd.DataFrame:
    """Query VizieR TAP for all rows of J/ApJ/904/140 table 5."""
    from astroquery.utils.tap.core import TapPlus

    tap = TapPlus(url=VIZIER_TAP_URL)
    job = tap.launch_job_async(f"SELECT * FROM {VIZIER_TABLE}")
    table = job.get_results()
    return table.to_pandas()


def fetch_via_mirror() -> pd.DataFrame:
    """Download the FITS mirror of Table 5 and return it as a DataFrame."""
    from astropy.table import Table

    with urllib.request.urlopen(MIRROR_URL, timeout=60) as resp:
        buf = io.BytesIO(resp.read())
    return Table.read(buf, format="fits").to_pandas()


def load_table(use_mirror: bool) -> tuple[pd.DataFrame, str]:
    if use_mirror:
        return fetch_via_mirror(), "github-mirror"
    try:
        return fetch_via_tap(), "vizier-tap"
    except (urllib.error.URLError, ConnectionError, OSError) as err:
        print(f"[warn] VizieR TAP unreachable ({err}); falling back to mirror.",
              file=sys.stderr)
        return fetch_via_mirror(), "github-mirror"
    except Exception as err:  # astroquery wraps errors; catch broadly then retry
        print(f"[warn] TAP query failed ({type(err).__name__}: {err}); "
              "falling back to mirror.", file=sys.stderr)
        return fetch_via_mirror(), "github-mirror"


def decode_bytes(df: pd.DataFrame) -> pd.DataFrame:
    """FITS/VOTable string columns often come back as bytes; normalize to str."""
    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna().head(1)
        if len(sample) and isinstance(sample.iloc[0], bytes):
            df[col] = df[col].str.decode("utf-8", errors="replace")
    return df


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    print()
    print("Per-cluster counts:")
    counts = df["Cluster"].value_counts().sort_index()
    width = max(len(str(c)) for c in counts.index)
    for cluster, n in counts.items():
        print(f"  {cluster:<{width}}  {n:>4d}")
    print()
    teff = pd.to_numeric(df["Teff"], errors="coerce")
    prot = pd.to_numeric(df["Prot"], errors="coerce")
    print(f"Teff range [K]: {teff.min():.1f} .. {teff.max():.1f} "
          f"(median {teff.median():.1f}, N={teff.notna().sum()})")
    print(f"Prot range [d]: {prot.min():.3f} .. {prot.max():.3f} "
          f"(median {prot.median():.3f}, N={prot.notna().sum()})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true",
                    help="skip TAP and fetch the FITS mirror directly")
    args = ap.parse_args()

    df, source = load_table(use_mirror=args.mirror)
    df = decode_bytes(df)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"Source: {source}")
    print(f"Wrote:  {OUT_CSV.relative_to(REPO_ROOT)}  ({len(df)} rows, "
          f"{len(df.columns)} cols)")
    print()
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
