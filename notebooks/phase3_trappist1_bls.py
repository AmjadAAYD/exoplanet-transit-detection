"""Phase 3: iterative BLS search on TRAPPIST-1, validated against published periods."""

import sys
import os
import time as time_module

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib.pyplot as plt

from exodetect.data import get_light_curve
from exodetect.detrend import detrend_light_curve
from exodetect.bls import iterative_bls_search
from exodetect.validate import match_detections_to_catalog
from exodetect.catalog import fetch_confirmed_planets

print("Downloading (or loading cached) and detrending TRAPPIST-1 light curve...")
raw = get_light_curve("trappist1_k2c12_60s", "TRAPPIST-1", mission="K2", author="K2", exptime=60)
flat = detrend_light_curve(raw)
print(f"Cleaned cadences: {len(flat.time)}")

print("Fetching published TRAPPIST-1 planet periods from NASA Exoplanet Archive...")
catalog_df = fetch_confirmed_planets("TRAPPIST-1")
catalog_periods = dict(zip(catalog_df["pl_name"], catalog_df["pl_orbper"]))
print(catalog_df[["pl_name", "pl_orbper"]].to_string(index=False))

print("\nRunning iterative BLS search (this searches, masks, and repeats)...")
t_start = time_module.time()
detections = iterative_bls_search(
    time=flat.time.value,
    flux=flat.flux.value,
    n_iterations=8,
    min_period=1.0,
    max_period=20.0,
)
elapsed = time_module.time() - t_start
print(f"Found {len(detections)} detections in {elapsed:.1f}s")
for i, d in enumerate(detections):
    print(f"  [{i}] period={d.period:.6f}d duration={d.duration:.4f}d depth={d.depth:.5f} snr={d.snr:.2f}")

print("\nMatching detections to published catalog periods...")
results = match_detections_to_catalog(detections, catalog_periods)

print("\n=== Validation table ===")
print(f"{'Planet':<16}{'Published (d)':<16}{'Recovered (d)':<16}{'Harmonic':<10}{'Error (%)':<12}{'Matched'}")
for r in results:
    rec = f"{r.recovered_period:.6f}" if r.recovered_period is not None else "-"
    harm = f"x{r.harmonic_factor:.3g}" if r.harmonic_factor is not None else "-"
    err = f"{r.percent_error:+.3f}" if r.percent_error is not None else "-"
    print(f"{r.pl_name:<16}{r.published_period:<16.6f}{rec:<16}{harm:<10}{err:<12}{r.matched}")

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)

matched_periods = {r.recovered_period for r in results if r.matched}

fig, ax = plt.subplots(figsize=(10, 5))
periods = [d.period for d in detections]
snrs = [d.snr for d in detections]
colors = ["tab:green" if p in matched_periods else "tab:red" for p in periods]
ax.bar(range(len(detections)), snrs, tick_label=[f"{p:.3f}d" for p in periods], color=colors)
ax.set_ylabel("Depth SNR")
ax.set_xlabel("Recovered period")
ax.set_title("TRAPPIST-1: BLS detections by iteration (green: matched a known planet, red: did not)")
fig.tight_layout()
out_path = os.path.join(out_dir, "trappist1_bls_detections.png")
fig.savefig(out_path, dpi=150)
print(f"\nSaved detection summary plot to {out_path}")
