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

## Reproducing the sample

```bash
python scripts/fetch_curtis_2020.py          # 923 rows, 7 clusters
python scripts/fetch_godoy_rivera_2021.py    # 3492 rows, 7 clusters
python scripts/fetch_curtis_2019_psceri.py   # 101 rows, Pisces-Eridanus stream
python scripts/build_gyro_sample.py          # -> data/processed/gyro_sample.csv
```

Each `fetch_*.py` script queries the VizieR TAP endpoint (primary) and
transparently falls back to a FITS mirror hosted in
[`lgbouma/gyro-interp`](https://github.com/lgbouma/gyro-interp) when CDS is
unreachable. Pass `--mirror` to force the fallback.

## Included catalogs

| Slug                  | Reference                              | Rows | Clusters / stream                                                    |
|-----------------------|----------------------------------------|------|----------------------------------------------------------------------|
| `curtis_2020`         | Curtis et al. 2020, ApJ 904, 140       | 923  | Pleiades, Praesepe, NGC 6811, NGC 6819, NGC 752, Ruprecht 147 (+ anchors) |
| `godoy_rivera_2021`   | Godoy-Rivera et al. 2021, ApJS 257, 46 | 3492 | NGC 2547, NGC 2516, M50, M37, Pleiades, Praesepe, NGC 6811            |
| `curtis_2019_psceri`  | Curtis et al. 2019, AJ 158, 77         | 101  | Pisces-Eridanus stream                                                |

## `data/processed/gyro_sample.csv` schema

`scripts/build_gyro_sample.py` merges all three raw catalogs into a single
long-format table. One row per published (star, catalog) pair.

| Column                        | Type   | Description                                                                 |
|-------------------------------|--------|-----------------------------------------------------------------------------|
| `source_catalog`              | str    | One of `curtis_2020`, `godoy_rivera_2021`, `curtis_2019_psceri`             |
| `cluster`                     | str    | Canonical cluster / stream name (e.g. `NGC 2516`, `Pisces-Eridanus`)        |
| `cluster_age_gyr`             | float  | Adopted literature age in Gyr (see `CLUSTER_AGE_GYR` in the build script)   |
| `gaia_dr2`                    | str    | Gaia DR2 source ID, or empty string if not reported                         |
| `teff_k`                      | float  | Effective temperature in Kelvin (photometric, as published)                 |
| `prot_d`                      | float  | Rotation period in days                                                     |
| `ra_deg`, `dec_deg`           | float  | ICRS coordinates (degrees) where provided                                   |
| `is_cross_catalog_duplicate`  | bool   | True if the same Gaia DR2 ID appears in more than one `source_catalog`      |

Rows are sorted by `cluster_age_gyr`, then by `cluster`, `source_catalog`, and
`teff_k`. Duplicate `gaia_dr2` IDs are kept intentionally so disagreements in
`teff_k` / `prot_d` between catalogs remain visible to analysis code.

### Current sample summary

```
Per-cluster counts (age-ordered):
  NGC 2547         0.035 Gyr  n=  176
  Pisces-Eridanus  0.120 Gyr  n=  101
  Pleiades         0.120 Gyr  n= 1081
  M50              0.130 Gyr  n=  812
  NGC 2516         0.150 Gyr  n=  362
  M37              0.500 Gyr  n=  367
  Praesepe         0.670 Gyr  n= 1151
  NGC 6811         1.000 Gyr  n=  393
  NGC 752          1.400 Gyr  n=    8
  NGC 6819         2.500 Gyr  n=   30
  Ruprecht 147     2.700 Gyr  n=   35
Total: 4516 rows; Teff span 2548–11593 K; Prot span 0.05–42.7 d.
```

## Conventions

- `data/raw/` is treated as read-only; transformations write to
  `data/processed/` via a separate script.
- Every dataset in `data/raw/` has a matching `scripts/fetch_*.py` so the repo
  is reproducible from code alone.
- Retired experiments move to `graveyard/` rather than being deleted.
