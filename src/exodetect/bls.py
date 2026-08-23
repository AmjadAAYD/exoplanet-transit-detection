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


def _effective_frequency_factor(
    time: np.ndarray,
    min_period: float,
    max_period: float,
    duration_grid: np.ndarray,
    frequency_factor: float,
    max_grid_points: int,
) -> float:
    """Raise frequency_factor only as far as needed to keep the period grid tractable.

    astropy's BoxLeastSquares.autoperiod sets its frequency step to
    df = frequency_factor * min(duration) / baseline**2 (see astropy's
    timeseries/periodograms/bls/core.py). That duration-aware spacing is
    correct and necessary: a narrow transit needs finer period sampling
    to avoid drifting out of phase over many cycles, which is exactly why
    a naive 1/baseline-only grid (tried first, see git history) silently
    lost TRAPPIST-1's known periods by under-resolving them.

    The problem is only that this formula's grid size can explode for a
    long, multi-quarter/multi-year baseline (e.g. Kepler-90's ~4 years)
    combined with a short minimum duration, producing tens of millions of
    points. Rather than replace astropy's formula, this only increases
    frequency_factor, and only when the requested value would exceed
    max_grid_points, which coarsens the correct duration-aware grid
    rather than substituting a differently-shaped one.
    """
    baseline = np.max(time) - np.min(time)
    min_duration = np.min(duration_grid)
    df = frequency_factor * min_duration / baseline**2
    f_min, f_max = 1.0 / max_period, 1.0 / min_period
    n_freq = (f_max - f_min) / df
    if n_freq <= max_grid_points:
        return frequency_factor
    required_df = (f_max - f_min) / max_grid_points
    return required_df * baseline**2 / min_duration


def run_bls(
    time: np.ndarray,
    flux: np.ndarray,
    min_period: float,
    max_period: float,
    duration_grid: np.ndarray = None,
    frequency_factor: float = 5.0,
    max_grid_points: int = 200_000,
):
    """Run a single BLS search over a period range, return the model and best-fit result.

    frequency_factor controls period-grid density (astropy's autopower
    convention: higher = coarser grid = faster but more alias risk).
    Automatically raised above the requested value, but never lowered,
    if the resulting grid would exceed max_grid_points, see
    _effective_frequency_factor.
    """
    if duration_grid is None:
        duration_grid = _default_duration_grid(min_period)

    effective_ff = _effective_frequency_factor(
        time, min_period, max_period, duration_grid, frequency_factor, max_grid_points,
    )

    model = BoxLeastSquares(time * u.day, flux)
    periodogram = model.autopower(
        duration_grid * u.day,
        minimum_period=min_period * u.day,
        maximum_period=max_period * u.day,
        frequency_factor=effective_ff,
    )
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
    frequency_factor: float = 5.0,
    max_grid_points: int = 200_000,
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
            frequency_factor=frequency_factor,
            max_grid_points=max_grid_points,
        )
        if min_snr is not None and detection.snr < min_snr:
            break
        detections.append(detection)
        keep = mask_transits(t, detection)
        t, f = t[keep], f[keep]

    return detections
