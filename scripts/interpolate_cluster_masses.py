#!/usr/bin/env python3
"""Interpolate stellar masses for cluster stars using MIST isochrones.

For each cluster star with a non-null Teff, inverts the minimint forward
model ``(mass, logage, feh) → logteff`` via root-finding to recover mass
given the cluster's adopted age and literature [Fe/H].

Requires:
    pip install minimint scipy
    python -c "import minimint; minimint.download_and_prepare()"

Output:
    data/raw/cluster_masses_mist.csv
    data/raw/mist_basta_calibration.csv  (Hall 2021 comparison)

Usage:
    python scripts/interpolate_cluster_masses.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
PROCESSED = REPO_ROOT / "data" / "processed"
OUT_MASSES = RAW / "cluster_masses_mist.csv"
OUT_CALIBRATION = RAW / "mist_basta_calibration.csv"

CLUSTER_FEH: dict[str, float] = {
    "NGC 2547": -0.10,
    "Pisces-Eridanus": 0.04,
    "Pleiades": 0.03,
    "M50": 0.07,
    "NGC 2516": 0.05,
    "M37": 0.02,
    "Praesepe": 0.16,
    "NGC 6811": 0.04,
    "NGC 752": -0.04,
    "NGC 6819": 0.09,
    "Ruprecht 147": 0.10,
    "M67": 0.00,
}

CLUSTER_AGE_GYR: dict[str, float] = {
    "NGC 2547": 0.035,
    "Pleiades": 0.120,
    "Pisces-Eridanus": 0.120,
    "M50": 0.130,
    "NGC 2516": 0.150,
    "M37": 0.500,
    "Praesepe": 0.670,
    "NGC 6811": 1.000,
    "NGC 752": 1.400,
    "NGC 6819": 2.500,
    "Ruprecht 147": 2.700,
    "M67": 4.000,
}

TEFF_UNC_K = 75
SYSTEMATIC_FRAC = 0.03


def _check_grid() -> bool:
    """Return True if minimint is installed and the MIST grid is prepared."""
    try:
        import minimint
    except ImportError:
        print("ERROR: minimint is not installed.")
        print("  pip install minimint")
        return False

    import os
    data_path = minimint.utils.get_data_path()
    expected = os.path.join(data_path, "interp.pkl")
    if not os.path.exists(expected):
        print("ERROR: MIST grid not prepared. Run this once:")
        print('  python -c "import minimint; minimint.download_and_prepare()"')
        print()
        print("This downloads ~500 MB of MIST isochrone data.")
        print("See scripts/_minimint_check.py for a diagnostic helper.")
        return False

    return True


def _interpolate_mass(
    interp,
    teff_target: float,
    logage: float,
    feh: float,
    mass_lo: float = 0.1,
) -> float | None:
    """Invert minimint forward model to find mass given Teff.

    Uses scipy.optimize.brentq to solve:
        log10(Teff_predicted(mass)) - log10(Teff_target) = 0

    Returns None if the root-finding fails or the solution is off the
    main sequence (EEP phase > 454).
    """
    from scipy.optimize import brentq

    log_teff_target = np.log10(teff_target)
    mass_hi = float(interp.getMaxMassMS(logage, feh))

    if mass_hi <= mass_lo:
        return None

    def residual(mass: float) -> float:
        result = interp(np.array([mass]), np.array([logage]), np.array([feh]))
        return float(result["logteff"][0]) - log_teff_target

    try:
        r_lo = residual(mass_lo)
        r_hi = residual(mass_hi)
    except Exception:
        return None

    if r_lo * r_hi > 0:
        return None

    try:
        mass = brentq(residual, mass_lo, mass_hi, xtol=1e-5, rtol=1e-5)
    except Exception:
        return None

    result = interp(np.array([mass]), np.array([logage]), np.array([feh]))
    phase = result.get("phase")
    if phase is not None and float(phase[0]) > 454:
        return None

    return float(mass)


def _mass_uncertainty(
    interp,
    mass: float,
    teff_target: float,
    logage: float,
    feh: float,
) -> float:
    """Propagate Teff uncertainty + systematic floor into mass uncertainty.

    sigma_M = sqrt((dM/dTeff * sigma_Teff)^2 + (f_sys * M)^2)
    where dM/dTeff is estimated via finite difference.
    """
    dm_dteff = 0.0
    delta_t = 50.0
    m_plus = _interpolate_mass(interp, teff_target + delta_t, logage, feh)
    m_minus = _interpolate_mass(interp, teff_target - delta_t, logage, feh)
    if m_plus is not None and m_minus is not None:
        dm_dteff = (m_plus - m_minus) / (2 * delta_t)

    sigma_teff = np.abs(dm_dteff) * TEFF_UNC_K
    sigma_sys = SYSTEMATIC_FRAC * mass
    return float(np.sqrt(sigma_teff**2 + sigma_sys**2))


def interpolate_clusters(interp) -> pd.DataFrame:
    """Interpolate masses for all cluster stars in gyro_sample.csv."""
    gyro_path = PROCESSED / "gyro_sample.csv"
    if not gyro_path.exists():
        print("ERROR: data/processed/gyro_sample.csv not found.")
        print("  Run: python scripts/build_gyro_sample.py")
        sys.exit(1)

    from scripts.gyro_sample import load_gyro_sample
    sample = load_gyro_sample(gyro_path)

    cluster_stars = sample[
        sample["cluster"].notna()
        & sample["teff_k"].notna()
        & sample["prot_d"].notna()
    ].copy()

    print(f"Cluster stars with Teff and Prot: {len(cluster_stars)}")

    rows = []
    n_ok = 0
    n_fail = 0

    for idx, row in cluster_stars.iterrows():
        cluster = row["cluster"]
        if cluster not in CLUSTER_FEH:
            n_fail += 1
            continue

        feh = CLUSTER_FEH[cluster]
        age_gyr = CLUSTER_AGE_GYR[cluster]
        logage = np.log10(age_gyr * 1e9)
        teff = float(row["teff_k"])

        mass = _interpolate_mass(interp, teff, logage, feh)
        if mass is None:
            n_fail += 1
            continue

        unc = _mass_uncertainty(interp, mass, teff, logage, feh)
        n_ok += 1

        rows.append({
            "source_catalog": row["source_catalog"],
            "cluster": cluster,
            "gaia_dr2": row.get("gaia_dr2"),
            "gaia_dr3": row.get("gaia_dr3"),
            "teff_k": teff,
            "mass_msun_mist": round(mass, 4),
            "mass_unc_msun_mist": round(unc, 4),
            "feh_adopted": feh,
            "logage_adopted": round(logage, 4),
        })

    print(f"  Interpolated: {n_ok}  |  Failed/skipped: {n_fail}")
    return pd.DataFrame(rows)


def calibration_check(interp) -> pd.DataFrame | None:
    """Compare MIST-interpolated masses to Hall 2021 BASTA masses."""
    hall_path = RAW / "hall_2021.csv"
    if not hall_path.exists():
        print("Skipping calibration: data/raw/hall_2021.csv not found.")
        return None

    hall = pd.read_csv(hall_path)
    hall = hall.dropna(subset=["Teff", "age", "modmass"])

    rows = []
    for _, row in hall.iterrows():
        teff = float(row["Teff"])
        age_gyr = float(row["age"])
        feh = float(row.get("feh", 0.0)) if pd.notna(row.get("feh")) else 0.0
        basta_mass = float(row["modmass"])
        logage = np.log10(age_gyr * 1e9)

        mist_mass = _interpolate_mass(interp, teff, logage, feh)
        if mist_mass is None:
            continue

        rows.append({
            "KIC": row["KIC"],
            "teff_k": teff,
            "age_gyr": age_gyr,
            "feh": feh,
            "basta_mass": basta_mass,
            "mist_mass": round(mist_mass, 4),
            "delta_mass": round(mist_mass - basta_mass, 4),
            "delta_pct": round(100 * (mist_mass - basta_mass) / basta_mass, 2),
        })

    if not rows:
        print("Calibration: no stars interpolated successfully.")
        return None

    cal = pd.DataFrame(rows)
    med = cal["delta_pct"].median()
    mad = (cal["delta_pct"] - med).abs().median()
    rms = np.sqrt((cal["delta_mass"] ** 2).mean())
    print()
    print(f"Calibration vs Hall 2021 BASTA ({len(cal)} stars):")
    print(f"  Median offset: {med:+.2f}%")
    print(f"  MAD:           {mad:.2f}%")
    print(f"  RMS(delta M):  {rms:.4f} Msun")

    outliers = cal[cal["delta_pct"].abs() > 10]
    if len(outliers):
        print(f"  Outliers (|delta| > 10%): {len(outliers)}")
        for _, o in outliers.iterrows():
            print(f"    KIC {o['KIC']}: BASTA={o['basta_mass']:.3f}, "
                  f"MIST={o['mist_mass']:.3f} ({o['delta_pct']:+.1f}%)")

    return cal


def main() -> int:
    if not _check_grid():
        print()
        print("Cannot proceed without the MIST grid.")
        print("Run this script locally after preparing the grid.")
        return 1

    import minimint
    data_path = minimint.utils.get_data_path()
    interp = minimint.TheoryInterpolator(data_path)
    print(f"minimint loaded (data: {data_path})")

    # --- Solar sanity check ---
    solar_logage = np.log10(4.6e9)
    solar_mass = _interpolate_mass(interp, 5770.0, solar_logage, 0.0)
    if solar_mass is not None:
        print(f"Solar sanity check: Teff=5770 K -> M={solar_mass:.4f} Msun "
              f"(expect ~1.0)")
        if abs(solar_mass - 1.0) > 0.05:
            print("  WARNING: solar mass off by > 5% — check grid integrity.")
    else:
        print("WARNING: solar sanity check failed (root-finding returned None).")
    print()

    # --- Cluster mass interpolation ---
    masses = interpolate_clusters(interp)

    if len(masses):
        RAW.mkdir(parents=True, exist_ok=True)
        masses.to_csv(OUT_MASSES, index=False)
        print(f"\nWrote {OUT_MASSES.relative_to(REPO_ROOT)}  ({len(masses)} rows)")

        # Per-cluster summary.
        print("\nPer-cluster mass summary:")
        for cluster in masses["cluster"].unique():
            sub = masses[masses["cluster"] == cluster]
            m = sub["mass_msun_mist"]
            print(f"  {cluster:<18s}  n={len(sub):>4d}  "
                  f"M={m.median():.3f} [{m.min():.3f}-{m.max():.3f}] Msun")

        # G-dwarf stall-regime recovery count.
        g_band = masses[(masses["teff_k"] >= 5200) & (masses["teff_k"] <= 5900)]
        old_g = g_band[g_band["cluster"].map(CLUSTER_AGE_GYR) > 2]
        print(f"\nG dwarfs (5200-5900 K) in age>2 Gyr clusters: {len(old_g)}")
    else:
        print("\nNo cluster masses interpolated.")

    # --- Calibration check ---
    cal = calibration_check(interp)
    if cal is not None and len(cal):
        cal.to_csv(OUT_CALIBRATION, index=False)
        print(f"\nWrote {OUT_CALIBRATION.relative_to(REPO_ROOT)}  ({len(cal)} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
