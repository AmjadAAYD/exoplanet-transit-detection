# Project 1: finding real planets in raw NASA light curves

Planning only. Built to specifically avoid the failure mode of the ISS tracker idea: this is not a chart of a benchmark score, it's a reproducible discovery pipeline run on real, unconfirmed data, with one visual nobody else in this space is posting.

---

## 1. Why the standard version of this project is boring, and what fixes it

The default version everyone builds: download Kaggle's "Kepler Labelled Time Series Data" (already cleaned, already labelled), train a classifier, report ~97% accuracy. It is the exoplanet equivalent of MNIST digit recognition. Technically fine, visually a confusion matrix, forgettable.

Three changes make this a different project entirely:

1. **Raw data, not the pre-cleaned Kaggle set.** Pull actual light curves from NASA's archive via `lightkurve`, for real stars. This alone changes every downstream step, the noise, the gaps, the systematics are all real, not sanitised.
2. **A physical payoff, not a score.** Convert a detection into an actual planet radius, orbital distance, and temperature, then ask "could this have liquid water." A person with zero ML background understands that sentence. Nobody understands or cares about 97.3% accuracy.
3. **One visual nobody else has**, a synthetic transit animation running in sync with a real light curve dip. That is the "oh damn."

---

## 2. The narrative arc of the whole project

This is the structure to build toward, because it is also the structure of the eventual post:

1. **Reproduce a famous, confirmed discovery from scratch**, TRAPPIST-1, using only public data and your own code, as proof the method works.
2. **Point the same method at real unconfirmed candidates**, TESS Objects of Interest that nobody has fully resolved yet, and report what you find.
3. **Characterise, don't just classify**, for anything your pipeline flags, compute what kind of planet it would actually be.

Detection to validation to discovery to meaning, in that order.

---

## 3. Data

### Primary source: `lightkurve` (STScI's official Python package)

- `pip install lightkurve`
- Talks directly to the MAST archive (Mikulski Archive for Space Telescopes), which hosts all Kepler and TESS data, free, no auth required for public data
- One call retrieves the full observed light curve for any target by name or catalog ID:
  ```python
  import lightkurve as lk
  search = lk.search_lightcurve("TRAPPIST-1", mission="Spitzer")  # or Kepler/TESS depending on target
  lc = search.download()
  ```
- For TRAPPIST-1 specifically, the original discovery used Spitzer and ground-based data, but TESS has also observed it, use whichever mission has usable public light curves for your chosen targets, check what's actually available before committing to one

### Confirmed-planet validation targets (pick two or three, not just TRAPPIST-1)

| Target | Why | Mission with good public data |
|---|---|---|
| TRAPPIST-1 | Seven Earth-sized planets, the most famous system of its kind, huge public recognition | TESS / Spitzer |
| Kepler-90 | Eight confirmed planets, a full "mini solar system" | Kepler |
| Kepler-186f | First Earth-size planet found in a habitable zone, historically significant | Kepler |

Reproducing detection on two or three well-known systems, not just one, is what makes the validation step credible rather than a single lucky result.

### Discovery targets: real unconfirmed candidates

- NASA Exoplanet Archive publishes the **TESS Objects of Interest (TOI) table**, candidates flagged by the pipeline but not yet confirmed as planets, freely downloadable as CSV: `https://exoplanetarchive.ipac.caltech.edu/`
- Filter to TOIs that are still listed as "candidate" (not yet "confirmed" or "false positive"), pick a manageable batch, 20 to 50, and run your pipeline on their raw light curves
- Be precise in the writeup: your pipeline can **flag a transit-like signal**, it cannot itself confirm a planet, real confirmation needs follow-up spectroscopy or radial velocity data you don't have. State this limitation explicitly, it is what separates honest work from an overclaim, and it reads as more credible, not less impressive.

---

## 4. Method

### Step 1: Detrend the raw light curve

Real light curves have instrumental drift, momentum-dump artifacts (TESS), and stellar variability, none of which exist in the pre-cleaned Kaggle set, and all of which you now have to actually handle:

- Remove NaNs and clear quality-flagged bad cadences (`lc.remove_nans()`, quality bitmask)
- Flatten long-term trends with a Savitzky-Golay filter (`lc.flatten()`, built into `lightkurve`)
- Sigma-clip remaining outliers

This step alone is worth documenting well, it's the difference between a real pipeline and a notebook that only works on one clean example.

### Step 2: Search for periodic transits, classically first

- **Box Least Squares (BLS)**, the standard classical method, built into `lightkurve` and `astropy.timeseries`
- BLS searches over a grid of periods and transit durations for the period that best matches a box-shaped dip
- Output: a periodogram, and the best-fit period, duration, and depth
- For your confirmed validation targets, check the recovered period against the known, published orbital period, this is your "did it actually work" number, and it's a strong one to state plainly in the post: "recovered orbital period, X days, published period, Y days."

### Step 3: A learned detector, and an honest comparison

