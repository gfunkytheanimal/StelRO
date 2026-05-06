# StelRO — Stellar Rotation research workspace

A small, reproducible workspace for stellar rotation / gyrochronology studies
built on published open-cluster rotation catalogs and asteroseismic field-star
samples.

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
python scripts/fetch_hall_2021.py            # asteroseismic field stars, 1-13 Gyr
python scripts/build_gyro_sample.py          # -> data/processed/gyro_sample.csv
```

Each `fetch_*.py` script queries the VizieR TAP endpoint (primary) and
transparently falls back to a mirror when CDS is unreachable. Pass `--mirror`
to force the fallback.

## Included catalogs

| Slug                  | Reference                              | Type   | Rows | Age coverage     |
|-----------------------|----------------------------------------|--------|-----:|------------------|
| `curtis_2020`         | Curtis et al. 2020, ApJ 904, 140 (t5)  | cluster |  923 | 0.12 – 2.7 Gyr  |
| `curtis_2020_rup147`  | Curtis et al. 2020, ApJ 904, 140 (t1)  | cluster |   67 | 2.7 Gyr          |
| `godoy_rivera_2021`   | Godoy-Rivera et al. 2021, ApJS 257, 46 | cluster | 3492 | 0.035 – 1.0 Gyr |
| `curtis_2019_psceri`  | Curtis et al. 2019, AJ 158, 77         | cluster |  101 | 0.12 Gyr         |
| `gruner_2023_m67`     | Gruner, Barnes & Weingrill 2023, A&A 675, A180 | cluster | 47 | 4.0 Gyr   |
| `hall_2021`           | Hall et al. 2021, Nature Astronomy 5, 707 | field (asteroseismic) | 94 | 1.3 – 13.0 Gyr |

**Hall et al. 2021 note.** Rotation periods in this catalog are derived from
asteroseismic rotational frequency splitting (not surface spot modulation).
For main-sequence solar-type stars this closely tracks the surface rotation
rate; for subgiants (`hrclass="SG"` in the raw table, 4 of 94 stars), core
and surface rates can decouple. The raw table preserves the `flag` and
`hrclass` columns for downstream quality filtering. Data sourced from the
author's official repository ([`ojhall94/halletal2021`](https://github.com/ojhall94/halletal2021)).

## `data/processed/gyro_sample.csv` schema

`scripts/build_gyro_sample.py` merges all raw catalogs into a single
long-format table. **One row per (catalog, star) pair** — cross-catalog
duplicates are flagged but retained.

| Column                        | Type     | Description                                                                             |
|-------------------------------|----------|-----------------------------------------------------------------------------------------|
| `source_catalog`              | string   | One of the slugs above                                                                  |
| `cluster`                     | string   | Canonical cluster / stream name, or null for field stars                                |
| `cluster_age_gyr`             | float    | Adopted cluster age in Gyr, or null for field stars                                     |
| `gaia_dr2`                    | string   | Gaia DR2 source ID (null for field stars without Gaia crossmatch)                       |
| `gaia_dr3`                    | string   | Gaia DR3 source ID (populated for `gruner_2023_m67`)                                    |
| `kic`                         | string   | Kepler Input Catalog ID (populated for `hall_2021`)                                     |
| `teff_k`                      | float    | Effective temperature in Kelvin                                                         |
| `teff_source`                 | string   | `catalog` if Teff was published; `derived_bp_rp` if derived from (BP-RP)₀               |
| `bp_rp_0`                     | float    | Dereddened Gaia BP-RP colour (where published)                                          |
| `prot_d`                      | float    | Rotation period in days (surface spot for clusters, asteroseismic splitting for Hall)    |
| `ra_deg`, `dec_deg`           | float    | ICRS coordinates (degrees) where provided                                               |
| `age_gyr`                     | float    | **Adopted age in Gyr.** Equals `cluster_age_gyr` for cluster stars; equals the asteroseismic age for field stars. Populated for every row. |
| `age_source`                  | string   | `cluster` or `asteroseismic_hall_2021` (extensible — Phase 2 will add `asteroseismic_legacy`) |
| `age_unc_gyr`                 | float    | Symmetric age uncertainty in Gyr (mean of asymmetric lo/up); null for cluster stars      |
| `is_cross_catalog_duplicate`  | bool     | True if the same Gaia ID (DR2 or DR3) appears in more than one `source_catalog`         |

**Teff derivation for M67.** Gruner et al. 2023 do not publish Teff. The
build script fits a degree-4 polynomial to the Curtis 2020 Table 5 pairs of
`(BP-RP)₀, Teff` over `0.5 ≤ (BP-RP)₀ ≤ 2.6`, and applies it to stars
lacking a published Teff. 48 rows have `teff_source = "derived_bp_rp"`.

### Loading the sample (precision-safe)

Gaia source IDs and KIC IDs are integers that can silently lose precision if
read as `float64`. Always go through the helper:

```python
from scripts.gyro_sample import load_gyro_sample, dedupe_by_gaia

sample = load_gyro_sample()
# If a one-row-per-star view is wanted:
unique = dedupe_by_gaia(sample)
```

### Current sample summary

```
Total: 4724 rows (4630 cluster + 94 field), 16 columns.

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

Hall 2021 field stars: 94
  Age span: 1.3 – 13.0 Gyr (asteroseismic)
  Prot span: 1.2 – 53.6 d (asteroseismic splitting)

Age histogram (1-Gyr bins):
   0- 1 Gyr   4050
   1- 2 Gyr    409
   2- 3 Gyr    159
   3- 4 Gyr     14
   4- 5 Gyr     51
   5- 6 Gyr      4
   6- 7 Gyr     14
   7- 8 Gyr      9
   8- 9 Gyr      4
   9-10 Gyr      3
  10-11 Gyr      3
  11-12 Gyr      3
  12-13 Gyr      1

G dwarfs (5200-5900 K) with age > 2 Gyr: 86
  cluster                           55
  asteroseismic_hall_2021           31
```

## Conventions

- `data/raw/` is treated as read-only; transformations write to
  `data/processed/` via a separate script.
- Every dataset in `data/raw/` has a matching `scripts/fetch_*.py` so the
  repo is reproducible from code alone.
- Retired experiments move to `graveyard/` rather than being deleted
  (see `graveyard/README.md` for the retirement log format).
