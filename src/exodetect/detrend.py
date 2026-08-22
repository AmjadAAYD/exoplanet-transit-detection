"""Detrending pipeline for raw light curves.

Real light curves carry instrumental drift, momentum-dump artifacts, and
stellar variability that the pre-cleaned Kaggle dataset strips out. This
module removes bad cadences, flattens long-term trends, and clips outliers,
so the result is usable for a transit search without hiding what real data
looks like.
"""

import lightkurve as lk


def detrend_light_curve(
    lc,
    window_length: int = 401,
    sigma: float = 5.0,
):
    """Clean and flatten a raw LightCurve.

    Steps, in order:
    1. Remove NaN flux cadences.
    2. Drop cadences flagged bad by the mission quality bitmask.
    3. Flatten long-term trends with a Savitzky-Golay filter.
    4. Sigma-clip remaining outliers.

    Parameters
    ----------
    lc : lightkurve.LightCurve
        Raw light curve, as returned by exodetect.data.download_light_curve.
    window_length : int
        Savitzky-Golay window length (in cadences), passed to lc.flatten().
        Must be odd and larger than the longest expected transit duration,
        so real transits are not flattened away.
    sigma : float
        Sigma-clipping threshold for outlier removal after flattening.

    Returns
    -------
    lightkurve.LightCurve
        Cleaned, flattened, normalized light curve.
    """
    clean = lc.remove_nans()
    clean = clean.remove_outliers(sigma=sigma)  # first pass, catches gross artifacts pre-flatten
    if hasattr(clean, "quality"):
        clean = clean[clean.quality == 0]

    flat = clean.flatten(window_length=window_length)
    flat = flat.remove_outliers(sigma=sigma)

    return flat