- Fold the light curve at candidate periods, generate a normalised, fixed-length input, train a small 1D CNN (or even a simple gradient-boosted model on hand-engineered features, depth, duration, shape, as a second honest baseline) to classify plausible-transit vs not
- Train on the confirmed catalog entries (Kepler/TESS confirmed planets have public labels), not the Kaggle set
- Compare BLS alone vs BLS-plus-CNN vetting on your held-out confirmed targets and on the TOI batch. Report where they agree and where they disagree, disagreement cases are your most interesting content, not a weakness to hide.

### Step 4: From detection to a planet

For anything with a credible period and depth:

- Transit depth approximates (planet radius / star radius)², so with the star's known radius (from the archive, alongside every target) you get an estimated planet radius
- Orbital period plus the star's mass (Kepler's third law) gives the orbital distance
- Star's luminosity and orbital distance give an estimated equilibrium temperature
- Compare that distance against the star's habitable zone boundaries (a standard, well-documented calculation from stellar luminosity and temperature) and report yes/no/marginal

This step is what turns a detection into a sentence a non-technical reader understands.

### Step 5: The signature visual

An animated, synchronised pair:
- **Left panel**: a simple 2D animation, a dark circle (planet) crossing in front of a bright circle (star), sized and timed to match the actual recovered transit depth and duration
- **Right panel**: the real light curve, playing in sync, with the brightness dipping exactly as the simulated planet crosses

Built with `matplotlib.animation` or `manim`, nothing exotic technically, the novelty is that essentially nobody doing a student exoplanet project makes this pairing. It is the single visual that explains the entire concept to someone with zero background, in five seconds, and it is what should open the post.

---

## 5. Deliverables

1. **The sync animation** (Section 4, Step 5), the post's opening visual
2. **A validation table**, target, published period, your recovered period, error, for TRAPPIST-1, Kepler-90, Kepler-186f
3. **A discovery table**, the TOI batch, what your pipeline flagged, estimated radius, estimated temperature, habitable-zone verdict, with the honest caveat that this is candidate-flagging, not confirmation
4. **The BLS-vs-CNN comparison**, agreement rate, and two or three concrete disagreement cases shown as light curves
5. **Repo**: `github.com/AmjadAAYD/exoplanet-transit-detection`, notebook, method write-up, the honest limitations section
6. Optional: a small Hugging Face Space, paste a TIC or KIC catalog ID, get back the light curve, the BLS periodogram, and a verdict

---

## 6. Build order

| Phase | Work |
|---|---|
| 1 | `lightkurve` installed, TRAPPIST-1 light curve pulled and plotted raw, confirm data actually arrives before building anything else |
| 2 | Detrending pipeline working cleanly on TRAPPIST-1 |
| 3 | BLS period search recovers TRAPPIST-1's known planets, cross-check against published periods, repeat for Kepler-90 and Kepler-186f |
| 4 | CNN or feature-based classifier trained on confirmed-planet catalog entries, compared against BLS on the three validation targets |
| 5 | Pipeline run on the TOI batch, results tabulated, physical characterisation computed for anything flagged |
| 6 | The sync animation built and polished, this is worth real time, it is the post |
| 7 | Repo, README, writeup, post |

Phase 3 alone is already postable: "I recovered the periods of TRAPPIST-1's seven planets from raw NASA data using the same classical method astronomers use." Do not wait for phase 7 if time runs short.

---

## 7. Known pitfalls

- **Do not confuse detection with confirmation.** State this limitation explicitly wherever a TOI result is shown. It is the single most important honesty line in the whole project, and it costs you nothing technically.
- **Check mission and cadence availability before committing to a target.** Not every star has clean public light curves in every mission, verify data actually exists and is usable before building the rest of the pipeline around it.
- **BLS is period-grid-dependent.** A grid that's too coarse will miss the true period, or alias to a harmonic of it. Validate against known periods first precisely so you catch this before it silently corrupts the TOI results.
- **Stellar parameters (radius, mass, luminosity) come with their own uncertainty.** Carry that uncertainty into the physical estimates, at minimum as an error bar, rather than presenting a single precise-looking number.
- **Cite sources properly**: NASA Exoplanet Archive, the Kepler and TESS missions, and `lightkurve` itself (it has a citable JOSS paper). This is standard practice and it signals real scientific literacy, not just API usage.

---

## 8. The post

```
Somewhere in NASA's public archive is the raw data that first revealed seven
Earth-sized planets around TRAPPIST-1.

I pulled it myself and re-found them, using the same method astronomers use.

[sync animation: simulated transit next to the real light curve dip]

Recovered orbital periods matched the published ones to within [X]%.

Then I pointed the same pipeline at real unconfirmed TESS candidates,
signals nobody has fully verified yet, and for the strongest ones, worked
out what kind of planet they'd actually be: size, distance from their star,
whether they could have liquid water.

This doesn't confirm new planets, that needs follow-up observations I don't
have access to. But it's the same first step real discovery pipelines take.

Method, data, and the full notebook in the comments.
```

Repo link in the first comment, not the post body.
