"""Load the unified gyro sample with correct column dtypes.

Gaia source IDs are 19-digit 64-bit integers, which lose precision if
read as float64 (pandas' default for numeric-looking string columns).
Always go through this helper — or pass the same ``dtype`` map to
``pd.read_csv`` — when consuming ``data/processed/gyro_sample.csv``.

Usage:
    from scripts.gyro_sample import load_gyro_sample
    sample = load_gyro_sample()
    g_dwarfs = sample[(sample.teff_k >= 5200) & (sample.teff_k <= 5900)]
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_PATH = (Path(__file__).resolve().parent.parent
                / "data" / "processed" / "gyro_sample.csv")

DTYPES: dict[str, str] = {
    "source_catalog": "string",
    "cluster": "string",
    "cluster_age_gyr": "float64",
    "gaia_dr2": "string",
    "gaia_dr3": "string",
    "kic": "string",
    "teff_k": "float64",
    "teff_source": "string",
    "bp_rp_0": "float64",
    "prot_d": "float64",
    "prot_source": "string",
    "ra_deg": "float64",
    "dec_deg": "float64",
    "age_gyr": "float64",
    "age_source": "string",
    "age_unc_gyr": "float64",
    "mass_msun": "float64",
    "feh": "float64",
    "logg": "float64",
    "radius_rsun": "float64",
    "is_cross_catalog_duplicate": "boolean",
}


def load_gyro_sample(path: str | Path | None = None) -> pd.DataFrame:
    """Read `data/processed/gyro_sample.csv` with precision-safe dtypes."""
    return pd.read_csv(Path(path) if path else DEFAULT_PATH, dtype=DTYPES)


def dedupe_by_gaia(
    sample: pd.DataFrame,
    priority: tuple[str, ...] = (
        "curtis_2020",
        "curtis_2020_rup147",
        "curtis_2019_psceri",
        "godoy_rivera_2021",
        "gruner_2023_m67",
        "legacy_2017",
        "hall_2021",
    ),
) -> pd.DataFrame:
    """Keep one row per star, preferring catalogs earlier in ``priority``.

    Duplicate resolution uses Gaia DR2 where available, falling back to
    Gaia DR3. Rows with neither ID are all retained (treated as unique).
    """
    rank = {name: i for i, name in enumerate(priority)}
    df = sample.copy()
    df["_rank"] = df["source_catalog"].map(rank).fillna(len(rank)).astype(int)
    df = df.sort_values("_rank", kind="mergesort")

    key = df["gaia_dr2"].where(df["gaia_dr2"].notna(), df["gaia_dr3"])
    key = key.where(key.notna(), df["kic"].where(df["kic"].notna()))
    key = key.where(key.notna(), pd.Series(
        [f"__row_{i}" for i in df.index], index=df.index, dtype="string"
    ))
    df["_key"] = key

    deduped = df.drop_duplicates(subset="_key", keep="first")
    return deduped.drop(columns=["_rank", "_key"]).reset_index(drop=True)
