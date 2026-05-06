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
python scripts/build_gyro_sample.py
```

## Loading the sample
Always use the helper — naive `pd.read_csv` corrupts 19-digit Gaia IDs:
```python
from scripts.gyro_sample import load_gyro_sample, dedupe_by_gaia
sample = load_gyro_sample()           # 4724 rows, 16 cols
unique = dedupe_by_gaia(sample)       # ~3784 unique stars
```

## Key columns
- `age_gyr` — the age column to use for all analysis (cluster age or
  asteroseismic age depending on `age_source`)
- `prot_d` — rotation period in days
- `teff_k` — effective temperature in K
- `age_source` — `"cluster"` or `"asteroseismic_hall_2021"`
- `age_unc_gyr` — age uncertainty (null for cluster stars)
- `is_cross_catalog_duplicate` — True if same Gaia ID in multiple catalogs

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
- Cluster ages are point estimates with no uncertainty in this schema;
  Hall 2021 field stars carry `age_unc_gyr`
