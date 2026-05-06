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
python scripts/fetch_silva_aguirre_2017.py   # LEGACY ages/masses, 66 stars
python scripts/fetch_nielsen_2017.py         # seismic Prot (literature)
python scripts/fetch_mcquillan_2014.py       # surface spot Prot (McQuillan etc.)
python scripts/build_legacy_sample.py        # -> data/processed/legacy_assembled.csv
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
| `legacy_2017`         | Silva Aguirre et al. 2017, ApJ 835, 173 (BASTA) + surface Prot crossmatch | field (asteroseismic) | 66 | 1.3 – 13.0 Gyr |

**Hall et al. 2021 note.** Rotation periods in this catalog are derived from
asteroseismic rotational frequency splitting (not surface spot modulation).
For main-sequence solar-type stars this closely tracks the surface rotation
rate; for subgiants (`hrclass="SG"` in the raw table, 4 of 94 stars), core
and surface rates can decouple. The raw table preserves the `flag` and
`hrclass` columns for downstream quality filtering. Data sourced from the
author's official repository ([`ojhall94/halletal2021`](https://github.com/ojhall94/halletal2021)).

**LEGACY 2017 note.** All 66 LEGACY KICs are a subset of the 94 Hall 2021
stars (source='L' in Hall). The LEGACY addition provides: (1) BASTA model
parameters (mass, radius, [Fe/H], log g) from Silva Aguirre et al. 2017,
and (2) surface spot-modulation Prot where available (43 of 66 stars from
McQuillan 2014, García 2014, and others — assembled via the `malatium`
companion repo). The `prot_source` column tracks which measurement each
star uses; 6 LEGACY stars have no Prot from any source. These 66 rows are
flagged as cross-catalog duplicates with Hall 2021; use `dedupe_by_gaia()`
(which also deduplicates on KIC) to retain only the preferred row per star.

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
| `prot_d`                      | float    | Rotation period in days                                                                 |
| `prot_source`                 | string   | `spot_modulation`, `asteroseismic_splitting`, `mcquillan_2014`, `garcia_2014`, etc.     |
| `ra_deg`, `dec_deg`           | float    | ICRS coordinates (degrees) where provided                                               |
| `age_gyr`                     | float    | **Adopted age in Gyr.** Equals `cluster_age_gyr` for cluster stars; equals the asteroseismic age for field stars. Populated for every row. |
| `age_source`                  | string   | `cluster`, `asteroseismic_hall_2021`, or `asteroseismic_legacy`                         |
| `age_unc_gyr`                 | float    | Symmetric age uncertainty in Gyr (mean of asymmetric lo/up); null for cluster stars      |
| `mass_msun`                   | float    | Stellar mass in solar masses (from BASTA models; populated for field stars)              |
| `feh`                         | float    | Metallicity [Fe/H] (populated for field stars)                                          |
| `logg`                        | float    | Surface gravity log g (populated for field stars)                                       |
| `radius_rsun`                 | float    | Stellar radius in solar radii (from BASTA; populated for LEGACY stars only)             |
| `is_cross_catalog_duplicate`  | bool     | True if the same Gaia ID (DR2/DR3) or KIC appears in more than one `source_catalog`    |

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
Total: 4790 rows (4630 cluster + 160 field), 21 columns.

Per-source counts:
  curtis_2020               923
  curtis_2020_rup147         67
  godoy_rivera_2021        3492
  curtis_2019_psceri        101
  gruner_2023_m67            47
  hall_2021                  94
  legacy_2017                66

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

Field stars: 160 (94 Hall 2021 + 66 LEGACY)
  Age span: 1.3 – 13.0 Gyr (asteroseismic)

Prot source breakdown:
  spot_modulation              4630
  asteroseismic_splitting        94
  garcia_2014                    31
  asteroseismic_benomar_2018     17
  mcquillan_2014                 10
  van_saders_ceillier             2
  (no Prot)                       6

Age histogram (1-Gyr bins):
   0- 1 Gyr   4050
   1- 2 Gyr    417
   2- 3 Gyr    181
   3- 4 Gyr     22
   4- 5 Gyr     55
   5- 6 Gyr      5
   6- 7 Gyr     20
   7- 8 Gyr     16
   8- 9 Gyr      7
   9-10 Gyr      6
  10-11 Gyr      5
  11-12 Gyr      4
  12-13 Gyr      2

G dwarfs (5200-5900 K) with age > 2 Gyr: 106
  cluster                           55
  asteroseismic_hall_2021           31
  asteroseismic_legacy              20

Modeling-ready (age>2, G-dwarf, non-null Prot AND mass): 49
```

## Conventions

- `data/raw/` is treated as read-only; transformations write to
  `data/processed/` via a separate script.
- Every dataset in `data/raw/` has a matching `scripts/fetch_*.py` so the
  repo is reproducible from code alone.
- Retired experiments move to `graveyard/` rather than being deleted
  (see `graveyard/README.md` for the retirement log format).
