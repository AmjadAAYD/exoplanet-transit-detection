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
