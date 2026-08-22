"""Match BLS detections against published catalog periods.

BLS can lock onto a harmonic or alias of the true period (e.g. finding
half or double the real orbital period) rather than the period itself,
so a detection is checked against small integer multiples/divisors of
each catalog period, not just a direct comparison.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class ValidationResult:
    pl_name: str
    published_period: float
    recovered_period: float | None
    harmonic_factor: float | None  # recovered = published * harmonic_factor
    percent_error: float | None
    matched: bool


def match_detections_to_catalog(
    detections,
    catalog_periods: dict,
    rel_tolerance: float = 0.01,
    harmonics=(1, 2, 0.5, 3, 1 / 3),
):
    """Greedily match each catalog planet to the closest BLS detection.

    For each catalog period, checks every detection against every
    candidate harmonic factor and keeps the closest match within
    rel_tolerance. Each detection can only be matched once, closest
    matches are assigned first so two planets don't both claim the
    same detection.
    """
    candidates = []
    for pl_name, published in catalog_periods.items():
        for detection in detections:
            for h in harmonics:
                expected = published * h
                rel_err = abs(detection.period - expected) / expected
                if rel_err <= rel_tolerance:
                    candidates.append((rel_err, pl_name, published, detection, h))

    candidates.sort(key=lambda c: c[0])

    matched_planets = set()
    matched_detections = set()
    results = {}
    for rel_err, pl_name, published, detection, h in candidates:
        if pl_name in matched_planets or id(detection) in matched_detections:
            continue
        matched_planets.add(pl_name)
        matched_detections.add(id(detection))
        results[pl_name] = ValidationResult(
            pl_name=pl_name,
            published_period=published,
            recovered_period=detection.period,
            harmonic_factor=h,
            percent_error=100 * (detection.period - published) / published,
            matched=True,
        )

    for pl_name, published in catalog_periods.items():
        if pl_name not in results:
            results[pl_name] = ValidationResult(
                pl_name=pl_name,
                published_period=published,
                recovered_period=None,
                harmonic_factor=None,
                percent_error=None,
                matched=False,
            )

    return [results[name] for name in catalog_periods]
