"""End-to-end validation runner: pull, detrend, BLS search, catalog match.

Shared by the per-target validation scripts (TRAPPIST-1, Kepler-90,
Kepler-186f) so each one is just a thin call with target-specific
parameters (period range, duration grid, flatten window) rather than a
duplicated copy of the same ~80 lines.
"""

from dataclasses import dataclass

import numpy as np

from .data import get_light_curve, get_stitched_light_curve
from .detrend import detrend_light_curve
from .bls import iterative_bls_search
from .validate import match_detections_to_catalog
from .catalog import fetch_confirmed_planets


@dataclass
class ValidationRun:
    target_name: str
    catalog_df: "object"
    detections: list
    results: list
    light_curve: "object"


def run_target_validation(
    target_name: str,
    cache_key: str,
    catalog_hostname: str,
    min_period: float,
    max_period: float,
    n_iterations: int,
    duration_grid: np.ndarray,
    window_length: int,
    mission: str = None,
    author: str = None,
    exptime=None,
    stitch: bool = False,
) -> ValidationRun:
    """Run the full pipeline for one validation target and return the results.

    stitch=True downloads and stitches every available quarter/sector,
    needed when a single quarter's baseline is too short to catch a
    transit of the longest-period planet in the system.
    """
    if stitch:
        raw = get_stitched_light_curve(cache_key, target_name, mission=mission, author=author, exptime=exptime)
    else:
        raw = get_light_curve(cache_key, target_name, mission=mission, author=author, exptime=exptime)

    flat = detrend_light_curve(raw, window_length=window_length)

    catalog_df = fetch_confirmed_planets(catalog_hostname)
    catalog_periods = dict(zip(catalog_df["pl_name"], catalog_df["pl_orbper"]))

    detections = iterative_bls_search(
        time=flat.time.value,
        flux=flat.flux.value,
        n_iterations=n_iterations,
        min_period=min_period,
        max_period=max_period,
        duration_grid=duration_grid,
    )

    results = match_detections_to_catalog(detections, catalog_periods)

    return ValidationRun(
        target_name=target_name,
        catalog_df=catalog_df,
        detections=detections,
        results=results,
        light_curve=flat,
    )


def print_validation_table(run: ValidationRun):
    print(f"\n=== Validation table: {run.target_name} ===")
    print(f"{'Planet':<16}{'Published (d)':<16}{'Recovered (d)':<16}{'Harmonic':<10}{'Error (%)':<12}{'Matched'}")
    for r in run.results:
        rec = f"{r.recovered_period:.6f}" if r.recovered_period is not None else "-"
        harm = f"x{r.harmonic_factor:.3g}" if r.harmonic_factor is not None else "-"
        err = f"{r.percent_error:+.3f}" if r.percent_error is not None else "-"
        print(f"{r.pl_name:<16}{r.published_period:<16.6f}{rec:<16}{harm:<10}{err:<12}{r.matched}")
