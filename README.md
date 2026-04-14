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
graveyard/      # retired code, framings, and theoretical threads
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Reproducing the sample

```bash
python scripts/fetch_curtis_2020.py          # t5 composite, 7 clusters, 923 rows
python scripts/fetch_curtis_2020_rup147.py   # t1 Rup 147 rotators, 2.7 Gyr
python scripts/fetch_godoy_rivera_2021.py    # 7 clusters, Gaia DR2, 3492 rows
python scripts/fetch_curtis_2019_psceri.py   # Pisces-Eridanus stream, 120 Myr
python scripts/fetch_gruner_2023_m67.py      # M67, ~4 Gyr, Gaia DR3
python scripts/build_gyro_sample.py          # -> data/processed/gyro_sample.csv
```

Each `fetch_*.py` script queries the VizieR TAP endpoint (primary) and
transparently falls back to a FITS/CSV mirror hosted in
[`lgbouma/gyro-interp`](https://github.com/lgbouma/gyro-interp) when CDS is
unreachable. Pass `--mirror` to force the fallback.

## Included catalogs

| Slug                  | Reference                              | Rows | Clusters / stream                                                    |
|-----------------------|----------------------------------------|-----:|----------------------------------------------------------------------|
| `curtis_2020`         | Curtis et al. 2020, ApJ 904, 140 (t5)  |  923 | Pleiades, Praesepe, NGC 6811, NGC 6819, NGC 752, Ruprecht 147 (+anchors) |
| `curtis_2020_rup147`  | Curtis et al. 2020, ApJ 904, 140 (t1)  |   67 | Ruprecht 147 (rotators only, parent = 440)                            |
| `godoy_rivera_2021`   | Godoy-Rivera et al. 2021, ApJS 257, 46 | 3492 | NGC 2547, NGC 2516, M50, M37, Pleiades, Praesepe, NGC 6811            |
| `curtis_2019_psceri`  | Curtis et al. 2019, AJ 158, 77         |  101 | Pisces-Eridanus stream                                                |
| `gruner_2023_m67`     | Gruner, Barnes & Weingrill 2023, A&A 675, A180 | 47 | M67                                                            |

## `data/processed/gyro_sample.csv` schema

`scripts/build_gyro_sample.py` merges all raw catalogs into a single
long-format table. **One row per (catalog, star) pair** — cross-catalog
duplicates are flagged but retained so downstream analysis can decide
how to resolve disagreements.

| Column                        | Type     | Description                                                                             |
|-------------------------------|----------|-----------------------------------------------------------------------------------------|
| `source_catalog`              | string   | One of the slugs above                                                                  |
| `cluster`                     | string   | Canonical cluster / stream name (e.g. `NGC 2516`, `Pisces-Eridanus`)                    |
| `cluster_age_gyr`             | float    | Adopted literature age in Gyr (see `CLUSTER_AGE_GYR` in `build_gyro_sample.py`)         |
| `gaia_dr2`                    | string   | Gaia DR2 source ID, or null if the source catalog did not publish DR2                   |
| `gaia_dr3`                    | string   | Gaia DR3 source ID (populated for `gruner_2023_m67`)                                    |
| `teff_k`                      | float    | Effective temperature in Kelvin                                                         |
| `teff_source`                 | string   | `catalog` if Teff was published; `derived_bp_rp` if derived from (BP-RP)_0              |
| `bp_rp_0`                     | float    | Dereddened Gaia BP-RP colour (where published)                                          |
| `prot_d`                      | float    | Rotation period in days                                                                 |
| `ra_deg`, `dec_deg`           | float    | ICRS coordinates (degrees) where provided                                               |
| `is_cross_catalog_duplicate`  | bool     | True if the same Gaia ID (DR2 or DR3) appears in more than one `source_catalog`         |

**Teff derivation for M67.** Gruner et al. 2023 do not publish Teff. The
build script fits a degree-4 polynomial to the Curtis 2020 Table 5 pairs of
`(BP-RP)_0, Teff` over `0.5 <= (BP-RP)_0 <= 2.6`, and applies it to stars
lacking a published Teff. Gruner M67 (BP-RP)_0 spans 0.69-2.52, well inside
the fit range. 48 rows have `teff_source = "derived_bp_rp"`.

### Loading the sample (precision-safe)

Gaia source IDs are 19-digit integers that silently lose precision if read
as `float64`. Always go through the helper:

```python
from scripts.gyro_sample import load_gyro_sample, dedupe_by_gaia

sample = load_gyro_sample()
# If a one-row-per-star view is wanted:
unique = dedupe_by_gaia(sample)
# Preference order: curtis_2020 > curtis_2020_rup147 > curtis_2019_psceri
#                 > godoy_rivera_2021 > gruner_2023_m67  (customizable)
```

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
  Ruprecht 147     2.700 Gyr  n=  102
  M67              4.000 Gyr  n=   47
Total: 4630 rows (3690 unique stars).
Teff span: 2548-11593 K    Prot span: 0.05-42.7 d.
```

**G-dwarf subsample** (5200 <= Teff <= 5900 K, deduped by Gaia ID, preferring
Curtis-family catalogs): 337 stars across 10 clusters. Underpowered
clusters (n<20): NGC 2547 (1), NGC 6819 (18), M67 (9). M67 is the binding
constraint at the old end and is where more data would most improve any
slow-sequence convergence test.

## Conventions

- `data/raw/` is treated as read-only; transformations write to
  `data/processed/` via a separate script.
- Every dataset in `data/raw/` has a matching `scripts/fetch_*.py` so the
  repo is reproducible from code alone.
- Retired experiments move to `graveyard/` rather than being deleted
  (see `graveyard/README.md` for the retirement log format).
