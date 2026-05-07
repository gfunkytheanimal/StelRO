#!/usr/bin/env python3
"""Assemble the Kepler LEGACY asteroseismic sample with surface Prot.

Joins three raw tables on KIC:
  1. Silva Aguirre 2017 — BASTA ages, masses, radii (66 stars)
  2. literature_seismo   — seismic Prot from 4 pipelines (informational)
  3. lit_spot_rots        — surface spot-modulation Prot (McQuillan, García, etc.)

The best available surface Prot is selected with this priority:
  McQP (McQuillan 2014) > GP (García 2014) > jvsP > NP > SP

Output: data/processed/legacy_assembled.csv

Run the fetchers first:
    python scripts/fetch_silva_aguirre_2017.py --mirror
    python scripts/fetch_nielsen_2017.py
    python scripts/fetch_mcquillan_2014.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
OUT = REPO_ROOT / "data" / "processed" / "legacy_assembled.csv"

SPOT_PROT_PRIORITY = ["McQP", "GP", "jvsP", "NP", "SP"]
SPOT_PROT_SOURCE = {
    "McQP": "mcquillan_2014",
    "GP": "garcia_2014",
    "jvsP": "van_saders_ceillier",
    "NP": "nielsen_2013",
    "SP": "santos",
}


def _pick_best_spot_prot(row: pd.Series) -> tuple:
    """Return (best_prot, prot_source_label) for a row from lit_spot_rots."""
    for col in SPOT_PROT_PRIORITY:
        val = row.get(col)
        if pd.notna(val):
            return float(val), SPOT_PROT_SOURCE[col]
    return pd.NA, pd.NA


def main() -> int:
    sa = pd.read_csv(RAW / "silva_aguirre_2017.csv")
    seismo = pd.read_csv(RAW / "literature_seismo.csv")
    spot = pd.read_csv(RAW / "lit_spot_rots.csv")

    # --- Surface Prot assignment ---
    best_prot = spot.apply(_pick_best_spot_prot, axis=1, result_type="expand")
    best_prot.columns = ["spot_prot_d", "spot_prot_source"]
    spot_slim = pd.concat([spot[["KIC"]], best_prot], axis=1)

    # --- Seismic Prot: keep Benomar 2018 (widest coverage) as reference ---
    seismo_slim = seismo[["KIC", "B18_P_rot"]].rename(
        columns={"B18_P_rot": "seismo_prot_d"}
    )

    # --- Join on KIC ---
    df = sa.merge(spot_slim, on="KIC", how="left")
    df = df.merge(seismo_slim, on="KIC", how="left")

    # --- Choose best Prot for the gyro sample ---
    # Priority: surface spot (direct measurement) > asteroseismic splitting
    df["prot_d"] = df["spot_prot_d"].where(
        df["spot_prot_d"].notna(), df["seismo_prot_d"]
    )
    df["prot_source"] = df["spot_prot_source"].where(
        df["spot_prot_d"].notna(),
        pd.Series("asteroseismic_benomar_2018", index=df.index).where(
            df["seismo_prot_d"].notna()
        ),
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    # --- Summary ---
    print(f"Wrote {OUT.relative_to(REPO_ROOT)}  "
          f"({len(df)} rows, {len(df.columns)} cols)")
    print()
    print(f"Stars with surface spot Prot: {df['spot_prot_d'].notna().sum()}")
    print(f"Stars with seismic Prot (B18): {df['seismo_prot_d'].notna().sum()}")
    print(f"Stars with ANY Prot: {df['prot_d'].notna().sum()}")
    print(f"Stars with NO Prot: {df['prot_d'].isna().sum()}")
    print()
    print("Prot source breakdown:")
    for src, n in df["prot_source"].value_counts(dropna=False).items():
        print(f"  {src!s:<32s}  {n:>3d}")
    print()
    g_band = df[(df["Teff"] >= 5200) & (df["Teff"] <= 5900)]
    g_with_prot = g_band[g_band["prot_d"].notna()]
    print(f"G dwarfs (5200-5900 K): {len(g_band)} total, "
          f"{len(g_with_prot)} with Prot")
    print(f"G dwarfs with age > 2 Gyr and Prot: "
          f"{len(g_with_prot[g_with_prot['age'] > 2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
