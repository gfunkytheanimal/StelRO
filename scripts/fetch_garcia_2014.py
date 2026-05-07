#!/usr/bin/env python3
"""Fetch García et al. 2014 (A&A 572, A34) — surface rotation periods for
~293 Kepler solar-like pulsating stars measured via photometric spot
modulation (autocorrelation + wavelet analysis).

The parent sample is 540 stars from Chaplin et al. 2014 (ApJS 210, 1),
of which 310 showed reliable surface modulation. After quality filtering
by Ruth Angus's assembly, 293 stars have both Prot and asteroseismic ages.

Primary path: VizieR catalog J/A+A/572/A34 (blocked in this environment).
Fallback:     RuthAngus/Gyro repository ``data/garcia_irfm.txt`` — a
              compiled table joining García Prot with Chaplin ages.
              Only the KIC and Prot columns are extracted here; ages and
              stellar parameters come from ``fetch_chaplin_2014.py``.

Output: data/raw/garcia_2014.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "garcia_2014.csv"

MIRROR_URL = (
    "https://raw.githubusercontent.com/RuthAngus/Gyro/master/"
    "data/garcia_irfm.txt"
)

EXPECTED_KEY_COLUMNS = {"KIC", "Prot", "Prot_err"}


def _fetch_mirror() -> pd.DataFrame:
    """Extract García rotation periods from the Angus compilation.

    The garcia_irfm.txt file has 14 rows (transposed numpy arrays):
    KIC, Teff, Teff_err, age, age_errp, age_errm, Prot, Prot_err,
    logg, logg_errp, logg_errm, feh, feh_err, flag.

    We only take KIC, Prot, and Prot_err — the Teff column has known
    data-quality issues (49 rows have [Fe/H] instead of Teff due to
    column misalignment in the assembly script). Ages and stellar
    parameters come from Chaplin 2014 directly.
    """
    with urllib.request.urlopen(MIRROR_URL, timeout=60) as resp:
        data = np.loadtxt(io.BytesIO(resp.read()))
    all_cols = [
        "KIC", "Teff", "Teff_err", "age", "age_errp", "age_errm",
        "Prot", "Prot_err", "logg", "logg_errp", "logg_errm",
        "feh", "feh_err", "flag",
    ]
    df = pd.DataFrame(data.T, columns=all_cols)
    df["KIC"] = df["KIC"].astype(int)
    return df[["KIC", "Prot", "Prot_err"]].copy()


def _fetch_tap() -> pd.DataFrame:
    from astroquery.utils.tap.core import TapPlus
    from _vizier_fetch import VIZIER_TAP_URL, decode_bytes

    tap = TapPlus(url=VIZIER_TAP_URL)
    job = tap.launch_job_async('SELECT * FROM "J/A+A/572/A34/table1"')
    df = decode_bytes(job.get_results().to_pandas())
    rename = {}
    for col in df.columns:
        cl = col.lower()
        if "kic" in cl or cl == "kid":
            rename[col] = "KIC"
        elif "prot" in cl or cl == "per":
            rename[col] = "Prot"
        elif "e_prot" in cl or "e_per" in cl:
            rename[col] = "Prot_err"
    df = df.rename(columns=rename)
    if "KIC" in df.columns and "Prot" in df.columns:
        df["KIC"] = df["KIC"].astype(int)
        return df
    return df


def _fetch(use_mirror: bool) -> tuple[pd.DataFrame, str]:
    if use_mirror:
        return _fetch_mirror(), "github-mirror"
    try:
        return _fetch_tap(), "vizier-tap"
    except Exception as err:
        print(f"[warn] TAP query failed ({type(err).__name__}: {err}); "
              "falling back to mirror.", file=sys.stderr)
        return _fetch_mirror(), "github-mirror"


def _validate(df: pd.DataFrame) -> None:
    missing = EXPECTED_KEY_COLUMNS - set(df.columns)
    if missing:
        print(f"[warn] expected columns not found: {missing}", file=sys.stderr)
    if len(df) < 280 or len(df) > 320:
        print(f"[warn] expected ~293-310 rows, got {len(df)}", file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    prot = pd.to_numeric(df["Prot"], errors="coerce")
    print(f"Prot range [d]: {prot.min():.2f} .. {prot.max():.2f} "
          f"(median {prot.median():.2f}, N={prot.notna().sum()})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true",
                    help="skip TAP and fetch the GitHub mirror directly")
    args = ap.parse_args()

    df, source = _fetch(args.mirror)
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
