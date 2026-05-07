#!/usr/bin/env python3
"""Fetch Silva Aguirre et al. 2017 (ApJ 835, 173) — the Kepler LEGACY
asteroseismic sample: 66 main-sequence and subgiant stars with
high-precision ages, masses, radii, and surface parameters from
BASTA grid modelling.

Primary path: VizieR TAP, `J/ApJ/835/173/table3` (observables) joined
with `J/ApJ/835/173/table4` (BASTA model results) on KIC.
Fallback:     LEGACY subset (source='L') from the Hall et al. 2021
              companion repo (ojhall94/malatium), which contains the
              same parameters re-assembled from Silva Aguirre 2017.

Output: data/raw/silva_aguirre_2017.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import VIZIER_TAP_URL, decode_bytes, write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "silva_aguirre_2017.csv"

MIRROR_URL = (
    "https://raw.githubusercontent.com/ojhall94/malatium/master/"
    "data/malatium.csv"
)

EXPECTED_ROWS = 66
EXPECTED_KEY_COLUMNS = {"KIC", "Teff", "age", "modmass", "feh", "modlogg", "modrad"}

ADQL_OBS = 'SELECT * FROM "J/ApJ/835/173/table3"'
ADQL_MOD = """SELECT KIC, Mass AS modmass, "E_Mass" AS upmodmass,
       "e_Mass" AS lomodmass, Rad AS modrad, "E_Rad" AS upmodrad,
       "e_Rad" AS lomodrad, "log(g)" AS modlogg, "E_log(g)" AS upmodlogg,
       "e_log(g)" AS lomodlogg, Age AS age, "E_Age" AS upage,
       "e_Age" AS loage
FROM "J/ApJ/835/173/table4"
WHERE Pipe = 'BASTA'"""


def _fetch_tap() -> pd.DataFrame:
    from astroquery.utils.tap.core import TapPlus

    tap = TapPlus(url=VIZIER_TAP_URL)
    obs = tap.launch_job_async(ADQL_OBS).get_results().to_pandas()
    mod = tap.launch_job_async(ADQL_MOD).get_results().to_pandas()
    obs = decode_bytes(obs)
    mod = decode_bytes(mod)
    return obs.merge(mod, on="KIC", how="inner")


def _fetch_mirror() -> pd.DataFrame:
    with urllib.request.urlopen(MIRROR_URL, timeout=60) as resp:
        buf = io.BytesIO(resp.read())
    full = pd.read_csv(buf)
    legacy = full[full["source"] == "L"].copy().reset_index(drop=True)
    legacy = legacy.drop(columns=["Unnamed: 0", "source"], errors="ignore")
    return legacy


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
    if len(df) != EXPECTED_ROWS:
        print(f"[warn] expected {EXPECTED_ROWS} rows, got {len(df)}",
              file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    age = pd.to_numeric(df.get("age"), errors="coerce")
    teff = pd.to_numeric(df.get("Teff"), errors="coerce")
    mass = pd.to_numeric(df.get("modmass"), errors="coerce")
    print(f"Age  range [Gyr]:   {age.min():.3f} .. {age.max():.3f} "
          f"(median {age.median():.3f})")
    print(f"Teff range [K]:     {teff.min():.0f} .. {teff.max():.0f}")
    print(f"Mass range [Msun]:  {mass.min():.3f} .. {mass.max():.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirror", action="store_true")
    args = ap.parse_args()

    df, source = _fetch(args.mirror)
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
