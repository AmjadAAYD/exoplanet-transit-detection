"""Light curve retrieval from the MAST archive via lightkurve."""

import lightkurve as lk


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
