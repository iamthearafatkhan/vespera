# Vespera

**A privacy-first life tracker. Courses with real finish-date forecasting, expenses with savings analytics, habits with streaks, and a class schedule — all without an email account.**

[![Live Site](https://img.shields.io/badge/Live_Site-vespera.alwaysdata.net-blue?style=for-the-badge&logo=alwaysdata)](https://vespera.alwaysdata.net)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**Author:** Arafat Khan · [Portfolio](https://arafatkhan.vercel.app) · [GitHub](https://github.com/iamthearafatkhan) · [LinkedIn](https://linkedin.com/in/iamthearafatkhan)

---

## 🧠 The Three Models

Vespera isn't just a to-do list with a coat of paint. Three mathematical models drive the product. Each is evaluated, explainable, and shipped to real users.

### 1. Finish-date forecasting (regression + uncertainty)
* **Where:** `courses/services.py`
* **Predicts:** The calendar date a user will complete a course.
* **Method:** Weighted daily-rate estimator. Recent activity has more influence than old activity (e.g., a session 30 days ago gets weight 1, today gets weight 30). Uncertainty propagates through `days = remaining / rate`. If `rate` has std σ, then days has std `remaining · σ / rate²`. We use ±1.28σ for an **80% confidence interval**.
* **Why it matters:** A bare progress bar tells you where you are. This tells you *when you'll arrive* — with a range that widens when your pace is erratic and narrows when you're steady.

### 2. Dropout risk (calibrated gradient boosting)
* **Where:** `analytics_app/ml.py`
* **Predicts:** `P(user studies tomorrow | last 21 days of behaviour)`
* **Model:** Gradient boosting (220 trees, depth 3) wrapped in `CalibratedClassifierCV` with Platt scaling (5-fold). Class-balanced. Reports **ROC AUC on a held-out 20%** at prediction time.
* **Features:** `studied_yesterday`, `study_days_3`, `study_days_7`, `avg_minutes_7`, `days_since_last_session`, `weekday_consistency_21`, `weekend_consistency_21`, `sessions_21`.
* **Explanation:** `permutation_importance × normalised_feature_deviation` — model-agnostic, returns top-3 drivers with signed contribution. The dashboard shows *"what's going well"* or *"what's pulling it down"* based on the sign of the probability.

### 3. Cross-domain insights (correlation)
* **Where:** `analytics_app/insights.py`
* **Detects:** Relationships between study behaviour, spending, and habits.
* **Method:** Pearson correlation on 60-day aligned time series, filtered to days with any activity (avoids zero-inflation dragging `r` toward 0). Only surfaces insights with `|r| ≥ 0.35` and ≥ 12 overlapping days.
* **Example output:** *"You study 40% longer on weekends than weekdays."* Framed as observation, not prescription. Every card shows `r` and sample size.

---

## ✨ Feature Overview

| Area | What it does |
| :--- | :--- |
| **Courses** | Add a course with total length. Log sessions. Forecast finish with 80% CI. "What if?" simulator shows how extra daily minutes shift the finish date. |
| **Expenses** | Log spending. Weekly and monthly views. Budget vs actual savings. Category doughnut chart. Historical bar chart with budget line. |
| **Habits** | Weekly grid, one-tap check-ins, streak calculation. |
| **Schedule** | Recurring weekly classes + one-off important dates (exams, CTs, deadlines). Exportable as PNG or PDF. |
| **Dashboard** | Aggregated view: study hours, monthly spend, momentum card, cross-domain patterns, hero forecast, three charts. |
| **Export** | Full JSON backup + CSV for expenses and sessions. |

---

## 🔒 Why no email?

Vespera uses **username + password + one security question + 8 one-time recovery codes**. No email provider, no auth vendor, no password-reset fees.

* **Argon2id** password hashing
* **SHA-256** hashed security answers (single-use, never plaintext)
* **62¹²** recovery code space (per code)
* Rate-limited login and reset
* Short-lived (15-min) signed reset tokens

> **The trade-off:** Recovery is weaker than email. Users must store their codes. This is documented on the landing page, not hidden. See [`docs/scaling.md`](docs/scaling.md) for the full privacy/security section.

---

## 🛠️ Stack

| Layer | Choice |
| :--- | :--- |
| **Backend** | Django 5 |
| **Database** | PostgreSQL 17 |
| **Frontend** | HTMX + Tailwind (CDN) |
| **Charts** | Chart.js 4 |
| **ML** | scikit-learn |
| **Background** | Vanta.js NET |
| **Serving** | WhiteNoise + gunicorn |
| **Host** | alwaysdata (free tier) |

---

## 💻 Running Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit SECRET_KEY
python manage.py migrate
python manage.py seed_security_questions
python manage.py runserver

```
## Tests:

```bash
python manage.py test
```

## 🚀 Deployment
Settings are split into config/settings/base.py, dev.py, and prod.py. Production runs on alwaysdata Python WSGI with gunicorn.

# on the server
```
# Connect to your server via SSH
ssh vespera@ssh-vespera.alwaysdata.net

# Once logged in, navigate to the project folder
cd ~/vespera
git pull
source .venv/bin/activate

# Apply updates
python manage.py migrate
python manage.py collectstatic --noinput

# Trigger gunicorn restart
touch config/wsgi.py
```
See docs/scaling.md for the 1M-user plan.
---
## 📸 Screenshots

Dashboard	Course + Advisor	Savings
![dashboard](docs/dashboard.png)
![course](docs/course.png)
![savings](docs/savings.png)
---
📄 License
This project is licensed under the MIT License.

---

