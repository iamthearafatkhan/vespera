# analytics_app/insights.py
"""Cross-domain insight detection.

For each pair of behaviours (study / spend / habits) we:
  1. Build aligned daily time series over a shared window.
  2. Compute Pearson correlation on the aligned pairs.
  3. Keep only pairs with |r| >= threshold AND enough non-zero overlap.
  4. Translate to a plain-English sentence.

We deliberately over-produce candidate insights and rank them — the UI
shows the top 3. Numbers are honest; language stays soft ("tends to",
"on days you…"), because correlation is not causation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from statistics import mean, pstdev

from django.utils import timezone

WINDOW_DAYS = 60              # look back this far
MIN_ACTIVE_PAIRS = 12         # require at least this many overlapping days
MIN_ABS_R = 0.35              # correlation strength floor


@dataclass
class Insight:
    title: str                 # plain-English sentence
    r: float                   # Pearson correlation (signed)
    strength: float            # |r|, for ranking
    sample: int                # how many days went into it


def _series(user, extractor, days=WINDOW_DAYS) -> list[tuple]:
    """Build [(date, value), ...] oldest → newest for the last `days` days."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    raw = extractor(user, start, today)          # {date: value}
    return [(start + timedelta(days=i), raw.get(start + timedelta(days=i), 0))
            for i in range(days)]


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    den = (sum(a * a for a in dx) ** 0.5) * (sum(b * b for b in dy) ** 0.5)
    if den == 0:
        return None
    return num / den


# ---------------- extractors ----------------

def _study_minutes_by_day(user, start, end) -> dict:
    from django.db.models import Sum
    rows = (
        user.courses
        .filter(sessions__occurred_at__date__gte=start,
                sessions__occurred_at__date__lte=end)
        .values("sessions__occurred_at__date")
        .annotate(total=Sum("sessions__minutes"))
    )
    return {r["sessions__occurred_at__date"]: (r["total"] or 0) for r in rows}


def _spend_by_day(user, start, end) -> dict:
    from expenses.models import Expense
    from django.db.models import Sum
    rows = (
        Expense.objects
        .filter(user=user, occurred_at__date__gte=start, occurred_at__date__lte=end)
        .values("occurred_at__date")
        .annotate(total=Sum("amount"))
    )
    return {r["occurred_at__date"]: float(r["total"] or 0) for r in rows}


def _habit_count_by_day(user, start, end) -> dict:
    from routines.models import HabitCheckin
    from django.db.models import Count
    rows = (
        HabitCheckin.objects
        .filter(habit__user=user, day__gte=start, day__lte=end)
        .values("day").annotate(c=Count("id"))
    )
    return {r["day"]: r["c"] for r in rows}


# ---------------- insight generators ----------------

def _study_vs_spend(user) -> list[Insight]:
    study = _series(user, _study_minutes_by_day)
    spend = _series(user, _spend_by_day)
    study_v = [s for _, s in study]
    spend_v = [s for _, s in spend]

    # only compare days where *some* signal exists — otherwise a run of zeros
    # drags every correlation toward 0 and looks like a real finding
    pairs = [(s, d) for s, d in zip(study_v, spend_v) if s > 0 or d > 0]
    if len(pairs) < MIN_ACTIVE_PAIRS:
        return []

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    r = _pearson(xs, ys)
    if r is None or abs(r) < MIN_ABS_R:
        return []

    if r < 0:
        title = (
            "You tend to study *less* on days you spend more. "
            "Worth checking if high-spend days are also your busiest."
        )
    else:
        title = (
            "Your study and spending tend to rise together — "
            "these could both track your overall energy level."
        )
    return [Insight(title=title, r=r, strength=abs(r), sample=len(pairs))]


def _study_vs_habits(user) -> list[Insight]:
    study = _series(user, _study_minutes_by_day)
    habits = _series(user, _habit_count_by_day)

    pairs = [(s, h) for (_, s), (_, h) in zip(study, habits) if s > 0 or h > 0]
    if len(pairs) < MIN_ACTIVE_PAIRS:
        return []

    r = _pearson([p[0] for p in pairs], [p[1] for p in pairs])
    if r is None or abs(r) < MIN_ABS_R:
        return []

    if r > 0:
        title = (
            "On days you study, you also keep more of your habits. "
            "Study days look like your anchor days."
        )
    else:
        title = (
            "Your habits drop on heavy study days — "
            "consider protecting one small habit even on big study days."
        )
    return [Insight(title=title, r=r, strength=abs(r), sample=len(pairs))]


def _weekday_vs_weekend_study(user) -> list[Insight]:
    study = _series(user, _study_minutes_by_day)
    wd = [s for d, s in study if d.weekday() < 5 and s > 0]
    we = [s for d, s in study if d.weekday() >= 5 and s > 0]
    if len(wd) < 5 or len(we) < 3:
        return []

    mw, me = mean(wd), mean(we)
    if mw <= 0 and me <= 0:
        return []

    # ratio as a soft signal, converted to a strength score
    if me > mw * 1.4:
        title = f"You study {round((me/mw - 1)*100)}% longer on weekends than weekdays."
        strength = min((me / mw) - 1, 1.0)
    elif mw > me * 1.4:
        title = f"You study {round((mw/me - 1)*100)}% longer on weekdays than weekends."
        strength = min((mw / me) - 1, 1.0)
    else:
        return []

    return [Insight(title=title, r=0.0, strength=strength, sample=len(wd) + len(we))]


# ---------------- public API ----------------

def generate_insights(user, limit: int = 3) -> list[Insight]:
    """Return up to `limit` insights, strongest first."""
    candidates: list[Insight] = []
    for fn in (_study_vs_spend, _study_vs_habits, _weekday_vs_weekend_study):
        try:
            candidates.extend(fn(user))
        except Exception:
            # never let one bad extractor kill the whole dashboard
            continue
    candidates.sort(key=lambda i: i.strength, reverse=True)
    return candidates[:limit]