"""Small helpers shared across scripts/fetch_*.py.

Each published catalog has two access paths:
  1. VizieR TAP (primary, reproducible from the authoritative source)
  2. A GitHub FITS/CSV mirror (fallback, for sandboxes that block CDS)

`fetch_catalog` tries TAP first and transparently falls back to the mirror on
network errors, or when `--mirror` is requested.
"""
from __future__ import annotations

import io
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

VIZIER_TAP_URL = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap"


@dataclass(frozen=True)
class CatalogSpec:
    """Where to find one published rotation catalog."""
    name: str                # short slug, e.g. "curtis_2020_table5"
    vizier_table: str        # e.g. 'J/ApJ/904/140/table5'
    mirror_url: str          # raw.githubusercontent.com URL to FITS/CSV mirror
    mirror_format: Literal["fits", "csv"] = "fits"


def _fetch_tap(spec: CatalogSpec) -> pd.DataFrame:
    from astroquery.utils.tap.core import TapPlus

    tap = TapPlus(url=VIZIER_TAP_URL)
    job = tap.launch_job_async(f'SELECT * FROM "{spec.vizier_table}"')
    return job.get_results().to_pandas()


def _fetch_mirror(spec: CatalogSpec) -> pd.DataFrame:
    with urllib.request.urlopen(spec.mirror_url, timeout=60) as resp:
        buf = io.BytesIO(resp.read())
    if spec.mirror_format == "fits":
        from astropy.table import Table
        return Table.read(buf, format="fits").to_pandas()
    return pd.read_csv(buf)


def fetch_catalog(spec: CatalogSpec, *, use_mirror: bool = False
                  ) -> tuple[pd.DataFrame, str]:
    """Return (dataframe, source_tag) for the requested catalog."""
    if use_mirror:
        return _fetch_mirror(spec), "github-mirror"
    try:
        return _fetch_tap(spec), "vizier-tap"
    except (urllib.error.URLError, ConnectionError, OSError) as err:
        print(f"[warn] VizieR TAP unreachable ({err}); falling back to mirror.",
              file=sys.stderr)
    except Exception as err:
        print(f"[warn] TAP query failed ({type(err).__name__}: {err}); "
              "falling back to mirror.", file=sys.stderr)
    return _fetch_mirror(spec), "github-mirror"


def decode_bytes(df: pd.DataFrame) -> pd.DataFrame:
    """FITS string columns often arrive as bytes — normalize to str."""
    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna().head(1)
        if len(sample) and isinstance(sample.iloc[0], bytes):
            df[col] = df[col].str.decode("utf-8", errors="replace")
    return df


def write_csv(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
