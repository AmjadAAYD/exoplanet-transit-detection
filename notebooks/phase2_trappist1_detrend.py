"""Phase 2: detrend TRAPPIST-1's light curve and confirm it cleans up well."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import lightkurve as lk
import matplotlib.pyplot as plt

from exodetect.detrend import detrend_light_curve

print("Downloading raw TRAPPIST-1 light curve (K2 Campaign 12, 60s cadence)...")
search = lk.search_lightcurve("TRAPPIST-1", mission="K2", exptime=60, author="K2")
raw = search.download()
print(f"Raw cadences: {len(raw.time)}")

flat = detrend_light_curve(raw)
print(f"Cleaned cadences: {len(flat.time)}")
print(f"Flux range after flatten: {flat.flux.min():.4f} to {flat.flux.max():.4f}")

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)

fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
raw.plot(ax=axes[0])
axes[0].set_title("Raw (K2 Campaign 12)")
flat.plot(ax=axes[1])
axes[1].set_title("Detrended: NaN removal, quality filter, Savitzky-Golay flatten, sigma-clip")
fig.suptitle("TRAPPIST-1: raw vs detrended")
fig.tight_layout()
out_path = os.path.join(out_dir, "trappist1_detrended.png")
fig.savefig(out_path, dpi=150)
print(f"Saved comparison plot to {out_path}")
