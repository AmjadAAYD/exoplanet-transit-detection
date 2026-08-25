"""Queries against the NASA Exoplanet Archive TAP service.

Used to fetch published planet and stellar parameters for validation
targets (confirmed periods to check BLS recovery against) and, later,
stellar radius/mass/luminosity for physical characterization of any
flagged TOI candidates.

Reference: NASA Exoplanet Archive, https://exoplanetarchive.ipac.caltech.edu/
"""

import io

import pandas as pd
import requests

TAP_SYNC_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"


def _tap_query(query: str) -> pd.DataFrame:
    """Run a synchronous ADQL query against the archive TAP service, return a DataFrame."""
    response = requests.get(
        TAP_SYNC_URL,
        params={"query": query, "format": "csv"},
        timeout=30,
    )
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))


def fetch_confirmed_planets(hostname: str) -> pd.DataFrame:
    """Fetch confirmed planet parameters for all planets of a given host star.

    Returns one row per planet (default parameter set only, via default_flag=1)
    with orbital period and its reported uncertainty, plus radius and
    equilibrium temperature where available.
    """
    query = (
        "select pl_name, pl_orbper, pl_orbpererr1, pl_orbpererr2, "
        "pl_rade, pl_radeerr1, pl_radeerr2, pl_eqt "
        f"from ps where hostname='{hostname}' and default_flag=1 "
        "order by pl_orbper asc"
    )
    return _tap_query(query)


def fetch_koi_sample(disposition: str, limit: int, min_period: float = 1.0, max_period: float = 50.0) -> pd.DataFrame:
    """Fetch a sample of Kepler Objects of Interest with a given disposition.

    disposition is one of 'CONFIRMED' or 'FALSE POSITIVE' (the Kepler
    cumulative table's koi_disposition values). Used to build a labeled
    training set for the transit classifier from real archive dispositions,
    not the pre-cleaned Kaggle set. Restricting to min_period/max_period
    keeps the sample to periods short enough that a single Kepler quarter
    captures multiple transits, which keeps per-target download and
    folding cheap.
    """
    query = (
        "select kepid, kepoi_name, koi_disposition, koi_period, koi_time0bk, "
        "koi_duration, koi_depth "
        "from cumulative "
        f"where koi_disposition='{disposition}' "
        f"and koi_period between {min_period} and {max_period} "
        "and koi_time0bk is not null and koi_duration is not null "
        f"order by kepid asc"
    )
    df = _tap_query(query)
    return df.head(limit)


def fetch_stellar_params(hostname: str) -> pd.DataFrame:
    """Fetch stellar parameters (radius, mass, luminosity, Teff) for a host star.

    Returns one row per planet entry (the stellar params are repeated per
    planet in the `ps` table); callers should take the first row or dedupe.
    """
    query = (
        "select hostname, st_rad, st_raderr1, st_raderr2, "
        "st_mass, st_masserr1, st_masserr2, "
        "st_lum, st_lumerr1, st_lumerr2, st_teff "
        f"from ps where hostname='{hostname}' and default_flag=1"
    )
    return _tap_query(query)
