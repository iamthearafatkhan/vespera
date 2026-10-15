# expenses/views.py
from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ExpenseForm
from .models import Expense


# ------------------------------------------------------------------
# List view (existing)
# ------------------------------------------------------------------

@login_required
def expense_list(request):
    """Main view: form + monthly summary + recent list, all on one page."""
    today = timezone.localdate()
    month_str = request.GET.get("month", today.strftime("%Y-%m"))
    try:
        year, month = map(int, month_str.split("-"))
    except ValueError:
        year, month = today.year, today.month
        month_str = f"{year:04d}-{month:02d}"

    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    month_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=first,
        occurred_at__date__lte=last,
    )

    total = month_qs.aggregate(s=Sum("amount"))["s"] or 0
    by_category = (
        month_qs.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    recent = month_qs[:20]

    return render(request, "expenses/list.html", {
        "form": ExpenseForm(),
        "recent": recent,
        "total": total,
        "by_category": by_category,
        "month_str": month_str,
        "month_label": first.strftime("%B %Y"),
    })


# ------------------------------------------------------------------
# Trends / insights view (weekly + monthly + savings)
# ------------------------------------------------------------------

def _range_for(mode: str, anchor: date):
    """Return (start, end, label) for the current period."""
    if mode == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        label = f"Week of {start.strftime('%b %d, %Y')}"
    else:
        start = anchor.replace(day=1)
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1, day=1)
        else:
            nxt = start.replace(month=start.month + 1, day=1)
        end = nxt - timedelta(days=1)
        label = start.strftime("%B %Y")
    return start, end, label


def _prev_range(mode: str, start: date, end: date):
    """Same-length period immediately before [start, end]."""
    length = (end - start).days + 1
    return start - timedelta(days=length), start - timedelta(days=1)


@login_required                                     # ← MISSING BEFORE, ADDED HERE
def insights_view(request):
    """Weekly / monthly view with savings comparison and trend."""
    today = timezone.localdate()
    mode = request.GET.get("mode", "month")
    if mode not in ("week", "month"):
        mode = "month"

    start, end, label = _range_for(mode, today)
    p_start, p_end = _prev_range(mode, start, end)

    this_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=start,
        occurred_at__date__lte=end,
    )
    this_total = this_qs.aggregate(s=Sum("amount"))["s"] or 0

    last_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=p_start,
        occurred_at__date__lte=p_end,
    )
    last_total = last_qs.aggregate(s=Sum("amount"))["s"] or 0

    delta = this_total - last_total
    delta_pct = None
    if last_total > 0:
        delta_pct = float(delta / last_total * 100)

    # linear trend on daily totals in this period
    daily = (
        this_qs.values("occurred_at__date")
        .annotate(total=Sum("amount"))
        .order_by("occurred_at__date")
    )
    series = list(daily)
    trend_label = "steady"
    if len(series) >= 4:
        xs = list(range(len(series)))
        ys = [float(r["total"]) for r in series]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = sum((x - mx) ** 2 for x in xs)
        slope = num / den if den else 0
        pct_per_day = (slope / (my or 1)) * 100
        if pct_per_day > 2:
            trend_label = "rising"
        elif pct_per_day < -2:
            trend_label = "falling"

    # last 6 periods bars
    trunc = TruncWeek("occurred_at") if mode == "week" else TruncMonth("occurred_at")
    history = list(reversed(list(
        Expense.objects
        .filter(user=request.user)
        .annotate(bucket=trunc)
        .values("bucket")
        .annotate(total=Sum("amount"))
        .order_by("-bucket")[:6]
    )))

    hist_labels = [
        h["bucket"].strftime("%b %d" if mode == "week" else "%b %Y")
        for h in history
    ]
    hist_values = [float(h["total"]) for h in history]

    return render(request, "expenses/insights.html", {
        "mode": mode,
        "label": label,
        "this_total": this_total,
        "last_total": last_total,
        "delta": delta,
        "delta_pct": delta_pct,
        "trend_label": trend_label,
        "hist_labels": hist_labels,
        "hist_values": hist_values,
    })


# ------------------------------------------------------------------
# Add / delete (existing)
# ------------------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def expense_add(request):
    form = ExpenseForm(request.POST)
    if form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        messages.success(request, "Expense added.")
    else:
        messages.error(request, "Could not save — check the values.")

    if request.headers.get("HX-Request"):
        return _render_recent(request)
    return redirect("expenses:list")


@login_required
@require_http_methods(["POST"])
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()
    if request.headers.get("HX-Request"):
        return _render_recent(request)
    return redirect("expenses:list")


def _render_recent(request):
    today = timezone.localdate()
    first = today.replace(day=1)
    month_qs = Expense.objects.filter(
        user=request.user, occurred_at__date__gte=first
    )
    return render(request, "expenses/_recent.html", {
        "recent": month_qs[:20],
        "total": month_qs.aggregate(s=Sum("amount"))["s"] or 0,
        "by_category": month_qs.values("category").annotate(total=Sum("amount")).order_by("-total"),
    })