# exoplanet-transit-detection (ExoDetect)

Finding real planets in raw NASA light curves, not the pre-cleaned Kaggle set.

Pulls raw light curves directly from the MAST archive via [`lightkurve`](https://docs.lightkurve.org/), detrends them,
runs a classical Box Least Squares (BLS) transit search, validates recovered orbital periods against published values
for known systems (TRAPPIST-1, Kepler-90, Kepler-186f), then applies the same pipeline to real unconfirmed TESS
Objects of Interest (TOI) candidates from the NASA Exoplanet Archive.

**This pipeline flags transit-like signals. It does not confirm planets.** Confirmation requires follow-up
spectroscopy or radial-velocity data outside the scope of this project. This caveat is stated explicitly wherever
a TOI result appears.

## Status

Work in progress. See `docs/plan.md` for the full project plan and build order.

## Structure

- `src/exodetect/`: pipeline package (data retrieval, detrending, BLS, classifier, physical characterization)
- `notebooks/`: exploratory and validation notebooks
- `docs/`: plan and write-up
- `tests/`: unit tests

## Citations

- NASA Exoplanet Archive
- Kepler and TESS missions (NASA)
- Lightkurve Collaboration, *Lightkurve: Kepler and TESS time series analysis in Python*, JOSS, 2018.
