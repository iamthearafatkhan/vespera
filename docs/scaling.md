# Vespera — Scaling Notes

The single most-asked interview question about any web project:
**"What happens when this has 1M users?"**

This document answers that for Vespera with real numbers, a staged plan, and
an honest admission of where the current deployment breaks.

---

## Current state

| Layer | Choice | Why |
|---|---|---|
| App server | alwaysdata Python WSGI (gunicorn) | Free tier, no ops overhead |
| Database | PostgreSQL 17 (alwaysdata free) | Real SQL, real queries |
| Static files | WhiteNoise | No CDN needed at this scale |
| Background jobs | alwaysdata cron | Nightly model retraining |
| ML | scikit-learn, in-process | Fits on the request thread at this scale |

**Row counts at demo stage:** a few dozen users, low thousands of rows.
**Free-tier ceiling:** ~1,000 registered users before storage becomes the wall.

---

## Data volume per user

Every active user generates roughly:

| Entity | Rows / month | Notes |
|---|---|---|
| StudySessions | 20–60 | ~1 KB each including index |
| Expenses | 40–120 | ~0.5 KB each |
| HabitCheckins | 30–150 | one per habit per day |
| ClassEntry | 0 (static) | created once |
| ImportantDate | 0–5 (static) | created once |

**~1 KB / day / active user.** An idle user is ~0.5 KB static forever.

That gives us a rough projection table:

| Registered | Active (7d) | Rows in DB | Disk | What holds |
|---|---|---|---|---|
| 100 | 20 | ~50K | ~10 MB | Free tier comfortable |
| 1,000 | 200 | ~500K | ~100 MB | Free tier ceiling |
| 10,000 | 2,000 | ~5M | ~1 GB | Needs paid DB |
| 100,000 | 20,000 | ~50M | ~10 GB | Needs a real stack |
| 1,000,000 | 200,000 | ~500M | ~100 GB | Sharding + caching |

Assumption: 20% active-to-registered ratio. That's generous — most free apps sit closer to 10%.

---

## What breaks, in order — and the fix

### Stage 1 — 1K registered (~200 active). Free tier holds.

- All queries fit in PostgreSQL's working set.
- One gunicorn worker handles the request rate.
- No changes needed. This is where Vespera is today.

### Stage 2 — 10K registered (~2K active). Free tier hits walls.

**What breaks first:**

1. **Static file serving.** WhiteNoise is a Python process serving CSS/JS on the same box that runs Django. Above ~50 req/s of static assets, it competes with the app for CPU.
2. **Cold dashboard queries.** `study_last_days`, `spend_last_days`, and `habit_completion_last_days` each run aggregations over 14–60 days of the user's history. At 2K active users hitting `/` multiple times per session, these become the dominant DB load.
3. **Postgres connection limit.** Free tier caps at ~20 concurrent. Two gunicorn workers × 12 threads × per-request connections will exhaust it.

**Fixes:**

- **CDN for static files.** Cloudflare free tier. Zero config change — just move the `/static/` URL to the CDN origin.
- **Redis cache for `forecast_course()`.** Key: `forecast:{course_id}:{last_session_id}`. TTL 5 minutes. Invalidates naturally when a new session lands because the key changes.
- **PgBouncer in transaction mode.** Keeps app-side connections at 2–3 while Postgres sees 20+. Free-tier essential.
- **Add a covering index** on `StudySession (course_id, occurred_at DESC) INCLUDE (minutes)`. The forecast engine reads this exact pattern.

### Stage 3 — 100K registered (~20K active). Requires paid infrastructure.

**What breaks:**

1. **Forecast recomputation.** Even cached, 20K users × a few courses × hourly cache misses is a lot of Python work on the app servers.
2. **Dashboard N+1.** `dashboard/home.html` builds three chart series per request. Each is a separate DB round-trip.
3. **ML retraining.** Fitting a calibrated GBM on real data starts taking longer than a cron window.
4. **Disk I/O** for exports and PDFs — alwaysdata's free tier won't hold them.

**Fixes:**

