"""Phase-folding a light curve into a fixed-length local view, plus
hand-engineered vetting features extracted from the same folded data.

The local view (fixed-length, binned, centered on the transit) is the
standard input representation for a small transit-classification CNN,
following the general approach of Shallue & Vanderburg's AstroNet. The
hand-engineered features are the honest second baseline: depth,
odd-even depth mismatch, secondary-eclipse depth, and ingress/egress
symmetry are the same signals a human vetter or the Kepler Robovetter
checks, and they are cheap to compute directly from the folded data.
"""

from dataclasses import dataclass

import numpy as np


def fold_and_bin(
    time: np.ndarray,
    flux: np.ndarray,
    period: float,
    epoch: float,
    duration: float,
    n_bins: int = 201,
    n_durations: float = 6.0,
    clip_depth: float = 0.10,
) -> np.ndarray:
    """Fold the light curve at (period, epoch) and bin into a fixed-length local view.

    The view spans n_durations transit durations, centered on the transit,
    so a long-period system and a short-period system produce the same
    shaped input regardless of how many transits are actually observed.
    Empty bins (no cadences fell in them) are filled with 1.0, the
    expected out-of-transit normalized flux, rather than left as NaN.

    clip_depth caps how far flux can dip below 1.0 before binning (default
    10%). Real transiting planets never come close to this: even a
    Jupiter-size planet on a small star is a percent or two. Kepler false
    positives, mostly eclipsing binaries, routinely eclipse 10-80%+. Left
    unclipped, a single near-total-eclipse example dominates training on a
    small dataset (seen directly: one KOI at 84.6% measured depth dragged
    training into a degenerate always-predict-positive CNN and an
    overfit GBM on a 60-example set). Clipping does not remove the
    discriminating signal, an eclipsing binary still reads as a very deep
    dip at the cap, it just stops a single extreme case from dominating
    the gradient.
    """
    flux = np.clip(flux, 1.0 - clip_depth, None)
    phase = ((time - epoch + 0.5 * period) % period) - 0.5 * period
    half_width = 0.5 * n_durations * duration
    bin_edges = np.linspace(-half_width, half_width, n_bins + 1)
    bin_indices = np.digitize(phase, bin_edges) - 1

    binned = np.full(n_bins, np.nan)
    for i in range(n_bins):
        vals = flux[bin_indices == i]
        if len(vals) > 0:
            binned[i] = np.median(vals)

    nan_mask = np.isnan(binned)
    binned[nan_mask] = 1.0
    return binned


@dataclass
class VettingFeatures:
    depth: float
    depth_to_scatter: float
    odd_even_depth_diff: float
    secondary_depth: float
    symmetry_diff: float


def extract_features(
    time: np.ndarray,
    flux: np.ndarray,
    period: float,
    epoch: float,
    duration: float,
    n_bins: int = 201,
    n_durations: float = 6.0,
) -> VettingFeatures:
    """Hand-engineered vetting features from a folded light curve.

    depth: transit depth measured directly from the data (not the catalog
        value), from the deepest bin near phase 0.
    depth_to_scatter: depth divided by the scatter of the out-of-transit
        bins, a rough per-target signal-to-noise measure.
    odd_even_depth_diff: relative difference between the depth measured
        using only odd-numbered transit epochs vs even-numbered ones.
        A large mismatch is the classic signature of an eclipsing binary
        diluted by a third star, one of the most common Kepler false
        positive types, rather than a real planet.
    secondary_depth: depth of any dip near phase 0.5 (half an orbit away
        from the primary transit). A detected secondary eclipse also
        points to a binary star system rather than a planet.
    symmetry_diff: relative difference between the mean flux in the first
        half vs second half of the in-transit window. A real transit is
        close to symmetric; a strongly asymmetric dip suggests a blended
        or spurious signal.
    """
    view = fold_and_bin(time, flux, period, epoch, duration, n_bins=n_bins, n_durations=n_durations)

    in_transit_width = n_bins / n_durations  # bins spanning roughly one duration
    center = n_bins // 2
    # Ceiling plus a small margin, not floor: flooring systematically
    # clips a fraction of a bin off each edge of the true transit window,
    # which can cut off the deepest point when it falls near the edge
    # (seen directly on a real KOI where the true minimum sat one bin
    # outside a floor-sized window, silently reading back as zero depth).
    half_in = max(1, int(np.ceil(in_transit_width / 2)) + 2)
    in_transit = view[max(0, center - half_in): center + half_in]
    out_of_transit = np.concatenate([view[: max(0, center - 2 * half_in)], view[center + 2 * half_in:]])

    depth = 1.0 - np.min(in_transit)
    scatter = np.std(out_of_transit) if len(out_of_transit) > 1 else np.nan
    depth_to_scatter = depth / scatter if scatter and scatter > 0 else 0.0

    # Odd/even split by transit epoch number (0th, 1st, 2nd, ... transit
    # since the catalog epoch), each folded separately at the same
    # period/duration. A real planet's odd and even transits look the
    # same; an eclipsing binary's alternating primary/secondary eclipses
    # do not.
    epoch_number = np.round((time - epoch) / period)
    odd_mask = (epoch_number.astype(int) % 2) != 0
    even_mask = ~odd_mask
    odd_view = fold_and_bin(time[odd_mask], flux[odd_mask], period, epoch, duration, n_bins=n_bins, n_durations=n_durations)
    even_view = fold_and_bin(time[even_mask], flux[even_mask], period, epoch, duration, n_bins=n_bins, n_durations=n_durations)
    odd_depth = 1.0 - np.min(odd_view[max(0, center - half_in): center + half_in])
    even_depth = 1.0 - np.min(even_view[max(0, center - half_in): center + half_in])
    denom = max(odd_depth, even_depth, 1e-9)
    odd_even_depth_diff = abs(odd_depth - even_depth) / denom

    # Secondary eclipse: fold at the same period but centered half an
    # orbit away from the primary transit.
    secondary_view = fold_and_bin(time, flux, period, epoch + 0.5 * period, duration, n_bins=n_bins, n_durations=n_durations)
    secondary_window = secondary_view[max(0, center - half_in): center + half_in]
    secondary_depth = 1.0 - np.min(secondary_window)

    first_half = in_transit[: len(in_transit) // 2]
    second_half = in_transit[len(in_transit) // 2:]
    symmetry_diff = abs(np.mean(first_half) - np.mean(second_half)) / depth if depth > 0 else 0.0

    return VettingFeatures(
        depth=depth,
        depth_to_scatter=depth_to_scatter,
        odd_even_depth_diff=odd_even_depth_diff,
        secondary_depth=secondary_depth,
        symmetry_diff=symmetry_diff,
    )
