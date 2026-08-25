"""Phase 4 (1/3): build the labeled transit-classifier training set.

Real Kepler KOI dispositions, not the pre-cleaned Kaggle set: each
target's light curve is downloaded fresh (up to 4 quarters) and folded
ourselves, using the archive's CONFIRMED / FALSE POSITIVE labels.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd

from exodetect.catalog import fetch_koi_sample
from exodetect.training_data import build_dataset

N_PER_CLASS = 30

print(f"Fetching {N_PER_CLASS} CONFIRMED and {N_PER_CLASS} FALSE POSITIVE KOIs from the archive...")
confirmed = fetch_koi_sample("CONFIRMED", limit=N_PER_CLASS)
false_pos = fetch_koi_sample("FALSE POSITIVE", limit=N_PER_CLASS)

print("\n--- Collecting CONFIRMED targets ---")
views_pos, feats_pos, labels_pos, fail_pos = build_dataset(confirmed, label=1, log_prefix="[CONFIRMED] ")

print("\n--- Collecting FALSE POSITIVE targets ---")
views_neg, feats_neg, labels_neg, fail_neg = build_dataset(false_pos, label=0, log_prefix="[FALSE POS] ")

views = np.array(views_pos + views_neg)
labels = np.array(labels_pos + labels_neg)
feature_rows = feats_pos + feats_neg
features_df = pd.DataFrame([vars(f) for f in feature_rows])
features_df["label"] = labels

out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(out_dir, exist_ok=True)
np.savez(os.path.join(out_dir, "local_views.npz"), views=views, labels=labels)
features_df.to_csv(os.path.join(out_dir, "features.csv"), index=False)

print(f"\nCollected {len(views_pos)}/{len(confirmed)} confirmed, {len(views_neg)}/{len(false_pos)} false positive")
print(f"Failures: {len(fail_pos)} confirmed, {len(fail_neg)} false positive")
if fail_pos:
    print("Confirmed failures:", fail_pos)
if fail_neg:
    print("False positive failures:", fail_neg)
print(f"\nSaved {len(views)} labeled examples to {out_dir}")
print(features_df.groupby("label").mean(numeric_only=True).to_string())
