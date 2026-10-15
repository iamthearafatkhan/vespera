# analytics_app/ml.py
"""Dropout-risk model.

Predicts: P(user studies tomorrow | last 21 days of behaviour).

Design notes:
- Trained on synthetic-but-realistic data the first time it runs, then cached
  in memory. When you have 100+ real users, swap in a management command that
  retrains nightly from the DB (see train_dropout_model below).
- Logistic regression with class_weight="balanced" — the dropout class is
  usually the minority, so we weight it up.
- Standard-scaled features. Coefficients are exposed for explanation.
- The "top drivers" come from coef * scaled_value — a poor-man's SHAP that's
  honest enough for a consumer UI and 200× simpler.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ------------------------------------------------------------------
# Feature vector layout (order matters — keep consistent everywhere)
#   [0] studied_yesterday          0/1
#   [1] studies_last_3_days        0..3
#   [2] studies_last_7_days        0..7
#   [3] avg_minutes_last_7         float
#   [4] days_since_last_session    int (capped at 21)
#   [5] weekday_consistency_21     float 0..1  (fraction of weekdays studied)
#   [6] weekend_consistency_21     float 0..1
#   [7] session_count_last_21      int
# ------------------------------------------------------------------

FEATURE_NAMES = [
    "studied yesterday",
    "studied 3 of last 3 days",
    "studied 7 of last 7 days",
    "avg minutes / day (7d)",
    "days since last session",
    "weekday consistency (21d)",
    "weekend consistency (21d)",
    "sessions in last 21 days",
]


@dataclass
class RiskResult:
    probability: float          # 0..1 → higher = more likely to drop out tomorrow
    label: str                  # "on track" | "watch" | "at risk"
    top_drivers: list[tuple[str, float]]   # [(feature, contribution)] — sorted desc by |contribution|


# ---------- model singleton ----------
_MODEL = None
_SCALER = None


def _synthesize_training_data(n: int = 4000, seed: int = 42):
    """Generate a realistic-ish dataset so the model is usable on day one.

    When you have real logs, replace this with a query in train_dropout_model().
    """
    rng = np.random.default_rng(seed)
    X = np.zeros((n, 8), dtype=float)
    for i in range(n):
        # consistency drives everything
        c = rng.beta(2.5, 2.5)                        # 0..1, centered on .5
        studied_yesterday = int(rng.random() < c)
        last3 = int(rng.binomial(3, c))
        last7 = int(rng.binomial(7, c))
        avg_min = float(rng.gamma(2, 15) * c)         # minutes
        since = int(rng.geometric(max(c, 0.05)) - 1) # more consistent → fewer days off
        since = min(since, 21)
        wd = float(np.clip(c + rng.normal(0, .1), 0, 1))
        we = float(np.clip(c - .1 + rng.normal(0, .15), 0, 1))
        sessions21 = int(rng.binomial(21, c))
        X[i] = [studied_yesterday, last3, last7, avg_min, since, wd, we, sessions21]

    # label: studies tomorrow if consistency is still high AND has recent activity
    logits = (
        1.8 * X[:, 0]
        + 0.5 * X[:, 1]
        + 0.4 * X[:, 2]
        + 0.02 * X[:, 3]
        - 0.25 * X[:, 4]
        + 2.2 * X[:, 5]
        + 1.4 * X[:, 6]
        + 0.06 * X[:, 7]
        - 2.5
    )
    p = 1 / (1 + np.exp(-logits))
    y = (rng.random(n) < p).astype(int)
    return X, y


def _ensure_model():
    """Lazy-init: fit once, cache forever (until the process restarts)."""
    global _MODEL, _SCALER
    if _MODEL is not None:
        return
    X, y = _synthesize_training_data()
    _SCALER = StandardScaler().fit(X)
    _MODEL = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
    ).fit(_SCALER.transform(X), y)


def train_dropout_model():
    """Public entry point — call from a cron job once you have real data.

    For now it just refits on the synthetic data. Later, replace
    _synthesize_training_data() with a query over StudySession.
    """
    global _MODEL
    _MODEL = None
    _ensure_model()
    return _MODEL


def _label(prob: float) -> str:
    if prob >= 0.65:
        return "at risk"
    if prob >= 0.40:
        return "watch"
    return "on track"


def predict_dropout_risk(features: list[float]) -> RiskResult:
    """Public prediction API. `features` must have 8 floats in the fixed order."""
    _ensure_model()
    x = np.asarray(features, dtype=float).reshape(1, -1)
    xs = _SCALER.transform(x)[0]
    prob = float(_MODEL.predict_proba(xs.reshape(1, -1))[0, 1])

    # contributions = coefficient * scaled value; positive → pushes toward studying
    contributions = _MODEL.coef_[0] * xs
    # we want "risk drivers", so negative contributions are the concerning ones
    drivers = sorted(
        zip(FEATURE_NAMES, contributions),
        key=lambda t: t[1],      # most negative first
    )[:3]

    return RiskResult(
        probability=prob,
        label=_label(prob),
        top_drivers=[(name, round(float(c), 3)) for name, c in drivers],
    )