- **Pre-aggregate daily stats.** Add a `DailyUserStats` table — one row per user per day, updated on write. `study_last_days` becomes a `SELECT ... WHERE user_id = ? AND day >= ?` on an indexed column. Dashboard drops from ~50ms to ~3ms.
- **Horizontal app servers.** 3–5 gunicorn instances behind a load balancer. Sessions move to Redis (`SESSION_ENGINE = "django.contrib.sessions.backends.cache"`) so any server can serve any request.
- **Read replica for analytics.** Dashboard queries go to the replica. Writes go to primary. 1-second lag is invisible to users.
- **Move ML training offline.** Nightly cron fits the model, serializes coefficients + scaler to a `ModelArtifact` row (or S3). Prediction becomes: load artifact → dot-product. No sklearn import in the request path.
- **Object storage** (S3-compatible) for CSV exports and generated PDFs.

### Stage 4 — 1M registered (~200K active). Distributed system.

**What breaks:**

1. **Single Postgres primary** can't take 200K users × ~5 writes/day = 1M writes/day plus everything else.
2. **Cross-user queries** — the `/staff/` metrics page — become expensive table scans.
3. **Model serving** at 200K users × hourly = 5M predictions/day.
4. **Backup window** exceeds any reasonable RPO.

**Fixes:**

- **Shard by `user_id`.** The schema is already shard-friendly: every user-owned model has a `user_id` FK, and there are **no cross-user JOINs** in the hot path. `user_id % N` routing sends every request to a single shard.
- **Separate OLTP from OLAP.** Postgres for transactional writes. ClickHouse or BigQuery for analytics aggregates. Dashboards query OLAP, never OLTP.
- **Event stream.** Kafka or Kinesis for activity events. Batched commits replace per-request writes.
- **Batch ML serving.** One request from the app server carries 1,000 user feature vectors → one response with 1,000 predictions. 1000× fewer round-trips than per-user inference.
- **Cold storage tier.** Sessions older than 90 days move to object storage. Only aggregates stay hot.
- **Model registry** with A/B routing — v1 and v2 serving side by side, with metrics.

---

## What to monitor before upgrading

These are the four numbers that predict each stage. All are measurable today.

| Metric | Where | Alert threshold |
|---|---|---|
| Active / registered ratio | `/staff/` metrics page | > 30% (shrinks the free tier window) |
| DB disk used | alwaysdata panel | 80% of plan |
| P95 dashboard response | Django debug toolbar (dev), New Relic (prod) | > 400ms |
| Postgres slow queries | `log_min_duration_statement = 500` | Any query > 500ms |

If any two thresholds fire, it's time to execute the next stage.

---

## What I would NOT do

Deliberately listed because "not doing things" is as important as doing them.

- **Not shard early.** A single well-indexed Postgres on a $20/mo VPS handles 10K users. Sharding before 100K wastes engineering hours.
- **Not use NoSQL.** The data is fundamentally relational — users → courses → sessions, users → habits → checkins. Postgres is the right tool. MongoDB would be a downgrade.
- **Not add a message queue at 2K users.** Cron is enough until sub-minute latency is a user-visible feature.
- **Not pre-optimize the ML model.** A GBM that fits in 50ms and runs on the request thread is fine until 10K active users. Microservices for prediction are premature.
- **Not chase distributed tracing before there's a distributed system.** Logs + Sentry catch 95% of production bugs at this scale.

---

## The load test (roadmap)

Planned in `docs/loadtest.py` (not yet written):

1. Generate 1M synthetic users, 20M sessions, 5M expenses, 10M habit checkins with realistic distributions (power-law activity, 20% active ratio).
2. Run Locust against the three hot endpoints: `/` (dashboard), `/courses/` (list + forecast), `/expenses/insights/` (aggregates).
3. Produce a report with RPS, P50/P95/P99, and the exact request count where the free tier breaks.

Target when written: **100 RPS at P95 < 300ms on the free tier.** That's the empirical ceiling. Everything above it triggers Stage 2.

---

## Honest summary

Vespera is not a 1M-user product today. It's a portfolio project that is *designed* for 1M, *deployed* for hundreds, and *documented* for both.

This document exists because **knowing where your app breaks is more valuable than pretending it doesn't.**