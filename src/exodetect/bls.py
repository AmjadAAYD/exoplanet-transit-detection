"""Box Least Squares transit search, including iterative multi-planet recovery.

A single BLS run finds the strongest periodic box-shaped dip in a light
curve. A multi-planet system like TRAPPIST-1 needs the transits of the
strongest signal masked out before the next-strongest signal becomes
visible, otherwise every run just re-finds the same dominant planet (or
a harmonic/alias of it). This module implements that mask-and-repeat loop.
"""

from dataclasses import dataclass

import numpy as np
from astropy import units as u
from astropy.timeseries import BoxLeastSquares


@dataclass
class BLSDetection:
    period: float  # days
    duration: float  # days
    t0: float  # days, same time system as input
    depth: float
    power: float
    snr: float


def _default_duration_grid(min_period: float) -> np.ndarray:
    """Candidate transit durations (days), capped below the shortest period searched.

    Spans roughly 20 minutes to 3 hours, which covers everything from
    compact rocky-planet systems (TRAPPIST-1: 36-62 min) up to longer
    transits around larger or more distant hosts, without letting a
    duration exceed a meaningful fraction of the period itself.
    """
    grid = np.array([0.02, 0.03, 0.05, 0.08, 0.10, 0.125])
    return grid[grid < 0.5 * min_period]


def _build_period_grid(
    time: np.ndarray,
    min_period: float,
    max_period: float,
    n_oversample: float = 5.0,
    max_grid_points: int = 200_000,
) -> np.ndarray:
    """Build a period grid oversampled relative to the natural frequency
    resolution of the observing baseline (1/baseline), rather than using
    astropy's BoxLeastSquares.autopower default.

    autopower's frequency step scales as frequency_factor * min(duration)
    / baseline**2. That is fine for a single-quarter or single-sector
    baseline, but for a multi-year stitched baseline (Kepler-90, several
    years) combined with a short minimum duration (tens of minutes), it
    produces tens of millions of grid points and effectively hangs. This
    grid instead scales with 1/baseline, the standard frequency resolution
    for a periodic search, oversampled by n_oversample, and stays bounded
    by max_grid_points regardless of baseline or duration.
    """
    baseline = np.max(time) - np.min(time)
    df = 1.0 / (n_oversample * baseline)
    f_min = 1.0 / max_period
    f_max = 1.0 / min_period
    n_freq = int(np.ceil((f_max - f_min) / df))
    if n_freq > max_grid_points:
        df = (f_max - f_min) / max_grid_points
        n_freq = max_grid_points
    freqs = f_min + df * np.arange(1, n_freq + 1)
    return np.sort(1.0 / freqs)


def run_bls(
    time: np.ndarray,
    flux: np.ndarray,
    min_period: float,
    max_period: float,
    duration_grid: np.ndarray = None,
    n_oversample: float = 5.0,
):
    """Run a single BLS search over a period range, return the model and best-fit result.

    n_oversample controls period-grid density relative to the natural
    frequency resolution of the observing baseline (higher = finer grid
    = slower but less alias risk). See _build_period_grid for why this
    replaces astropy's autopower.
    """
    if duration_grid is None:
        duration_grid = _default_duration_grid(min_period)

    model = BoxLeastSquares(time * u.day, flux)
    period_grid = _build_period_grid(time, min_period, max_period, n_oversample=n_oversample)
    periodogram = model.power(period_grid * u.day, duration_grid * u.day)
    best_idx = np.argmax(periodogram.power)
    stats = model.compute_stats(
        periodogram.period[best_idx],
        periodogram.duration[best_idx],
        periodogram.transit_time[best_idx],
    )
    depth_value, depth_uncertainty = stats["depth"]
    snr = depth_value / depth_uncertainty if depth_uncertainty > 0 else 0.0
    detection = BLSDetection(
        period=periodogram.period[best_idx].to(u.day).value,
        duration=periodogram.duration[best_idx].to(u.day).value,
        t0=periodogram.transit_time[best_idx].to(u.day).value,
        depth=depth_value,
        power=periodogram.power[best_idx],
        snr=snr,
    )
    return periodogram, detection


def mask_transits(time: np.ndarray, detection: BLSDetection, pad_factor: float = 1.5) -> np.ndarray:
    """Boolean mask, True for cadences NOT in transit for the given detection.

    pad_factor widens the masked window slightly beyond the fitted duration
    so ingress/egress points near the model edges are still excluded.
    """
    phase = ((time - detection.t0 + 0.5 * detection.period) % detection.period) - 0.5 * detection.period
    half_width = 0.5 * detection.duration * pad_factor
    return np.abs(phase) > half_width


def iterative_bls_search(
    time: np.ndarray,
    flux: np.ndarray,
    n_iterations: int,
    min_period: float,
    max_period: float,
    min_snr: float | None = None,
    duration_grid: np.ndarray = None,
    n_oversample: float = 5.0,
):
    """Run BLS, mask the detected transits, repeat, up to n_iterations times.

    min_snr is an optional early-stop gate. Leave it as None (the default)
    for noisy per-cadence data, faint targets can have genuine detections
    with naive depth/depth-uncertainty SNR well under 6-7, so gating hides
    real signals rather than rejecting noise. Prefer validating each
    detection's period against a published catalog instead of trusting
    this SNR number alone.

    Returns a list of BLSDetection, strongest (most significant) first.
    """
    t = np.asarray(time, dtype=float)
    f = np.asarray(flux, dtype=float)
    detections = []

    for _ in range(n_iterations):
        if len(t) < 100:
            break
        _, detection = run_bls(
            t, f,
            min_period=min_period,
            max_period=max_period,
            duration_grid=duration_grid,
            n_oversample=n_oversample,
        )
        if min_snr is not None and detection.snr < min_snr:
            break
        detections.append(detection)
        keep = mask_transits(t, detection)
        t, f = t[keep], f[keep]

    return detections
