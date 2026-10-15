# expenses/views.py
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ExpenseForm
from .models import Expense, MonthlyBudget


# ------------------------------------------------------------------
# LIST VIEW
# ------------------------------------------------------------------

@login_required
def expense_list(request):
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
    by_category = month_qs.values("category").annotate(total=Sum("amount")).order_by("-total")

    return render(request, "expenses/list.html", {
        "form": ExpenseForm(),
        "recent": month_qs[:20],
        "total": total,
        "by_category": by_category,
        "month_str": month_str,
        "month_label": first.strftime("%B %Y"),
    })


# ------------------------------------------------------------------
# INSIGHTS / SAVINGS VIEW
# ------------------------------------------------------------------

def _range_for(mode: str, anchor: date):
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


def _prev_range(start: date, end: date):
    length = (end - start).days + 1
    return start - timedelta(days=length), start - timedelta(days=1)


@login_required
def insights_view(request):
    """Weekly / monthly savings view with historical bar chart."""
    today = timezone.localdate()
    mode = request.GET.get("mode", "month")
    if mode not in ("week", "month"):
        mode = "month"

    start, end, label = _range_for(mode, today)
    p_start, p_end = _prev_range(start, end)

    # this period
    this_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=start,
        occurred_at__date__lte=end,
    )
    this_total = this_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

    # previous period
    last_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=p_start,
        occurred_at__date__lte=p_end,
    )
    last_total = last_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

    # ---- savings math ----
    # Priority 1: if user set a budget, savings = budget - spend
    # Priority 2: otherwise savings = previous period spend - this period spend
    budget = MonthlyBudget.objects.filter(user=request.user).first()
    budget_for_period = None

    if budget and budget.amount > 0:
        # weekly budget = monthly / 4.333 (52 weeks / 12 months)
        budget_for_period = budget.amount if mode == "month" else (budget.amount / Decimal("4.333"))
        savings = budget_for_period - this_total
        savings_source = "budget"
    else:
        savings = last_total - this_total
        savings_source = "comparison"

    # percentage spent of budget / of last period
    spend_pct_of_target = None
    if budget_for_period and budget_for_period > 0:
        spend_pct_of_target = float(this_total / budget_for_period * 100)

    # delta vs last period
    delta = this_total - last_total
    delta_pct = None
    if last_total > 0:
        delta_pct = float(delta / last_total * 100)

    # ---- trend ----
    daily = list(
        this_qs.values("occurred_at__date")
        .annotate(total=Sum("amount"))
        .order_by("occurred_at__date")
    )
    trend_label = "steady"
    if len(daily) >= 4:
        xs = list(range(len(daily)))
        ys = [float(r["total"]) for r in daily]
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

    # ---- history for chart: last 8 periods ----
    trunc = TruncWeek("occurred_at") if mode == "week" else TruncMonth("occurred_at")
    history = list(reversed(list(
        Expense.objects
        .filter(user=request.user)
        .annotate(bucket=trunc)
        .values("bucket")
        .annotate(total=Sum("amount"))
        .order_by("-bucket")[:8]
    )))

    hist_labels = [
        h["bucket"].strftime("%b %d" if mode == "week" else "%b %y")
        for h in history
    ]
    hist_values = [float(h["total"]) for h in history]

    # ---- budget line for chart (per period) ----
    chart_budget = None
    if budget and budget.amount > 0:
        chart_budget = float(
            budget.amount if mode == "month" else (budget.amount / Decimal("4.333"))
        )

    # ---- category breakdown for this period ----
    by_category = list(
        this_qs.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    cat_labels = [dict(Expense.CATEGORY_CHOICES).get(r["category"], r["category"]) for r in by_category]
    cat_values = [float(r["total"]) for r in by_category]

    return render(request, "expenses/insights.html", {
        "mode": mode,
        "label": label,
        "this_total": this_total,
        "last_total": last_total,
        "delta": delta,
        "delta_pct": delta_pct,
        "savings": savings,
        "savings_source": savings_source,
        "budget": budget,
        "budget_for_period": budget_for_period,
        "spend_pct_of_target": spend_pct_of_target,
        "trend_label": trend_label,
        "hist_labels": hist_labels,
        "hist_values": hist_values,
        "chart_budget": chart_budget,
        "cat_labels": cat_labels,
        "cat_values": cat_values,
    })


# ------------------------------------------------------------------
# ADD / DELETE
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
    month_qs = Expense.objects.filter(user=request.user, occurred_at__date__gte=first)
    return render(request, "expenses/_recent.html", {
        "recent": month_qs[:20],
        "total": month_qs.aggregate(s=Sum("amount"))["s"] or 0,
        "by_category": month_qs.values("category").annotate(total=Sum("amount")).order_by("-total"),
    })


# ------------------------------------------------------------------
# BUDGET
# ------------------------------------------------------------------

@login_required
@require_http_methods(["POST"])
def set_budget(request):
    amount_raw = (request.POST.get("amount") or "0").strip()
    try:
        amount = Decimal(amount_raw)
    except Exception:
        messages.error(request, "Budget must be a number.")
        return redirect("expenses:insights")

    obj, _ = MonthlyBudget.objects.get_or_create(user=request.user)
    obj.amount = max(amount, Decimal("0"))
    obj.save()

    if obj.amount == 0:
        messages.success(request, "Budget cleared — comparing to previous periods instead.")
    else:
        messages.success(request, f"Monthly budget set to {obj.amount}.")
    return redirect("expenses:insights")