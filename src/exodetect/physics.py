"""Turning a transit detection into a physical planet: radius, orbital
distance, equilibrium temperature, and a habitable-zone verdict.

Stellar radius, mass, and temperature all carry their own measurement
uncertainty. Rather than propagate that analytically, this samples the
stellar parameters within their reported Gaussian uncertainty many times
and recomputes the planet's physical parameters for each draw, reporting
a median and a 16th-84th percentile range. A single precise-looking
number would misrepresent how well any of this is actually known.

Physical relations used, all standard:
- Transit depth ~ (Rp/Rstar)^2, so Rp = Rstar * sqrt(depth)
- Stellar mass from surface gravity and radius: M = g R^2 / G
- Semi-major axis from Kepler's third law: a^3 = G M P^2 / (4 pi^2)
- Zero-albedo equilibrium temperature: Teq = Tstar * sqrt(Rstar / (2a))
- Habitable zone boundaries, conservative estimate (Kasting et al. 1993
  style): d_inner = sqrt(L / 1.1) AU, d_outer = sqrt(L / 0.53) AU
"""

from dataclasses import dataclass

import numpy as np

G = 6.674e-11  # m^3 kg^-1 s^-2
R_SUN = 6.957e8  # m
M_SUN = 1.989e30  # kg
T_SUN = 5772.0  # K
AU = 1.496e11  # m
DAY = 86400.0  # s
SIGMA_SB = 5.670374e-8  # W m^-2 K^-4
L_SUN = 3.828e26  # W


@dataclass
class Characterization:
    planet_radius_re: tuple  # (median, lo, hi) in Earth radii
    semi_major_axis_au: tuple
    eq_temp_k: tuple
    hz_inner_au: float
    hz_outer_au: float
    hz_verdict: str  # "in habitable zone", "too hot", "too cold", "marginal"


def _percentiles(samples: np.ndarray) -> tuple:
    lo, med, hi = np.percentile(samples, [16, 50, 84])
    return float(med), float(lo), float(hi)


def characterize(
    depth: float,
    period_days: float,
    star_radius_rsun: float, star_radius_err_rsun: float,
    star_teff_k: float, star_teff_err_k: float,
    star_logg: float, star_logg_err: float,
    n_samples: int = 5000,
    seed: int = 0,
) -> Characterization:
    """Monte Carlo physical characterization of a transit detection.

    depth is a fractional flux drop (e.g. 0.01 for 1 percent), not ppm.
    star_logg is log10(g) in cgs (cm/s^2), the catalog convention.
    """
    rng = np.random.default_rng(seed)
    depth = max(depth, 0.0)

    r_star = rng.normal(star_radius_rsun, max(star_radius_err_rsun, 1e-6), n_samples)
    r_star = np.clip(r_star, 1e-3, None) * R_SUN

    teff = rng.normal(star_teff_k, max(star_teff_err_k, 1.0), n_samples)
    teff = np.clip(teff, 100.0, None)

    logg = rng.normal(star_logg, max(star_logg_err, 1e-3), n_samples)
    g_cgs = 10 ** logg
    g_si = g_cgs * 1e-2  # cm/s^2 -> m/s^2
    m_star = g_si * r_star ** 2 / G  # kg

    planet_radius_m = r_star * np.sqrt(depth)
    planet_radius_re = planet_radius_m / (R_SUN / 109.2)  # Earth radii (Rsun/Rearth ~ 109.2)

    period_s = period_days * DAY
    a_m = (G * m_star * period_s ** 2 / (4 * np.pi ** 2)) ** (1 / 3)
    a_au = a_m / AU

    eq_temp = teff * np.sqrt(r_star / (2 * a_m))

    luminosity = 4 * np.pi * r_star ** 2 * SIGMA_SB * teff ** 4 / L_SUN  # in L_sun
    hz_inner = np.sqrt(np.median(luminosity) / 1.1)
    hz_outer = np.sqrt(np.median(luminosity) / 0.53)

    a_med = float(np.median(a_au))
    a_spread = float(np.std(a_au))
    if a_med < hz_inner - a_spread:
        verdict = "too hot"
    elif a_med > hz_outer + a_spread:
        verdict = "too cold"
    elif hz_inner <= a_med <= hz_outer:
        verdict = "in habitable zone"
    else:
        verdict = "marginal"

    return Characterization(
        planet_radius_re=_percentiles(planet_radius_re),
        semi_major_axis_au=_percentiles(a_au),
        eq_temp_k=_percentiles(eq_temp),
        hz_inner_au=float(hz_inner),
        hz_outer_au=float(hz_outer),
        hz_verdict=verdict,
    )
