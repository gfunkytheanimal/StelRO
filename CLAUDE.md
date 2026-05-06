# StelRO — Claude Code orientation

## What this is
A stellar rotation / gyrochronology research workspace. The pipeline fetches
published rotation catalogs, harmonizes them into a single analysis-ready
table (`data/processed/gyro_sample.csv`), and supports studies of rotational
evolution across 0.035–13 Gyr.

## Quick start
```bash
pip install -r requirements.txt
python scripts/fetch_curtis_2020.py
python scripts/fetch_curtis_2020_rup147.py
python scripts/fetch_godoy_rivera_2021.py
python scripts/fetch_curtis_2019_psceri.py
python scripts/fetch_gruner_2023_m67.py
python scripts/fetch_hall_2021.py
python scripts/fetch_silva_aguirre_2017.py --mirror
python scripts/fetch_nielsen_2017.py
python scripts/fetch_mcquillan_2014.py
python scripts/build_legacy_sample.py
python scripts/build_gyro_sample.py
```

## Loading the sample
Always use the helper — naive `pd.read_csv` corrupts 19-digit Gaia IDs:
```python
from scripts.gyro_sample import load_gyro_sample, dedupe_by_gaia
sample = load_gyro_sample()           # 4790 rows, 21 cols
unique = dedupe_by_gaia(sample)       # ~3784 unique stars
```

## Key columns
- `age_gyr` — the age column to use for all analysis (cluster age or
  asteroseismic age depending on `age_source`)
- `prot_d` — rotation period in days
- `teff_k` — effective temperature in K
- `prot_source` — measurement technique: `"spot_modulation"`, `"asteroseismic_splitting"`, or per-paper label
- `age_source` — `"cluster"`, `"asteroseismic_hall_2021"`, or `"asteroseismic_legacy"`
- `age_unc_gyr` — age uncertainty (null for cluster stars)
- `mass_msun`, `feh`, `logg`, `radius_rsun` — BASTA model parameters (populated for field stars)
- `is_cross_catalog_duplicate` — True if same Gaia ID or KIC in multiple catalogs

## Data is gitignored
`data/raw/` and `data/processed/` are in `.gitignore`. Run the fetch scripts
above to regenerate everything from code. Each fetcher tries VizieR TAP first
and falls back to a GitHub mirror when CDS is unreachable (pass `--mirror`
to force the fallback).

## Conventions
- Analysis outputs go in `results/`
- Notebooks go in `notebooks/`
- Retired code goes in `graveyard/` with a row in `graveyard/README.md`
- New catalogs get a `scripts/fetch_<author>_<year>.py` following the
  existing pattern (see `scripts/_vizier_fetch.py` for the shared helper)
- Match existing code style: type hints, `from __future__ import annotations`,
  no excess comments

## Known sample limitations
- M67 (4 Gyr) has only 9 G dwarfs in the Teff 5200–5900 K band
- NGC 6819 (2.5 Gyr) has only 18 G dwarfs
- NGC 752 (1.4 Gyr) has only 8 stars total
- Hall 2021 Prot is from asteroseismic frequency splitting, not spot
  modulation — distinct measurement technique from the cluster catalogs
- LEGACY 2017: all 66 KICs are a subset of Hall 2021; the addition brings
  BASTA model params and surface-Prot crossmatch (43/66 have spot Prot)
- 6 LEGACY stars have no Prot from any source
- Cluster ages are point estimates with no uncertainty in this schema;
  field stars carry `age_unc_gyr`
- Modeling-ready count (age>2 Gyr, G-dwarf, non-null Prot AND mass): 49
