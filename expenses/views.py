# expenses/views.py
from calendar import monthrange
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ExpenseForm
from .models import Expense


@login_required
def expense_list(request):
    """Main view: form + monthly summary + recent list, all on one page."""

    # figure out which month we're looking at (?month=YYYY-MM), default = current
    today = timezone.localdate()
    month_str = request.GET.get("month", today.strftime("%Y-%m"))
    try:
        year, month = map(int, month_str.split("-"))
    except ValueError:
        year, month = today.year, today.month
        month_str = f"{year:04d}-{month:02d}"

    # range for this month — first day to last day
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    # base queryset: user's expenses in this month
    month_qs = Expense.objects.filter(
        user=request.user,
        occurred_at__date__gte=first,
        occurred_at__date__lte=last,
    )

    # total for the month
    total = month_qs.aggregate(s=Sum("amount"))["s"] or 0

    # breakdown per category (only nonzero ones)
    by_category = (
        month_qs.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    # recent 20 entries for the list
    recent = month_qs[:20]

    return render(request, "expenses/list.html", {
        "form": ExpenseForm(),
        "recent": recent,
        "total": total,
        "by_category": by_category,
        "month_str": month_str,
        "month_label": first.strftime("%B %Y"),
    })


@login_required
@require_http_methods(["POST"])
def expense_add(request):
    """Add an expense. Supports HTMX for in-place list refresh."""
    form = ExpenseForm(request.POST)
    if form.is_valid():
        expense = form.save(commit=False)
        expense.user = request.user
        expense.save()
        messages.success(request, "Expense added.")
    else:
        messages.error(request, "Could not save — check the values.")

    if request.headers.get("HX-Request"):
        # Return the fresh list partial so HTMX swaps it in.
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
    """Helper: rebuild the 'recent expenses + totals' partial."""
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