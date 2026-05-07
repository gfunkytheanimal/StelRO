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
python scripts/fetch_garcia_2014.py --mirror
python scripts/fetch_chaplin_2014.py
python scripts/build_garcia_sample.py
python scripts/build_gyro_sample.py
# Optional: cluster mass interpolation (requires local MIST grid)
python scripts/_minimint_check.py
python scripts/interpolate_cluster_masses.py
python scripts/build_gyro_sample.py          # re-run to merge MIST masses
```

## Loading the sample
Always use the helper — naive `pd.read_csv` corrupts 19-digit Gaia IDs:
```python
from scripts.gyro_sample import load_gyro_sample, dedupe_by_gaia
sample = load_gyro_sample()           # 5083 rows, 23 cols
unique = dedupe_by_gaia(sample)       # ~4037 unique stars
```

## Key columns
- `age_gyr` — the age column to use for all analysis (cluster age or
  asteroseismic age depending on `age_source`)
- `prot_d` — rotation period in days
- `teff_k` — effective temperature in K
- `prot_source` — measurement technique: `"spot_modulation"`, `"asteroseismic_splitting"`, or per-paper label
- `age_source` — `"cluster"`, `"asteroseismic_hall_2021"`, `"asteroseismic_legacy"`, or `"asteroseismic_garcia2014"`
- `age_unc_gyr` — age uncertainty (null for cluster stars)
- `mass_msun`, `mass_unc_msun`, `mass_source` — stellar mass + uncertainty + provenance (`"basta"` or `"mist_isochrone"`)
- `feh`, `logg`, `radius_rsun` — BASTA model parameters (field stars) or adopted values (cluster stars)
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
- García 2014: 293 stars, 253 genuinely new (40 overlap Hall by KIC).
  Prot is surface spot modulation; ages are Chaplin 2014 grid-based
  (~20-30% precision vs ~10% for Hall/LEGACY BASTA). Dedup prefers
  Hall > LEGACY > García for overlapping KICs.
- Cluster ages are point estimates with no uncertainty in this schema;
  field stars carry `age_unc_gyr`
- Modeling-ready count (age>2 Gyr, G-dwarf, non-null Prot AND mass):
  100 pre-dedup, 73 deduped (44 García + 18 LEGACY + 11 Hall)
  With MIST cluster masses: ~128 expected (73 field + ~55 cluster G dwarfs)
- MIST mass interpolation requires local grid (~500 MB); `build_gyro_sample.py`
  gracefully skips if `cluster_masses_mist.csv` is absent
