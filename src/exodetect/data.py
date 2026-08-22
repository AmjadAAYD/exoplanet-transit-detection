"""Light curve retrieval from the MAST archive via lightkurve."""

import os

import lightkurve as lk

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")


def search_target(target_name: str, mission: str | None = None):
    """Search MAST for all available light curve products for a target.

    Returns the lightkurve SearchResult so callers can inspect what's
    actually available (author, mission, cadence, quarter/sector) before
    committing to a download.
    """
    return lk.search_lightcurve(target_name, mission=mission)


def download_light_curve(target_name: str, mission: str | None = None, **kwargs):
    """Download and return a single stitched LightCurve for a target.

    kwargs are forwarded to SearchResult.download() / download_all() as
    needed (e.g. author, exptime, quarter, sector).
    """
    search = search_target(target_name, mission=mission)
    if len(search) == 0:
        raise ValueError(f"No light curve products found for {target_name!r} (mission={mission!r})")
    return search, search.download_all(**kwargs)


def get_light_curve(
    cache_key: str,
    target_name: str,
    mission: str | None = None,
    author: str | None = None,
    exptime=None,
):
    """Download a single light curve, or load it from a local cache if present.

    MAST's search API can be slow or briefly unavailable; caching the raw
    FITS locally after a successful download means later runs (including
    repeated debugging in this project) don't re-hit the network at all.
    cache_key should be a filesystem-safe name unique to this target/mission
    combination, e.g. "trappist1_k2c12_60s".
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}.fits")

    if os.path.exists(cache_path):
        return lk.read(cache_path)

    search = lk.search_lightcurve(target_name, mission=mission, author=author, exptime=exptime)
    if len(search) == 0:
        raise ValueError(f"No light curve products found for {target_name!r} (mission={mission!r})")
    lc = search.download()
    lc.to_fits(path=cache_path, overwrite=True)
    return lc
