# courses/services.py
"""
Forecast engine for Vespera.

Given a course's session history, we answer three questions:
  1. How fast is the user actually studying? (daily_rate)
  2. When will they finish at that pace? (predicted_finish)
  3. How confident are we? (earliest / latest = 80% interval)

Method:
  - Build a daily time series of minutes studied over the last WINDOW days.
  - Compute a *weighted* mean so recent activity counts more than old activity.
  - Propagate uncertainty: days_to_finish = remaining / rate.
    If rate has std σ_r, then std in days ≈ remaining * σ_r / rate².
  - Use ±1.28σ for an 80% confidence interval (nice for a consumer UI).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import pstdev

from django.db.models import Sum
from django.utils import timezone

WINDOW_DAYS = 30          # how far back we look
CI_Z = 1.28               # 80% interval (2-sided)


@dataclass
class Forecast:
    studied_minutes: int
    remaining_minutes: int
    progress_pct: float
    daily_rate: float                     # minutes per day (weighted)
    days_to_finish: int | None            # None → not enough signal
    predicted_finish: date | None
    earliest_finish: date | None
    latest_finish: date | None
    momentum: str                         # rising | steady | fading | stalled
    is_complete: bool


def _daily_series(course, window=WINDOW_DAYS) -> list[int]:
    """Return a list of `window` ints — minutes studied per day, oldest first."""
    today = timezone.localdate()
    start = today - timedelta(days=window - 1)

    # one query, aggregated by date — cheap and portable
    rows = (
        course.sessions
        .filter(occurred_at__date__gte=start)
        .values("occurred_at__date")
        .annotate(total=Sum("minutes"))
    )
    by_day = {r["occurred_at__date"]: r["total"] for r in rows}

    return [by_day.get(start + timedelta(days=i), 0) for i in range(window)]


def _weighted_rate(series: list[int]) -> float:
    """Weight recent days more. Day i gets weight (i+1)."""
    weights = [i + 1 for i in range(len(series))]
    return sum(x * w for x, w in zip(series, weights)) / sum(weights)


def _momentum(series: list[int]) -> str:
    """Compare the last 7 days to the 7 before that."""
    last7, prev7 = series[-7:], series[-14:-7]
    a = sum(last7) / 7
    b = sum(prev7) / 7
    if a == 0 and b == 0:
        return "stalled"
    if a == 0:
        return "fading"
    if b == 0:
        return "rising"
    ratio = a / b
    if ratio >= 1.2:
        return "rising"
    if ratio <= 0.8:
        return "fading"
    return "steady"


def forecast_course(course) -> Forecast:
    """Compute the full Forecast object for a course."""
    studied = course.studied_minutes
    remaining = course.remaining_minutes
    pct = course.progress_pct

    # already done → no forecast needed
    if remaining == 0:
        return Forecast(
            studied_minutes=studied, remaining_minutes=0, progress_pct=100.0,
            daily_rate=0.0, days_to_finish=0, predicted_finish=timezone.localdate(),
            earliest_finish=timezone.localdate(), latest_finish=timezone.localdate(),
            momentum="steady", is_complete=True,
        )

    series = _daily_series(course)
    rate = _weighted_rate(series)
    momentum = _momentum(series)

    # not enough signal — user has barely any history
    if rate < 1:            # < 1 min/day averaged → can't forecast honestly
        return Forecast(
            studied_minutes=studied, remaining_minutes=remaining, progress_pct=pct,
            daily_rate=rate, days_to_finish=None, predicted_finish=None,
            earliest_finish=None, latest_finish=None,
            momentum=momentum, is_complete=False,
        )

    days = remaining / rate

    # uncertainty: only nonzero days carry information
    nonzero = [x for x in series if x > 0]
    sigma_rate = pstdev(nonzero) if len(nonzero) >= 2 else 0
    sigma_days = (remaining * sigma_rate / (rate ** 2)) if rate > 0 else 0

    today = timezone.localdate()
    predicted = today + timedelta(days=round(days))
    earliest = today + timedelta(days=max(0, round(days - CI_Z * sigma_days)))
    latest   = today + timedelta(days=round(days + CI_Z * sigma_days))

    return Forecast(
        studied_minutes=studied, remaining_minutes=remaining, progress_pct=pct,
        daily_rate=rate, days_to_finish=round(days),
        predicted_finish=predicted, earliest_finish=earliest, latest_finish=latest,
        momentum=momentum, is_complete=False,
    )

# courses/services.py — append these

def simulate_course(course, extra_minutes_per_day: int = 0, weekday_only: bool = True):
    """Return a dict with the *simulated* forecast if the user adds
    `extra_minutes_per_day` on weekdays (or every day).

    We reuse the exact same math as forecast_course — only the daily series
    changes. This keeps the baseline and the simulation directly comparable.
    """
    if extra_minutes_per_day <= 0:
        return None  # caller will show the baseline only

    series = _daily_series(course, window=WINDOW_DAYS)
    today = timezone.localdate()
    start = today - timedelta(days=WINDOW_DAYS - 1)

    # apply the "what if" boost to each day in the window
    boosted = []
    for i, m in enumerate(series):
        d = start + timedelta(days=i)
        if weekday_only and d.weekday() >= 5:      # Sat=5, Sun=6
            boosted.append(m)                      # weekend unchanged
        else:
            boosted.append(m + extra_minutes_per_day)

    rate = _weighted_rate(boosted)
    if rate < 1:
        return None

    remaining = course.remaining_minutes
    days = remaining / rate

    # same uncertainty propagation as the baseline
    nonzero = [x for x in boosted if x > 0]
    sigma_rate = pstdev(nonzero) if len(nonzero) >= 2 else 0
    sigma_days = (remaining * sigma_rate / (rate ** 2)) if rate > 0 else 0

    predicted = today + timedelta(days=round(days))
    earliest = today + timedelta(days=max(0, round(days - CI_Z * sigma_days)))
    latest = today + timedelta(days=round(days + CI_Z * sigma_days))

    return {
        "rate": rate,
        "days_to_finish": round(days),
        "predicted_finish": predicted,
        "earliest_finish": earliest,
        "latest_finish": latest,
    }