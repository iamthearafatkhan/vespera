# analytics_app/features.py
"""Build the 8-float feature vector for a user from their session history."""
from datetime import timedelta

from django.utils import timezone


def build_features_for_user(user) -> list[float]:
    """Return the feature vector for the dropout-risk model."""
    today = timezone.localdate()

    # gather all session days in the last 21 days in one query
    qs = (
        user.courses
        .values_list("sessions__occurred_at__date", "sessions__minutes")
    )
    # filter out nulls from courses with no sessions
    sessions = [(d, m) for d, m in qs if d is not None]

    by_day: dict = {}
    for d, m in sessions:
        by_day[d] = by_day.get(d, 0) + (m or 0)

    def studied_on(day):
        return 1 if by_day.get(day, 0) > 0 else 0

    studied_yesterday = studied_on(today - timedelta(days=1))
    last3 = sum(studied_on(today - timedelta(days=i)) for i in range(3))
    last7 = sum(studied_on(today - timedelta(days=i)) for i in range(7))

    last7_min = sum(by_day.get(today - timedelta(days=i), 0) for i in range(7))
    avg_min_7 = last7_min / 7.0

    # days since last session (capped at 21)
    since = 21
    for i in range(22):
        if by_day.get(today - timedelta(days=i), 0) > 0:
            since = i
            break

    # consistency over last 21 days, split weekday / weekend
    wd_hits = wd_total = we_hits = we_total = 0
    sessions_21 = 0
    for i in range(21):
        d = today - timedelta(days=i)
        hit = by_day.get(d, 0) > 0
        if hit:
            sessions_21 += 1
        if d.weekday() < 5:
            wd_total += 1
            wd_hits += int(hit)
        else:
            we_total += 1
            we_hits += int(hit)

    wd_consistency = wd_hits / wd_total if wd_total else 0.0
    we_consistency = we_hits / we_total if we_total else 0.0

    return [
        float(studied_yesterday),
        float(last3),
        float(last7),
        float(avg_min_7),
        float(since),
        float(wd_consistency),
        float(we_consistency),
        float(sessions_21),
    ]