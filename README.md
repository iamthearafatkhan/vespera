# Vespera

**A privacy-first life tracker. Courses with real finish-date forecasting.
Expenses with savings analytics. Habits with streaks.**

**Live:** https://vespera.alwaysdata.net
**Author:** Arafat Khan · [arafatkhan.vercel.app](https://arafatkhan.vercel.app) · [GitHub](https://github.com/iamthearafatkhan) · [LinkedIn](https://linkedin.com/in/iamthearafatkhan)

---

## The three models

Vespera isn't a to-do list. Three models drive the product. All are
evaluated, explainable, and shipped to real users.

### 1. Finish-date forecasting (regression)

**Where:** `courses/services.py`
**Predicts:** the calendar date a user will complete a course.
**Method:** weighted daily-rate estimator. Recent activity has more influence
than old activity (linear weight, so day-30 has 1× and today has 30×).
Uncertainty propagates through `days = remaining / rate`: if `rate` has
std σ, then days has std `remaining · σ / rate²`. We use ±1.28σ for an
**80% confidence interval**.

**Why it matters:** a bare progress bar tells you where you are. This tells
you *when you'll arrive* — with a range.

### 2. Dropout risk (calibrated classification)

**Where:** `analytics_app/ml.py`
**Predicts:** `P(user studies tomorrow | last 21 days of behaviour)`
**Model:** Gradient boosting (220 trees, depth 3) wrapped in
`CalibratedClassifierCV` with Platt scaling. Class-balanced. Reported
**ROC AUC on a held-out 20%** at prediction time — logged and shown to the user.

**8 engineered features:**
`studied_yesterday`, `study_days_3`, `study_days_7`, `avg_minutes_7`,
`days_since_last_session`, `weekday_consistency_21`, `weekend_consistency_21`,
`sessions_21`.

**Explanation:** `permutation_importance × normalised_feature_deviation`.
Model-agnostic. Returns top-3 drivers with signed contribution — the same
positive/negative phrasing you'd expect from SHAP, at 1/50th the cost.

### 3. Cross-domain insights (correlation)

**Where:** `analytics_app/insights.py`
**Detects:** relationships between study behaviour, spending, and habits.
**Method:** Pearson correlation on 60-day aligned time series, filtered to
days with any activity (avoids zero-inflation biasing `r` toward zero).
Only surfaces insights with `|r| ≥ 0.35` and ≥ 12 overlapping days.

**Example output:** *"You study 40% longer on weekends than weekdays."*
Framed as observation, not prescription. Every insight card shows `r` and
sample size.

---

## Why no email?

Vespera uses **username + password + security question + one-time recovery codes**.
No email provider, no auth vendor, no password-reset fees.

- Argon2id password hashing
- SHA-256 hashed security answers (single-use, never plaintext)
- 8 single-use recovery codes with `62¹²` search space
- Rate-limited login and reset
- Short-lived (15-min) signed reset tokens

**The trade-off:** recovery is weaker than email. You must store your codes.
This is documented on the landing page, not hidden.

---

## Stack

Django 5 · PostgreSQL 17 · HTMX · Tailwind (CDN) · Chart.js ·
scikit-learn · Vanta.js · WhiteNoise · gunicorn · alwaysdata

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit SECRET_KEY
python manage.py migrate
python manage.py seed_security_questions
python manage.py runserver

```
## Tests:

bash
python manage.py test

## Deployment
config/settings/ splits dev/prod. Production runs on alwaysdata Python
WSGI with gunicorn. See docs/scaling.md for the
1M-user capacity plan and load-test roadmap.