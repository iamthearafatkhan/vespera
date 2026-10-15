# Vespera — Scaling Notes

This document answers the question every interviewer asks:
**"What happens when you have 1M users?"**

Spoiler: the current deployment is sized for ~500 active users on a free
tier. This is what would change — and in what order — to serve 1M.

## Current deployment

| Component | Choice | Why |
|---|---|---|
| App server | alwaysdata Python WSGI (gunicorn) | Free tier, no ops overhead |
| Database | PostgreSQL 17 (alwaysdata free) | Real SQL, real queries |
| Static files | WhiteNoise | No CDN needed at this scale |
| Background jobs | alwaysdata cron | Nightly model retraining |
| Row count, real | < 100 | Demo stage |

## Free-tier ceiling (measured)

Rough numbers from running the seed script locally:

| Users (registered) | Active (last 7d) | Rows in DB | Disk | Notes |
|---|---|---|---|---|
| 100 | 20 | ~15K | ~5 MB | Free tier comfortable |
| 1,000 | 200 | ~150K | ~50 MB | Free tier limit approaching |
| 10,000 | 2,000 | ~1.5M | ~500 MB | Need paid DB |
| 100,000 | 20,000 | ~15M | ~5 GB | Need a real stack |
| 1,000,000 | 200,000 | ~150M | ~50 GB | Sharding + caching required |

**Rule of thumb**: every active user adds ~1 KB/day across all trackers.
Every registered-but-idle user is ~0.5 KB static.

## What breaks first, and how to fix each

### Stage 1 — 1K registered (~200 active). Free tier holds.
- All queries fit in RAM.
- Single gunicorn worker handles the load.
- No changes needed.

### Stage 2 — 10K registered (~2K active). Free tier hits walls.
- **Read replicas** for the dashboard queries (`study_last_days`, `spend_last_days`, etc.). They're read-only and can tolerate 1s lag.
- **Redis cache** for `forecast_course()` — the same user refreshing doesn't need recompute. Key: `forecast:{course_id}:{last_session_id}`. TTL 5 minutes.
- **Database connection pooling** (PgBouncer). Free-tier Postgres drops connections above ~20 concurrent.
- **CDN** for static files (Cloudflare free). WhiteNoise becomes a bottleneck above ~50 req/s.

### Stage 3 — 100K registered (~20K active). Requires paid infrastructure.
- **Horizontal app servers**: 3–5 gunicorn instances behind a load balancer.
- **Read replica for analytics**: dashboards go to a replica, writes go to primary.
- **Pre-aggregate daily metrics**: instead of `SUM(minutes)` on every dashboard load, maintain a `DailyUserStats` table updated on session write. Dashboard becomes a single indexed lookup.
- **Move ML training offline**: nightly cron retrains and stores coefficients in a `ModelArtifact` table. Prediction becomes a load + dot-product, not a live sklearn call.
- **Object storage** (S3) for exports and generated PDFs — alwaysdata disk won't hold them.

### Stage 4 — 1M registered (~200K active). Distributed system.
- **Shard by `user_id % N`**: all user-scoped queries become single-shard after routing. No cross-user JOINs exist in the schema, so this is clean.
- **Separate OLTP and OLAP**: Postgres for writes, ClickHouse or BigQuery for analytics aggregates. Dashboards query OLAP.
- **Model serving** as a separate microservice with a cached batch API: send 1000 user feature vectors, get 1000 predictions. Single round-trip.
- **Event stream** (Kafka) for activity: replaces per-request writes with batched commits.
- **Session store**: Redis instead of DB. Django `SESSION_ENGINE = "django.contrib.sessions.backends.cache"`.
- **Cold storage**: sessions older than 90 days to object storage; only aggregates stay hot.

## What I'd monitor before upgrading

The `/staff/` metrics page tracks exactly the numbers that predict the ceiling:

- **Active / Total ratio** — if 20% of registered users are active, free tier lasts to ~1K. If 50%, the ceiling drops to ~400.
- **DB size** — alwaysdata shows this in the panel. Alert at 80% of plan.
- **P95 response time** — anything above 400ms on the dashboard means a query needs an index or a cache.
- **Slow query log** — Postgres `log_min_duration_statement = 500`.

## What I would NOT do

- **Not shard early.** A single well-indexed Postgres handles 10K users on a $20 VPS.
- **Not use NoSQL.** The data is relational (users → courses → sessions). Postgres is the right tool.
- **Not add a message queue at 2K users.** Cron is enough until you need sub-minute latency.

## The load test (planned)

`docs/loadtest.py` (not yet written) will:
1. Generate 1M synthetic users + 20M sessions + 5M expenses.
2. Run Locust against the dashboard + course detail endpoints.
3. Produce a report: RPS, P50/P95/P99, and where it breaks.

Target when written: 100 RPS at P95 < 300ms on the free tier — the number
that tells us exactly when to upgrade.