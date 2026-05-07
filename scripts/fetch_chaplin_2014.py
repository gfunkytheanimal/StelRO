#!/usr/bin/env python3
"""Fetch Chaplin et al. 2014 (ApJS 210, 1) — asteroseismic fundamental
properties for ~518 solar-type Kepler stars.

Provides ages, masses, radii, log g for the parent sample from which
García et al. 2014 drew rotation periods. Two tables are parsed:

  Table 1 (observables): KIC, numax, Dnu, SDSS Teff, IRFM Teff, [Fe/H]
  Table 5 (IRFM properties): KIC, Mass, Radius, log g, Age (with errors)

Primary path: Machine-readable tables hosted in the RuthAngus/Gyro
              repository (ApJS91604R2tables.txt — the original Chaplin
              submission file).
VizieR:       J/ApJS/210/1 (blocked in this environment).

Output: data/raw/chaplin_2014.csv
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vizier_fetch import write_csv

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = REPO_ROOT / "data" / "raw" / "chaplin_2014.csv"

MIRROR_URL = (
    "https://raw.githubusercontent.com/RuthAngus/Gyro/master/"
    "data/ApJS91604R2tables.txt"
)

EXPECTED_KEY_COLUMNS = {"KIC", "IRFM_Teff", "feh", "mass_msun", "age_gyr"}


def _parse_table1(lines: list[str]) -> pd.DataFrame:
    """Parse Table 1 (observables) from the fixed-width Chaplin file."""
    rows = []
    for i in range(28, 559):
        line = lines[i]
        if not line.strip():
            continue
        try:
            kic = int(line[0:8].strip())
        except ValueError:
            continue
        def _flt(s: str) -> float | None:
            s = s.strip()
            return float(s) if s else None
        rows.append({
            "KIC": kic,
            "numax": _flt(line[9:13]),
            "e_numax": _flt(line[14:17]),
            "Dnu": _flt(line[18:23]),
            "e_Dnu": _flt(line[24:27]),
            "SDSS_Teff": _flt(line[28:32]),
            "e_SDSS_Teff": _flt(line[33:36]),
            "IRFM_Teff": _flt(line[37:41]),
            "e_IRFM_Teff": _flt(line[42:45]),
            "feh": _flt(line[46:51]),
            "e_feh": _flt(line[52:56]),
        })
    return pd.DataFrame(rows)


def _parse_table5(lines: list[str]) -> pd.DataFrame:
    """Parse Table 5 (IRFM stellar properties) from the Chaplin file."""
    rows = []
    for i in range(1251, 1780):
        line = lines[i]
        if not line.strip():
            continue
        try:
            kic = int(line[0:8].strip())
        except ValueError:
            continue
        def _flt(s: str) -> float | None:
            s = s.strip()
            return float(s) if s else None
        rows.append({
            "KIC": kic,
            "mass_msun": _flt(line[9:13]),
            "e_mass_up": _flt(line[14:18]),
            "e_mass_lo": _flt(line[19:23]),
            "radius_rsun": _flt(line[24:28]),
            "e_radius_up": _flt(line[29:33]),
            "e_radius_lo": _flt(line[34:38]),
            "logg": _flt(line[60:65]),
            "e_logg_up": _flt(line[66:71]),
            "e_logg_lo": _flt(line[72:77]),
            "age_gyr": _flt(line[78:82]),
            "e_age_up": _flt(line[83:87]),
            "e_age_lo": _flt(line[88:91]),
        })
    return pd.DataFrame(rows)


def _fetch() -> pd.DataFrame:
    with urllib.request.urlopen(MIRROR_URL, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    lines = text.split("\n")
    t1 = _parse_table1(lines)
    t5 = _parse_table5(lines)
    return t1.merge(t5, on="KIC", how="inner")


def _validate(df: pd.DataFrame) -> None:
    missing = EXPECTED_KEY_COLUMNS - set(df.columns)
    if missing:
        print(f"[warn] expected columns not found: {missing}", file=sys.stderr)
    if len(df) < 500:
        print(f"[warn] expected ~518 rows, got {len(df)}", file=sys.stderr)


def summarize(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    teff = df["IRFM_Teff"]
    age = df["age_gyr"]
    mass = df["mass_msun"]
    print(f"Teff range [K] (IRFM): {teff.min():.0f} .. {teff.max():.0f} "
          f"(N={teff.notna().sum()})")
    print(f"Age  range [Gyr]:      {age.min():.1f} .. {age.max():.1f} "
          f"(median {age.median():.1f}, N={age.notna().sum()})")
    print(f"Mass range [Msun]:     {mass.min():.2f} .. {mass.max():.2f} "
          f"(N={mass.notna().sum()})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()

    df = _fetch()
    _validate(df)
    write_csv(df, OUT_CSV)
    print(f"Wrote:  {OUT_CSV.relative_to(REPO_ROOT)}  "
          f"({len(df)} rows, {len(df.columns)} cols)")
    print()
    summarize(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
