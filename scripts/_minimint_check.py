#!/usr/bin/env python3
"""Verify that minimint is installed and the MIST grid is prepared.

Run this before ``interpolate_cluster_masses.py`` to confirm that the
one-time MIST grid download has been completed.

Usage:
    python scripts/_minimint_check.py
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import minimint
    except ImportError:
        print("ERROR: minimint is not installed.")
        print("  pip install minimint")
        return 1

    print(f"minimint version: {minimint.__version__}")

    import os
    data_path = minimint.utils.get_data_path()
    print(f"Data path: {data_path}")

    expected = os.path.join(data_path, "interp.pkl")
    if not os.path.exists(expected):
        print()
        print("ERROR: MIST grid not prepared. Run this once:")
        print("  python -c \"import minimint; minimint.download_and_prepare()\"")
        print()
        print("This downloads ~500 MB of MIST isochrone data.")
        return 1

    print("MIST grid: found")

    # Sanity test: solar parameters should give ~1.0 Msun
    import numpy as np
    interp = minimint.TheoryInterpolator(data_path)
    solar_logage = np.log10(4.6e9)  # 4.6 Gyr
    solar_feh = 0.0
    solar_mass = 1.0
    result = interp(solar_mass, solar_logage, solar_feh)
    teff_predicted = 10 ** result["logteff"][0]
    logg_predicted = result["logg"][0]
    print()
    print(f"Sanity test (M=1.0 Msun, age=4.6 Gyr, [Fe/H]=0.0):")
    print(f"  Predicted Teff = {teff_predicted:.0f} K (expect ~5770)")
    print(f"  Predicted log g = {logg_predicted:.3f} (expect ~4.44)")

    if abs(teff_predicted - 5770) > 200:
        print("  WARNING: Teff prediction > 200 K from solar — check grid.")
    else:
        print("  OK — within 200 K of solar.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
