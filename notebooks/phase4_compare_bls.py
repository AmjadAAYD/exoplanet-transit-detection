"""Phase 4 (3/3): compare BLS alone vs BLS-plus-classifier vetting.

Reuses the actual BLS detections from Phase 3 for TRAPPIST-1, Kepler-90,
and Kepler-186, where the catalog match already tells us which
detections were real planets and which were not. For each detection,
folds it (independently of the Phase 3 period search) and asks both
trained classifiers whether it looks like a real transit, then checks
whether that vetting call agrees with the known ground truth.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib.pyplot as plt
import torch
import joblib

from exodetect.pipeline import run_target_validation
from exodetect.fold import fold_and_bin, extract_features
from exodetect.classifier import TransitCNN, predict_cnn, predict_gbm

data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
npz = np.load(os.path.join(data_dir, "local_views.npz"))
view_length = npz["views"].shape[1]

cnn_model = TransitCNN(input_length=view_length)
cnn_model.load_state_dict(torch.load(os.path.join(data_dir, "cnn_model.pt")))
gbm_model = joblib.load(os.path.join(data_dir, "gbm_model.joblib"))

TARGETS = [
    dict(target_name="TRAPPIST-1", cache_key="trappist1_k2c12_60s", catalog_hostname="TRAPPIST-1",
         mission="K2", author="K2", exptime=60, stitch=False, window_length=401,
         duration_grid=None, min_period=1.0, max_period=20.0, n_iterations=8),
    dict(target_name="Kepler-90", cache_key="kepler90_kepler_lc", catalog_hostname="KOI-351",
         mission="Kepler", author="Kepler", exptime=1800, stitch=True, window_length=73,
         duration_grid=np.array([0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5]),
         min_period=3.0, max_period=350.0, n_iterations=9),
    dict(target_name="Kepler-186", cache_key="kepler186_kepler_lc", catalog_hostname="Kepler-186",
         mission="Kepler", author="Kepler", exptime=1800, stitch=True, window_length=49,
         duration_grid=np.array([0.02, 0.05, 0.08, 0.12, 0.18, 0.25]),
         min_period=2.0, max_period=145.0, n_iterations=6),
]

rows = []
disagreements = []

for cfg in TARGETS:
    print(f"\n=== {cfg['target_name']} ===", flush=True)
    print("  fetching catalog + running BLS...", flush=True)
    run = run_target_validation(**cfg)
    print(f"  got {len(run.detections)} detections, now folding + classifying each...", flush=True)
    matched_periods = {r.recovered_period for r in run.results if r.matched}
    t = run.light_curve.time.value
    f = run.light_curve.flux.value

    for d in run.detections:
        ground_truth = d.period in matched_periods
        view = fold_and_bin(t, f, d.period, d.t0, d.duration, n_bins=view_length)
        feats = extract_features(t, f, d.period, d.t0, d.duration, n_bins=view_length)
        cnn_prob = predict_cnn(cnn_model, view)
        gbm_prob = predict_gbm(gbm_model, feats)
        cnn_verdict = cnn_prob >= 0.5
        gbm_verdict = gbm_prob >= 0.5

        row = dict(
            target=cfg["target_name"], period=d.period, ground_truth=ground_truth,
            cnn_prob=cnn_prob, gbm_prob=gbm_prob,
            cnn_agrees=cnn_verdict == ground_truth, gbm_agrees=gbm_verdict == ground_truth,
        )
        rows.append(row)
        print(f"  period={d.period:.4f}d matched={ground_truth} cnn_prob={cnn_prob:.3f} gbm_prob={gbm_prob:.3f}", flush=True)

        if not row["cnn_agrees"] or not row["gbm_agrees"]:
            disagreements.append((cfg["target_name"], d, view, ground_truth, cnn_prob, gbm_prob))

cnn_agreement = np.mean([r["cnn_agrees"] for r in rows])
gbm_agreement = np.mean([r["gbm_agrees"] for r in rows])

print(f"\n=== Summary across {len(rows)} BLS detections (3 validation targets) ===")
print(f"CNN vetting agrees with ground truth: {cnn_agreement:.1%}")
print(f"GBM vetting agrees with ground truth: {gbm_agreement:.1%}")
print(f"Disagreement cases: {len(disagreements)}")

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "figures")
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(data_dir, "bls_vs_classifier_comparison.json"), "w") as fh:
    json.dump(rows, fh, indent=2, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))

n_show = min(3, len(disagreements))
if n_show > 0:
    fig, axes = plt.subplots(n_show, 1, figsize=(8, 3 * n_show))
    if n_show == 1:
        axes = [axes]
    for ax, (target, d, view, gt, cnn_p, gbm_p) in zip(axes, disagreements[:n_show]):
        ax.plot(view, color="tab:blue")
        ax.set_title(
            f"{target}: period={d.period:.3f}d, ground truth matched={gt}, "
            f"CNN prob={cnn_p:.2f}, GBM prob={gbm_p:.2f}"
        )
        ax.set_xlabel("Phase bin")
        ax.set_ylabel("Normalized flux")
    fig.tight_layout()
    out_path = os.path.join(out_dir, "bls_vs_classifier_disagreements.png")
    fig.savefig(out_path, dpi=150)
    print(f"\nSaved {n_show} disagreement case plots to {out_path}")
else:
    print("\nNo disagreement cases to plot.")
