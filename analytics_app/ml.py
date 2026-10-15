# analytics_app/ml.py
"""Study-momentum model.

Predicts: P(user studies tomorrow | last 21 days of behaviour).

Why gradient boosting + calibration?
  - A linear model can't capture interactions (e.g. "consistent on weekdays
    but not weekends" vs "consistent everywhere") — GBMs can.
  - Raw tree probabilities are over-confident. We wrap the model in
    CalibratedClassifierCV with Platt scaling (sigmoid) trained on a
    held-out fold, so 0.70 actually means ~70%.
  - Explanation comes from permutation importance times the deviation of
    each feature from its training mean — model-agnostic and more honest
    than logistic coef * x.

Training data:
  On first call, we synthesize a realistic population by simulating a
  latent "motivation" random walk per user. The model never sees the
  motivation — it only sees the observable features. When real logs
  exist, swap `_synthesize_population()` for a query over StudySession.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = [
    "studied yesterday",
    "study days in last 3",
    "study days in last 7",
    "avg minutes / day (7d)",
    "days since last session",
    "weekday consistency (21d)",
    "weekend consistency (21d)",
    "sessions in last 21 days",
]


@dataclass
class RiskResult:
    probability: float
    label: str
    top_drivers: list[tuple[str, float]]
    model_auc: float | None = None       # ROC AUC on holdout — for the README
    calibrated: bool = True


# ------------------------------------------------------------------
# Training-data synthesis — a proper generative process
# ------------------------------------------------------------------

def _simulate_one_user(rng) -> tuple[list[float], int]:
    """Simulate 21 days for one user and return (features, label).

    The hidden state is `motivation` — an OU-ish random walk in [-3, 3].
    Study on day t is drawn from sigmoid(motivation_t + weekday_bias).
    The model has to recover the same signal from observable features only.
    """
    # latent motivation trajectory
    m = np.zeros(22)
    m[0] = rng.normal(0, 1)
    for t in range(1, 22):
        m[t] = 0.85 * m[t - 1] + rng.normal(0, 0.6)

    studied = np.zeros(22, dtype=int)
    minutes = np.zeros(22)
    for t in range(22):
        dow = t % 7                              # 0..6, purely synthetic
        weekday_bias = 0.4 if dow < 5 else -0.6  # weekdays slightly more likely
        p = 1 / (1 + np.exp(-(m[t] + weekday_bias)))
        studied[t] = int(rng.random() < p)
        if studied[t]:
            # minutes scale with motivation too
            minutes[t] = max(0, rng.gamma(2.0, 15.0) + m[t] * 5)

    # we predict day 22 (tomorrow)
    label = studied[-1]

    # features from days 0..20 (what the user "did yesterday and before")
    past = slice(0, 21)
    studied_yesterday = studied[19]
    last3  = int(studied[17:20].sum())
    last7  = int(studied[14:21].sum())
    avg_min_7 = float(minutes[14:21].mean())
    since = 21
    for i, v in enumerate(reversed(studied[past])):
        if v:
            since = i
            break
    wd_mask = np.array([(i % 7) < 5 for i in range(21)])
    we_mask = ~wd_mask
    wd_consistency = float(studied[past][wd_mask].mean()) if wd_mask.any() else 0.0
    we_consistency = float(studied[past][we_mask].mean()) if we_mask.any() else 0.0
    sessions_21 = int(studied[past].sum())

    feats = [
        float(studied_yesterday),
        float(last3),
        float(last7),
        avg_min_7,
        float(since),
        wd_consistency,
        we_consistency,
        float(sessions_21),
    ]
    return feats, int(label)


def _synthesize_population(n_users: int = 6000, seed: int = 42):
    rng = np.random.default_rng(seed)
    X = np.zeros((n_users, len(FEATURE_NAMES)))
    y = np.zeros(n_users, dtype=int)
    for i in range(n_users):
        feats, label = _simulate_one_user(rng)
        X[i] = feats
        y[i] = label
    return X, y


# ------------------------------------------------------------------
# Singleton training — done once per process
# ------------------------------------------------------------------

_MODEL = None
_SCALER = None
_FEATURE_MEANS = None
_IMPORTANCE = None
_AUC = None


def _ensure_model():
    global _MODEL, _SCALER, _FEATURE_MEANS, _IMPORTANCE, _AUC
    if _MODEL is not None:
        return

    X, y = _synthesize_population()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    _SCALER = StandardScaler().fit(X_train)
    Xtr = _SCALER.transform(X_train)
    Xte = _SCALER.transform(X_test)
    _FEATURE_MEANS = X_train.mean(axis=0)

    base = GradientBoostingClassifier(
        n_estimators=220,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.9,
        random_state=42,
    )

    # 5-fold Platt calibration gives us honest probabilities
    calibrated = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    calibrated.fit(Xtr, y_train)

    from sklearn.metrics import roc_auc_score
    try:
        _AUC = float(roc_auc_score(y_test, calibrated.predict_proba(Xte)[:, 1]))
    except Exception:
        _AUC = None

    # permutation importance on the holdout — model-agnostic
    try:
        perm = permutation_importance(
            calibrated, Xte, y_test,
            n_repeats=6, random_state=42, scoring="roc_auc",
        )
        _IMPORTANCE = perm.importances_mean
    except Exception:
        _IMPORTANCE = np.ones(len(FEATURE_NAMES)) / len(FEATURE_NAMES)

    _MODEL = calibrated


def train_dropout_model():
    """Force a refit. Call from cron once you have real data."""
    global _MODEL
    _MODEL = None
    _ensure_model()
    return _MODEL


# ------------------------------------------------------------------
# Public prediction API
# ------------------------------------------------------------------

def _label(prob: float) -> str:
    if prob < 0.35:
        return "at risk"
    if prob < 0.60:
        return "watch"
    return "on track"


def predict_dropout_risk(features: list[float]) -> RiskResult:
    _ensure_model()
    x = np.asarray(features, dtype=float).reshape(1, -1)
    xs = _SCALER.transform(x)[0]

    prob = float(_MODEL.predict_proba(xs.reshape(1, -1))[0, 1])

    # driver score = (feature deviation from mean) * model-importance
    # positive → this feature is helping; negative → this feature is hurting
    deviation = (x[0] - _FEATURE_MEANS)
    # normalize deviations so magnitudes are comparable across features
    std = np.where(_FEATURE_MEANS != 0, np.abs(_FEATURE_MEANS), 1.0)
    norm_dev = deviation / std
    driver_scores = norm_dev * _IMPORTANCE

    # when probability is low, we want to explain *why* — show the features
    # pushing away from studying (most negative scores).
    # when probability is high, show what's helping (most positive).
    if prob < 0.60:
        order = np.argsort(driver_scores)[:3]      # ascending
    else:
        order = np.argsort(-driver_scores)[:3]     # descending

    drivers = [(FEATURE_NAMES[i], float(round(driver_scores[i], 3))) for i in order]

    return RiskResult(
        probability=prob,
        label=_label(prob),
        top_drivers=drivers,
        model_auc=_AUC,
        calibrated=True,
    )