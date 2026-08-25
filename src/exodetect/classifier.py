"""Two transit classifiers trained on the same labeled dataset:
a small 1D CNN on the folded local view, and a gradient-boosted model
on hand-engineered features, as an honest second baseline per the
project plan (not just one model presented as the only answer).
"""

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix

import torch
import torch.nn as nn


FEATURE_COLUMNS = ["depth", "depth_to_scatter", "odd_even_depth_diff", "secondary_depth", "symmetry_diff"]
VIEW_SCALE = 1000.0


class TransitCNN(nn.Module):
    """Small 1D CNN over the fixed-length folded local view."""

    def __init__(self, input_length: int):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(16, 32, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        pooled_length = input_length // 4
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * pooled_length, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.classifier(self.conv(x)).squeeze(-1)


def train_cnn(views: np.ndarray, labels: np.ndarray, epochs: int = 200, seed: int = 0):
    """Train the CNN on a train/test split of (views, labels). Returns (model, test_metrics, test_indices)."""
    torch.manual_seed(seed)
    n = len(views)
    idx = np.arange(n)
    train_idx, test_idx = train_test_split(idx, test_size=0.25, random_state=seed, stratify=labels)

    # Center at 0 and scale to O(1) magnitude: raw transit depths are
    # fractions of order 1e-3 to 1e-4, too small relative to default
    # weight initialization for the network to learn from in a handful
    # of epochs on this few examples (seen directly: without scaling,
    # training collapsed to predicting the majority class regardless of
    # input). VIEW_SCALE turns fractional depth into roughly parts-per-
    # thousand, an O(0.1-100) range standard init handles well.
    x = torch.tensor((views - 1.0) * VIEW_SCALE, dtype=torch.float32).unsqueeze(1)  # (N, 1, L)
    y = torch.tensor(labels, dtype=torch.float32)

    model = TransitCNN(input_length=views.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss()

    x_train, y_train = x[train_idx], y[train_idx]
    x_test, y_test = x[test_idx], y[test_idx]

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        logits = model(x_train)
        loss = loss_fn(logits, y_train)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        test_probs = torch.sigmoid(model(x_test)).numpy()
    test_preds = (test_probs >= 0.5).astype(int)

    metrics = _classification_metrics(y_test.numpy(), test_preds)
    return model, metrics, test_idx


def train_gbm(features_df, labels: np.ndarray, seed: int = 0):
    """Train the gradient-boosted baseline on hand-engineered features."""
    x = features_df[FEATURE_COLUMNS].values
    idx = np.arange(len(x))
    train_idx, test_idx = train_test_split(idx, test_size=0.25, random_state=seed, stratify=labels)

    # Tried regularizing this down for a small dataset (fewer/shallower
    # trees, larger min_samples_leaf), reasoning that sklearn's defaults
    # are overparameterized for a few dozen examples. Checked directly:
    # on this data, every regularized variant tried did worse on the held-
    # out set than sklearn's plain defaults, which land exactly on the
    # trivial majority-class baseline. Keeping the defaults rather than a
    # change that measurably made things worse.
    model = GradientBoostingClassifier(random_state=seed)
    model.fit(x[train_idx], labels[train_idx])

    test_preds = model.predict(x[test_idx])
    metrics = _classification_metrics(labels[test_idx], test_preds)
    return model, metrics, test_idx


def _classification_metrics(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
        "n_test": len(y_true),
    }


def predict_cnn(model: TransitCNN, view: np.ndarray) -> float:
    """Probability a single folded local view is a real transit."""
    model.eval()
    with torch.no_grad():
        x = torch.tensor((view - 1.0) * VIEW_SCALE, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        return torch.sigmoid(model(x)).item()


def predict_gbm(model: GradientBoostingClassifier, features) -> float:
    """Probability a single feature vector is a real transit."""
    x = np.array([[getattr(features, col) for col in FEATURE_COLUMNS]])
    return model.predict_proba(x)[0, 1]
