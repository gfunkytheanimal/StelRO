#!/usr/bin/env python3
"""Assemble the García 2014 rotation + Chaplin 2014 asteroseismic sample.

Joins García rotation periods (surface spot modulation) with Chaplin
stellar properties (ages, masses, radii, Teff from IRFM) on KIC.

Output: data/raw/garcia_assembled.csv

Run the fetchers first:
    python scripts/fetch_garcia_2014.py --mirror
    python scripts/fetch_chaplin_2014.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
OUT = RAW / "garcia_assembled.csv"


def main() -> int:
    garcia = pd.read_csv(RAW / "garcia_2014.csv")
    chaplin = pd.read_csv(RAW / "chaplin_2014.csv")

    df = chaplin.merge(garcia, on="KIC", how="inner")

    # Prefer IRFM Teff, fall back to SDSS
    df["teff_k"] = df["IRFM_Teff"].where(df["IRFM_Teff"].notna(), df["SDSS_Teff"])

    # Symmetric age uncertainty
    df["age_unc_gyr"] = (
        pd.to_numeric(df["e_age_up"], errors="coerce")
        + pd.to_numeric(df["e_age_lo"], errors="coerce")
    ) / 2.0

    # Select and rename to standard schema
    out = pd.DataFrame({
        "KIC": df["KIC"],
        "teff_k": df["teff_k"],
        "age_gyr": df["age_gyr"],
        "age_unc_gyr": df["age_unc_gyr"],
        "mass_msun": df["mass_msun"],
        "radius_rsun": df["radius_rsun"],
        "feh": df["feh"],
        "logg": df["logg"],
        "prot_d": df["Prot"],
        "prot_err_d": df["Prot_err"],
    })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)

    # --- Summary ---
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}  "
          f"({len(out)} rows, {len(out.columns)} cols)")
    print()
    print(f"Teff range [K]:  {out.teff_k.min():.0f} .. {out.teff_k.max():.0f} "
          f"(N={out.teff_k.notna().sum()})")
    print(f"Age  range [Gyr]: {out.age_gyr.min():.1f} .. {out.age_gyr.max():.1f} "
          f"(median {out.age_gyr.median():.1f})")
    print(f"Prot range [d]:  {out.prot_d.min():.2f} .. {out.prot_d.max():.2f}")
    print(f"Mass range [Msun]: {out.mass_msun.min():.2f} .. {out.mass_msun.max():.2f}")
    print()

    g_band = out[(out.teff_k >= 5200) & (out.teff_k <= 5900)]
    g_old = g_band[g_band.age_gyr > 2]
    print(f"G dwarfs (5200-5900 K): {len(g_band)}")
    print(f"G dwarfs with age > 2 Gyr: {len(g_old)}")

    # Overlap check with Hall 2021
    hall_path = RAW / "hall_2021.csv"
    if hall_path.exists():
        hall = pd.read_csv(hall_path)
        hall_kics = set(hall["KIC"].values)
        garcia_kics = set(out["KIC"].values)
        overlap = garcia_kics & hall_kics
        new = garcia_kics - hall_kics
        print(f"\nOverlap with Hall 2021: {len(overlap)} KICs")
        print(f"García-only (new stars): {len(new)} KICs")
        new_df = out[out["KIC"].isin(new)]
        new_g = new_df[(new_df.teff_k >= 5200) & (new_df.teff_k <= 5900)]
        new_g_old = new_g[new_g.age_gyr > 2]
        print(f"New G dwarfs with age > 2 Gyr: {len(new_g_old)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
