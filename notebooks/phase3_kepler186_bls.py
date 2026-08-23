"""Phase 3 (cont.): iterative BLS on Kepler-186, validated against its 5 published planets.

Kepler-186f (129.9-day period) is the first Earth-size planet found in a
habitable zone, historically the most significant target in this
validation set. Kepler-186 is a quiet M dwarf, smaller and cooler than
Kepler-90, so transit durations are shorter and orbital periods are all
under 130 days.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib.pyplot as plt

from exodetect.pipeline import run_target_validation, print_validation_table

print("Downloading (or loading cached) and detrending Kepler-186...")
run = run_target_validation(
    target_name="Kepler-186",
    cache_key="kepler186_kepler_lc",
    catalog_hostname="Kepler-186",
    mission="Kepler",
    author="Kepler",
    exptime=1800,
    stitch=True,
    window_length=49,  # ~1.0 day: below the shortest orbital period (3.89d), above expected transit durations for a small M dwarf
    duration_grid=np.array([0.02, 0.05, 0.08, 0.12, 0.18, 0.25]),
    min_period=2.0,
    max_period=145.0,  # covers Kepler-186f (129.9d) with margin
    n_iterations=6,  # 5 known planets plus one buffer iteration
)
print(f"Cleaned cadences: {len(run.light_curve.time)}")

print("\nPublished Kepler-186 planet periods (NASA Exoplanet Archive):")
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
ax.set_title("Kepler-186: BLS detections by iteration (green: matched a known planet, red: did not)")
fig.tight_layout()
out_path = os.path.join(out_dir, "kepler186_bls_detections.png")
fig.savefig(out_path, dpi=150)
print(f"\nSaved detection summary plot to {out_path}")
