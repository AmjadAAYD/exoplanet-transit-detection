"""Builds a labeled transit-classifier training set from real Kepler KOI dispositions.

Not the pre-cleaned Kaggle set: each target's light curve is downloaded
fresh from MAST and folded ourselves, using the Kepler cumulative table's
CONFIRMED / FALSE POSITIVE dispositions as labels.
"""

from .data import get_multi_quarter_light_curve
from .detrend import detrend_light_curve, choose_flatten_window
from .fold import fold_and_bin, extract_features

KEPLER_LONG_CADENCE_DAYS = 1765.5 / 86400


def collect_one(kepid: int, period: float, epoch: float, duration_hours: float, max_quarters: int = 4):
    """Download (up to max_quarters), detrend, and fold a single KOI.

    Returns (local_view, features) or raises. max_quarters caps download
    cost per target while still giving several quarters of baseline, a
    single quarter was too unreliable, several targets showed zero
    measured depth because no transit landed inside that one quarter's
    window.
    """
    duration_days = duration_hours / 24.0
    cache_key = f"koi_kic{kepid}_mq{max_quarters}"
    lc = get_multi_quarter_light_curve(
        cache_key,
        f"KIC {kepid}",
        max_quarters=max_quarters,
        mission="Kepler",
        author="Kepler",
        exptime=1800,
    )
    window = choose_flatten_window(period, duration_days, KEPLER_LONG_CADENCE_DAYS)
    flat = detrend_light_curve(lc, window_length=window)

    t = flat.time.value
    f = flat.flux.value
    view = fold_and_bin(t, f, period, epoch, duration_days)
    feats = extract_features(t, f, period, epoch, duration_days)
    return view, feats


def build_dataset(koi_df, label: int, log_prefix: str = ""):
    """Run collect_one over every row of a KOI dataframe, skipping failures.

    Returns (views, feature_rows, labels, failures). Failures are (kepid,
    error message) pairs, reported rather than silently swallowed, since a
    training set built from whatever happens not to error out is a
    different, unstated sampling bias.
    """
    views, feature_rows, labels, failures = [], [], [], []

    for i, row in enumerate(koi_df.itertuples()):
        try:
            view, feats = collect_one(row.kepid, row.koi_period, row.koi_time0bk, row.koi_duration)
            views.append(view)
            feature_rows.append(feats)
            labels.append(label)
            print(f"{log_prefix}[{i+1}/{len(koi_df)}] KIC {row.kepid} ({row.kepoi_name}): ok", flush=True)
        except Exception as e:
            failures.append((row.kepid, str(e)))
            print(f"{log_prefix}[{i+1}/{len(koi_df)}] KIC {row.kepid} ({row.kepoi_name}): FAILED - {e}", flush=True)

    return views, feature_rows, labels, failures
