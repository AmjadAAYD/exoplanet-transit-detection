"""Phase 1: pull TRAPPIST-1's light curve and confirm the data is real and usable."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import lightkurve as lk
import matplotlib.pyplot as plt

print("Searching MAST for TRAPPIST-1 K2 Campaign 12, 60s cadence...")
search = lk.search_lightcurve("TRAPPIST-1", mission="K2", exptime=60, author="K2")
print(search)

print("\nDownloading...")
lc = search.download()
print(f"\nDownloaded: {lc}")
print(f"Time range: {lc.time.min()} to {lc.time.max()}")
print(f"Number of cadences: {len(lc.time)}")
print(f"Flux column: {lc.flux.unit if hasattr(lc.flux, 'unit') else type(lc.flux)}")

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)

fig, ax = plt.subplots(figsize=(12, 4))
lc.plot(ax=ax)
ax.set_title("TRAPPIST-1 raw light curve — K2 Campaign 12 (60s cadence)")
fig.tight_layout()
out_path = os.path.join(out_dir, "trappist1_raw.png")
fig.savefig(out_path, dpi=150)
print(f"\nSaved raw light curve plot to {out_path}")
