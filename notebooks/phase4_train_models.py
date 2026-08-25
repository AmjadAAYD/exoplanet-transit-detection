"""Phase 4 (2/3): train the CNN and gradient-boosted classifiers, report held-out metrics."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd
import torch

from exodetect.classifier import train_cnn, train_gbm

data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
npz = np.load(os.path.join(data_dir, "local_views.npz"))
views, labels = npz["views"], npz["labels"]
features_df = pd.read_csv(os.path.join(data_dir, "features.csv"))

print(f"Dataset: {len(views)} examples, {labels.sum()} confirmed, {len(labels) - labels.sum()} false positive")

print("\nTraining CNN on folded local views...")
cnn_model, cnn_metrics, cnn_test_idx = train_cnn(views, labels)
print(json.dumps(cnn_metrics, indent=2))

print("\nTraining gradient-boosted classifier on hand-engineered features...")
gbm_model, gbm_metrics, gbm_test_idx = train_gbm(features_df, labels)
print(json.dumps(gbm_metrics, indent=2))

torch.save(cnn_model.state_dict(), os.path.join(data_dir, "cnn_model.pt"))
import joblib
joblib.dump(gbm_model, os.path.join(data_dir, "gbm_model.joblib"))

with open(os.path.join(data_dir, "held_out_metrics.json"), "w") as fh:
    json.dump({"cnn": cnn_metrics, "gbm": gbm_metrics}, fh, indent=2)

print(f"\nSaved trained models and metrics to {data_dir}")
