# StelRO — Stellar Rotation research workspace

A small, reproducible workspace for stellar rotation / gyrochronology studies
built on published open-cluster rotation catalogs.

## Layout

```
data/
  raw/          # unmodified catalog pulls (gitignored; reproduce via scripts/)
  processed/    # derived tables, crossmatches, cleaned samples (gitignored)
scripts/        # data fetching + processing entry points
notebooks/      # exploratory analysis
results/        # figures and final tables (gitignored)
graveyard/      # retired code kept for reference
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Fetching Curtis et al. 2020 Table 5

Curtis et al. 2020, *ApJ* 904, 140 — a composite rotation sample across seven
open clusters (Pleiades, Praesepe, NGC 6811, NGC 6819, Ruprecht 147, …).

```bash
python scripts/fetch_curtis_2020.py
```

This queries the VizieR TAP endpoint for catalog `J/ApJ/904/140`, table
`table5`, writes `data/raw/curtis_2020_table5.csv`, and prints per-cluster
counts plus the global Teff and Prot ranges.

If the CDS TAP service is unreachable (e.g. in a locked-down sandbox), pass
`--mirror` to pull the identical 923-row table from the
[`lgbouma/gyro-interp`](https://github.com/lgbouma/gyro-interp) GitHub mirror
(`Curtis_2020_t5_composite_923_rows.fits`). The script also falls back to the
mirror automatically when the TAP request fails with a network error.

```bash
python scripts/fetch_curtis_2020.py --mirror
```

## Conventions

- `data/raw/` is treated as read-only; transformations write to
  `data/processed/` via a separate script.
- Every dataset that lives under `data/raw/` has a matching `scripts/fetch_*.py`
  so the repo is reproducible from code alone.
- Retired experiments move to `graveyard/` rather than being deleted.
