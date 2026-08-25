"""Phase 5: run the pipeline on a batch of real unconfirmed TESS Objects of Interest.

IMPORTANT: this pipeline can flag a transit-like signal, it cannot
confirm a new planet. Confirmation needs follow-up spectroscopy or
radial-velocity data outside the scope of this project. Every result
below is a candidate flag, not a discovery.

For each TOI: download its TESS light curve, detrend, run our own BLS
search bounded around the catalog's reported period to independently
check whether our pipeline recovers the same signal (rather than just
trusting the catalog), then physically characterize whatever depth we
end up using (our own if recovered, the catalog's if not) against the
host star's parameters, with uncertainty carried through via Monte
Carlo sampling rather than presented as a single precise number.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

from exodetect.catalog import fetch_toi_candidates
from exodetect.data import get_light_curve
from exodetect.detrend import detrend_light_curve, choose_flatten_window
from exodetect.bls import run_bls
from exodetect.physics import characterize

TESS_CADENCE_DAYS = 120 / 86400  # 2-minute SPOC cadence, the most common TESS product
N_CANDIDATES = 25

print(f"Fetching {N_CANDIDATES} TESS Objects of Interest still flagged as candidates...")
tois = fetch_toi_candidates(limit=N_CANDIDATES, max_period=15.0)
print(f"Got {len(tois)} candidates")

rows = []

for i, row in enumerate(tois.itertuples()):
    label = f"TOI-{row.toi}"
    print(f"\n[{i+1}/{len(tois)}] {label} (TIC {row.tid}, catalog period {row.pl_orbper:.4f}d)...", flush=True)
    try:
        lc = get_light_curve(f"toi_tic{row.tid}", f"TIC {row.tid}", mission="TESS", author="SPOC")
        duration_days = row.pl_trandurh / 24.0
        window = choose_flatten_window(row.pl_orbper, duration_days, TESS_CADENCE_DAYS)
        flat = detrend_light_curve(lc, window_length=window)

        duration_grid = np.array([0.5, 0.75, 1.0, 1.25, 1.5]) * duration_days
        _, detection = run_bls(
            flat.time.value, flat.flux.value,
            min_period=row.pl_orbper * 0.8,
            max_period=row.pl_orbper * 1.2,
            duration_grid=duration_grid,
        )
        rel_err = abs(detection.period - row.pl_orbper) / row.pl_orbper
        recovered = rel_err < 0.01

        if recovered:
            depth = detection.depth
            depth_source = "our BLS"
        else:
            depth = row.pl_trandep / 1e6 if not pd.isna(row.pl_trandep) else np.nan
            depth_source = "catalog (not independently recovered)"

        if pd.isna(depth) or depth <= 0:
            raise ValueError("no usable depth from either our pipeline or the catalog")

        # `x or default` is wrong here: pandas stores a missing numeric as
        # NaN, and NaN is truthy in Python, so the fallback would never
        # trigger and NaN would silently propagate through the whole
        # Monte Carlo characterization (caught directly: two candidates
        # came back with NaN radius and temperature because of this).
        rad_err = row.st_raderr1 if not pd.isna(row.st_raderr1) else 0.1 * row.st_rad
        teff_err = row.st_tefferr1 if not pd.isna(row.st_tefferr1) else 100.0
        logg_err = row.st_loggerr1 if not pd.isna(row.st_loggerr1) else 0.1

        char = characterize(
            depth=depth,
            period_days=row.pl_orbper,
            star_radius_rsun=row.st_rad, star_radius_err_rsun=abs(rad_err),
            star_teff_k=row.st_teff, star_teff_err_k=abs(teff_err),
            star_logg=row.st_logg, star_logg_err=abs(logg_err),
        )

        rows.append(dict(
            toi=label, tid=row.tid, catalog_period=row.pl_orbper,
            our_period=detection.period, recovered_by_our_pipeline=recovered,
            depth_source=depth_source,
            planet_radius_re_median=char.planet_radius_re[0],
            planet_radius_re_lo=char.planet_radius_re[1],
            planet_radius_re_hi=char.planet_radius_re[2],
            semi_major_axis_au_median=char.semi_major_axis_au[0],
            semi_major_axis_au_lo=char.semi_major_axis_au[1],
            semi_major_axis_au_hi=char.semi_major_axis_au[2],
            eq_temp_k_median=char.eq_temp_k[0],
            eq_temp_k_lo=char.eq_temp_k[1],
            eq_temp_k_hi=char.eq_temp_k[2],
            hz_verdict=char.hz_verdict,
            status="ok",
        ))
        print(f"  recovered={recovered} (our period={detection.period:.4f}d, rel_err={rel_err:.4f}), "
              f"radius={char.planet_radius_re[0]:.2f} Re, Teq={char.eq_temp_k[0]:.0f}K, hz={char.hz_verdict}", flush=True)
    except Exception as e:
        rows.append(dict(toi=label, tid=row.tid, catalog_period=row.pl_orbper, status=f"failed: {e}"))
        print(f"  FAILED: {e}", flush=True)

results_df = pd.DataFrame(rows)
out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(out_dir, exist_ok=True)
results_df.to_csv(os.path.join(out_dir, "toi_discovery_table.csv"), index=False)

n_ok = (results_df["status"] == "ok").sum()
n_recovered = results_df.get("recovered_by_our_pipeline", pd.Series(dtype=bool)).sum()
print(f"\n=== Summary: {n_ok}/{len(results_df)} characterized, {n_recovered} independently recovered by our own BLS ===")
print("\nCAVEAT: this pipeline flags transit-like signals. It does not confirm planets. "
      "Confirmation requires follow-up spectroscopy or radial-velocity data outside the scope of this project.")

docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
ok_df = results_df[results_df["status"] == "ok"].copy()
if len(ok_df) > 0:
    display_cols = ["toi", "catalog_period", "recovered_by_our_pipeline", "depth_source",
                     "planet_radius_re_median", "planet_radius_re_lo", "planet_radius_re_hi",
                     "eq_temp_k_median", "hz_verdict"]
    ok_df[display_cols].round(3).to_csv(os.path.join(docs_dir, "discovery_table.csv"), index=False)
    print(f"\nSaved discovery table to {os.path.join(docs_dir, 'discovery_table.csv')}")
