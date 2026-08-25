"""Export curated per-target data for the showcase site's interactive demo.

Reuses the existing pipeline end to end (no new detection/physics logic):
run_target_validation() for the three validation systems, and the same
get_light_curve + detrend + run_bls + characterize chain phase5 used for
the curated TOI subset. Each target's raw MAST data is already cached
locally from earlier phases, so this only re-runs cheap, fast steps.

Output: one JSON per target under site/public/data/, plus a manifest.
Deliberately curated and pre-computed, not a live cold-start lookup, see
the plan (site is showcase-first, demo picks from a known list) for why.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

from exodetect.pipeline import run_target_validation
from exodetect.data import get_light_curve
from exodetect.detrend import detrend_light_curve, choose_flatten_window
from exodetect.bls import run_bls
from exodetect.fold import fold_and_bin
from exodetect.catalog import fetch_toi_candidates
from exodetect.physics import characterize

TESS_CADENCE_DAYS = 120 / 86400
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "public", "data")
os.makedirs(OUT_DIR, exist_ok=True)


def downsample_periodogram(period, power, max_points=1500):
    """Max-pool (period, power) down to max_points bins, keeps peaks visible."""
    period = np.asarray(period)
    power = np.asarray(power)
    if len(period) <= max_points:
        return period.tolist(), power.tolist()
    order = np.argsort(period)
    period, power = period[order], power[order]
    edges = np.linspace(0, len(period), max_points + 1).astype(int)
    out_period, out_power = [], []
    for i in range(max_points):
        lo, hi = edges[i], edges[i + 1]
        if hi <= lo:
            continue
        seg_power = power[lo:hi]
        peak_idx = lo + int(np.argmax(seg_power))
        out_period.append(float(period[peak_idx]))
        out_power.append(float(power[peak_idx]))
    return out_period, out_power


def export_validation_target(slug, name, category, headline, showcase_planet, **cfg):
    print(f"\n=== {name} ===", flush=True)
    print("  running full validation pipeline (catalog fetch + iterative BLS)...", flush=True)
    run = run_target_validation(**cfg)
    print(f"  done: {len(run.detections)} detections, {sum(1 for r in run.results if r.matched)} matched", flush=True)
    matched = [r for r in run.results if r.matched]
    # Showcase a specific named planet (chosen for the story, e.g. the
    # historically significant Kepler-186f), not just whichever matched
    # planet happens to have the most transits.
    best = next(r for r in matched if r.pl_name == showcase_planet)
    detection = next(d for d in run.detections if d.period == best.recovered_period)

    t, f = run.light_curve.time.value, run.light_curve.flux.value
    print("  folding local view...", flush=True)
    view = fold_and_bin(t, f, detection.period, detection.t0, detection.duration, n_bins=150, n_durations=8)
    phase_hours = np.linspace(-4 * detection.duration, 4 * detection.duration, 150) * 24

    print("  running narrow-bounded BLS for the periodogram chart...", flush=True)
    pg, _ = run_bls(
        t, f,
        min_period=detection.period * 0.9, max_period=detection.period * 1.1,
        duration_grid=np.array([detection.duration]),
    )
    print("  narrow BLS done, downsampling...", flush=True)
    ds_period, ds_power = downsample_periodogram(pg.period.value, np.asarray(pg.power))

    payload = dict(
        slug=slug, name=name, category=category, headline=headline,
        published_period=best.published_period, recovered_period=best.recovered_period,
        error_percent=best.percent_error,
        n_planets_recovered=len(matched), n_planets_total=len(run.results),
        phase_hours=phase_hours.tolist(), folded_flux=view.tolist(),
        periodogram_period=ds_period, periodogram_power=ds_power,
    )
    with open(os.path.join(OUT_DIR, f"{slug}.json"), "w") as fh:
        json.dump(payload, fh)
    print(f"  exported {slug}.json (planet period={detection.period:.4f}d)", flush=True)
    return payload


def export_toi_target(slug, toi_row):
    print(f"\n=== {slug} ===", flush=True)
    tid = int(toi_row["tid"])
    lc = get_light_curve(f"toi_tic{tid}", f"TIC {tid}", mission="TESS", author="SPOC")
    duration_days = toi_row["pl_trandurh"] / 24.0
    window = choose_flatten_window(toi_row["pl_orbper"], duration_days, TESS_CADENCE_DAYS)
    flat = detrend_light_curve(lc, window_length=window)
    t, f = flat.time.value, flat.flux.value

    duration_grid = np.array([0.5, 0.75, 1.0, 1.25, 1.5]) * duration_days
    pg, detection = run_bls(
        t, f,
        min_period=toi_row["pl_orbper"] * 0.8, max_period=toi_row["pl_orbper"] * 1.2,
        duration_grid=duration_grid,
    )
    rel_err = abs(detection.period - toi_row["pl_orbper"]) / toi_row["pl_orbper"]
    recovered = rel_err < 0.01
    depth = detection.depth if recovered else toi_row["pl_trandep"] / 1e6

    view = fold_and_bin(t, f, detection.period, detection.t0, detection.duration, n_bins=150, n_durations=8)
    phase_hours = np.linspace(-4 * detection.duration, 4 * detection.duration, 150) * 24
    ds_period, ds_power = downsample_periodogram(pg.period.value, np.asarray(pg.power))

    rad_err = toi_row["st_raderr1"] if not pd.isna(toi_row["st_raderr1"]) else 0.1 * toi_row["st_rad"]
    teff_err = toi_row["st_tefferr1"] if not pd.isna(toi_row["st_tefferr1"]) else 100.0
    logg_err = toi_row["st_loggerr1"] if not pd.isna(toi_row["st_loggerr1"]) else 0.1
    char = characterize(
        depth=depth, period_days=toi_row["pl_orbper"],
        star_radius_rsun=toi_row["st_rad"], star_radius_err_rsun=abs(rad_err),
        star_teff_k=toi_row["st_teff"], star_teff_err_k=abs(teff_err),
        star_logg=toi_row["st_logg"], star_logg_err=abs(logg_err),
    )

    payload = dict(
        slug=slug, name=f"TOI-{toi_row['toi']}", category="discovery",
        headline=f"{char.hz_verdict}, {char.planet_radius_re[0]:.1f} Earth radii",
        catalog_period=toi_row["pl_orbper"], recovered_period=detection.period,
        recovered_by_pipeline=bool(recovered),
        phase_hours=phase_hours.tolist(), folded_flux=view.tolist(),
        periodogram_period=ds_period, periodogram_power=ds_power,
        planet_radius_re=list(char.planet_radius_re),
        semi_major_axis_au=list(char.semi_major_axis_au),
        eq_temp_k=list(char.eq_temp_k),
        hz_inner_au=char.hz_inner_au, hz_outer_au=char.hz_outer_au,
        hz_verdict=char.hz_verdict,
        caveat="This pipeline flags transit-like signals. It does not confirm planets. "
               "Confirmation requires follow-up spectroscopy or radial-velocity data "
               "outside the scope of this project.",
    )
    with open(os.path.join(OUT_DIR, f"{slug}.json"), "w") as fh:
        json.dump(payload, fh)
    print(f"  exported {slug}.json (recovered={recovered}, verdict={char.hz_verdict})", flush=True)
    return payload


manifest = []

manifest.append(export_validation_target(
    "trappist1", "TRAPPIST-1", "validation", "6 of 7 planets recovered, within 0.033%",
    showcase_planet="TRAPPIST-1 b",
    target_name="TRAPPIST-1", cache_key="trappist1_k2c12_60s", catalog_hostname="TRAPPIST-1",
    mission="K2", author="K2", exptime=60, stitch=False, window_length=401,
    duration_grid=None, min_period=1.0, max_period=20.0, n_iterations=8,
))
manifest.append(export_validation_target(
    "kepler90", "Kepler-90", "validation", "6 of 8 planets recovered, within 0.006%",
    showcase_planet="KOI-351 c",
    target_name="Kepler-90", cache_key="kepler90_kepler_lc", catalog_hostname="KOI-351",
    mission="Kepler", author="Kepler", exptime=1800, stitch=True, window_length=73,
    duration_grid=np.array([0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]),
    min_period=3.0, max_period=350.0, n_iterations=9,
))
manifest.append(export_validation_target(
    "kepler186", "Kepler-186", "validation", "5 of 5 planets recovered, including the habitable-zone Kepler-186f",
    showcase_planet="Kepler-186 f",
    target_name="Kepler-186", cache_key="kepler186_kepler_lc", catalog_hostname="Kepler-186",
    mission="Kepler", author="Kepler", exptime=1800, stitch=True, window_length=49,
    duration_grid=np.array([0.02, 0.05, 0.08, 0.12, 0.18, 0.25]),
    min_period=2.0, max_period=145.0, n_iterations=6,
))

CURATED_TOIS = ["1059.01", "1001.01", "1035.01", "1125.01", "1083.01"]
print(f"\nFetching TOI catalog rows for curated targets: {CURATED_TOIS}", flush=True)
tois = fetch_toi_candidates(limit=25, max_period=15.0)
for toi_num in CURATED_TOIS:
    row = tois[np.isclose(tois["toi"], float(toi_num), atol=1e-6)].iloc[0]
    payload = export_toi_target(f"toi-{toi_num}", row)
    manifest.append(payload)

manifest_out = [
    dict(slug=m["slug"], name=m["name"], category=m["category"], headline=m["headline"])
    for m in manifest
]
with open(os.path.join(OUT_DIR, "manifest.json"), "w") as fh:
    json.dump(manifest_out, fh, indent=2)
print(f"\nExported {len(manifest_out)} targets. Manifest saved to {os.path.join(OUT_DIR, 'manifest.json')}")
