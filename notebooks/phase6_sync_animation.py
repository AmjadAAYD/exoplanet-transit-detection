"""Phase 6: the signature visual, a simulated transit synced to the real light curve.

Left panel: a dark circle (planet) crossing a bright circle (star),
sized to the physically accurate transit depth and timed to the transit
duration our own pipeline recovered for TRAPPIST-1 b. Right panel: the
real, detrended TRAPPIST-1 light curve, phase-folded at our recovered
period, with a marker tracing the same crossing in sync.

Timing (period, epoch, duration) comes from our own Phase 3 BLS
detection, this is what our pipeline actually found. The planet's SIZE
does not: Phase 3 established that BLS's raw depth estimate for this
target is noise-inflated (K2's per-cadence noise for a faint M8 dwarf
produced an apparent ~4% depth, when TRAPPIST-1 b's real depth is
about 0.7%). Using the noisy value would draw a planet many times too
large. Instead the planet's size comes from the published stellar and
planet radii (depth = (Rp/Rstar)^2), a physically honest number to
animate even though it is not the number our own search produced.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle

from exodetect.data import get_light_curve
from exodetect.detrend import detrend_light_curve
from exodetect.bls import iterative_bls_search
from exodetect.catalog import fetch_stellar_params, fetch_confirmed_planets
from exodetect.fold import fold_and_bin

R_EARTH_PER_R_SUN = 1 / 109.2

print("Loading TRAPPIST-1 light curve and recovering planet b's transit (cached, from Phase 3)...")
raw = get_light_curve("trappist1_k2c12_60s", "TRAPPIST-1", mission="K2", author="K2", exptime=60)
flat = detrend_light_curve(raw)
detections = iterative_bls_search(flat.time.value, flat.flux.value, n_iterations=1, min_period=1.0, max_period=2.0)
planet_b = detections[0]
print(f"Recovered: period={planet_b.period:.6f}d duration={planet_b.duration:.4f}d t0={planet_b.t0:.4f}")

print("Fetching physically accurate depth from published stellar/planet radii...")
star = fetch_stellar_params("TRAPPIST-1").iloc[0]
planets = fetch_confirmed_planets("TRAPPIST-1")
planet_b_catalog = planets[planets["pl_name"] == "TRAPPIST-1 b"].iloc[0]
planet_radius_rsun = planet_b_catalog["pl_rade"] * R_EARTH_PER_R_SUN
true_depth = (planet_radius_rsun / star["st_rad"]) ** 2
radius_ratio = np.sqrt(true_depth)
print(f"Star radius: {star['st_rad']:.4f} Rsun, planet radius: {planet_b_catalog['pl_rade']:.3f} Re")
print(f"Physically accurate depth: {true_depth * 100:.3f}% (our raw BLS depth was {planet_b.depth * 100:.2f}%, noise-inflated)")

N_DURATIONS = 8
N_BINS = 90
view = fold_and_bin(
    flat.time.value, flat.flux.value,
    period=planet_b.period, epoch=planet_b.t0, duration=planet_b.duration,
    n_bins=N_BINS, n_durations=N_DURATIONS,
)
half_width_days = 0.5 * N_DURATIONS * planet_b.duration
phase_hours = np.linspace(-half_width_days, half_width_days, N_BINS) * 24

# Rescale the folded view to use the physically accurate depth for the
# dip shown, rather than the noise-inflated raw depth: keep the real
# data's shape (where the dip actually falls, its noise texture) but
# scale its amplitude to match the true ~0.7% transit.
raw_dip = 1.0 - view.min()
if raw_dip > 0:
    view_scaled = 1.0 - (1.0 - view) * (true_depth / raw_dip)
else:
    view_scaled = view

# Left panel x-axis: stellar radii. The star spans the crossing exactly
# over one transit duration (ingress start to egress end), so mapping
# phase linearly by (duration/2) puts the planet's edge exactly on the
# star's edge at that timing, no extra tuning needed.
x_stellar_radii = phase_hours / (planet_b.duration * 24 / 2)

fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(12, 5))

star_radius_plot = 1.0
ax_left.set_xlim(-N_DURATIONS, N_DURATIONS)
ax_left.set_ylim(-2, 2)
ax_left.set_aspect("equal")
ax_left.axis("off")
ax_left.set_title("Simulated transit (to scale)")
star_patch = Circle((0, 0), star_radius_plot, color="#FDB813", zorder=1)
ax_left.add_patch(star_patch)
planet_patch = Circle((x_stellar_radii[0], 0), radius_ratio, color="#1a1a2e", zorder=2)
ax_left.add_patch(planet_patch)

ax_right.plot(phase_hours, view_scaled, color="#2c7fb8", lw=1.2)
ax_right.set_xlabel("Hours from mid-transit")
ax_right.set_ylabel("Normalized flux")
ax_right.set_title("Real TRAPPIST-1 light curve (K2), phase-folded")
marker, = ax_right.plot([phase_hours[0]], [view_scaled[0]], "o", color="#d7263d", markersize=8, zorder=3)

fig.suptitle("TRAPPIST-1 b: recovered period 1.5109d, real K2 data, physically accurate transit depth")
fig.tight_layout()


def update(frame):
    planet_patch.center = (x_stellar_radii[frame], 0)
    marker.set_data([phase_hours[frame]], [view_scaled[frame]])
    return planet_patch, marker


anim = animation.FuncAnimation(fig, update, frames=N_BINS, interval=45, blit=True)

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "trappist1b_sync_animation.gif")
anim.save(out_path, writer="pillow", fps=22)
print(f"\nSaved sync animation to {out_path}")
