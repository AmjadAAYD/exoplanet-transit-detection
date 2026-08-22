"""Phase 3 (cont.): iterative BLS on Kepler-90, validated against its 8 published planets.

Kepler-90's outermost planet (h) has a 331.6-day period, so this needs
every available Kepler quarter stitched together, not a single quarter
like TRAPPIST-1's K2 campaign. Transit durations scale up with period
too, so the duration grid is widened well past what TRAPPIST-1 needed.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib.pyplot as plt

from exodetect.pipeline import run_target_validation, print_validation_table

print("Downloading (or loading cached) and detrending Kepler-90...")
run = run_target_validation(
    target_name="Kepler-90",
    cache_key="kepler90_kepler_lc",
    catalog_hostname="KOI-351",  # Kepler-90's host is archived under its KOI designation
    mission="Kepler",
    author="Kepler",
    exptime=1800,  # 29.4 min long cadence, standard for the full multi-year Kepler baseline
    stitch=True,
    window_length=73,  # ~1.5 days: above the longest expected transit duration, below the shortest orbital period (7.0d)
    duration_grid=np.array([0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]),
    min_period=3.0,
    max_period=350.0,  # covers Kepler-90h (331.6d) with margin
    n_iterations=9,  # 8 known planets plus one buffer iteration
)
print(f"Cleaned cadences: {len(run.light_curve.time)}")

print("\nPublished Kepler-90 planet periods (NASA Exoplanet Archive):")
print(run.catalog_df[["pl_name", "pl_orbper"]].to_string(index=False))

print(f"\nFound {len(run.detections)} detections")
for i, d in enumerate(run.detections):
    print(f"  [{i}] period={d.period:.6f}d duration={d.duration:.4f}d depth={d.depth:.6f} snr={d.snr:.5f}")

print_validation_table(run)

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)

matched_periods = {r.recovered_period for r in run.results if r.matched}
fig, ax = plt.subplots(figsize=(10, 5))
periods = [d.period for d in run.detections]
snrs = [d.snr for d in run.detections]
colors = ["tab:green" if p in matched_periods else "tab:red" for p in periods]
ax.bar(range(len(run.detections)), snrs, tick_label=[f"{p:.2f}d" for p in periods], color=colors)
ax.set_ylabel("Depth SNR")
ax.set_xlabel("Recovered period")
ax.set_title("Kepler-90: BLS detections by iteration (green: matched a known planet, red: did not)")
fig.tight_layout()
out_path = os.path.join(out_dir, "kepler90_bls_detections.png")
fig.savefig(out_path, dpi=150)
print(f"\nSaved detection summary plot to {out_path}")
