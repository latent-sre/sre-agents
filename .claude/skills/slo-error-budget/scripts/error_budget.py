#!/usr/bin/env python3
"""Error-budget & burn-rate calculator for the slo-error-budget skill.

Pure stdlib, cross-platform. Two complementary views:

  status mode  (--bad-minutes): how much budget is left this window
  burn   mode  (--sli):         how fast you're burning right now + severity

Examples:
  # 99.9% over 28 days, 12 minutes of badness so far this window
  python error_budget.py --slo 99.9 --window-days 28 --bad-minutes 12

  # 99.9% target; the last hour measured 99.2% availability -> burn rate + severity
  python error_budget.py --slo 99.9 --sli 99.2

  # both at once
  python error_budget.py --slo 99.9 --window-days 28 --bad-minutes 12 --sli 99.2
"""
import argparse
import sys


def fmt_minutes(m: float) -> str:
    if m >= 1440:
        return f"{m/1440:.2f} d ({m:.0f} min)"
    if m >= 60:
        return f"{m/60:.2f} h ({m:.0f} min)"
    return f"{m:.1f} min"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SLO error-budget & burn-rate calculator")
    p.add_argument("--slo", type=float, required=True, help="SLO target percent, e.g. 99.9")
    p.add_argument("--window-days", type=float, default=28.0, help="rolling window in days (default 28)")
    p.add_argument("--bad-minutes", type=float, help="error minutes consumed so far this window (status mode)")
    p.add_argument("--sli", type=float, help="recently-measured availability percent (burn mode), e.g. 99.2")
    args = p.parse_args(argv)

    if not (0 < args.slo < 100):
        p.error("--slo must be between 0 and 100 (exclusive)")
    if args.window_days <= 0:
        p.error("--window-days must be positive")
    budget_fraction = 1.0 - args.slo / 100.0          # e.g. 99.9 -> 0.001
    window_minutes = args.window_days * 24 * 60
    budget_minutes = window_minutes * budget_fraction

    print(f"SLO {args.slo}%  over {args.window_days:g}d  ->  error budget = "
          f"{budget_fraction*100:.4g}% = {fmt_minutes(budget_minutes)}")

    if args.bad_minutes is not None:
        consumed = args.bad_minutes
        remaining = budget_minutes - consumed
        pct = (consumed / budget_minutes * 100) if budget_minutes else float("inf")
        state = "OVER BUDGET" if remaining < 0 else "ok"
        print(f"  consumed:  {fmt_minutes(consumed)}  ({pct:.1f}% of budget)  [{state}]")
        print(f"  remaining: {fmt_minutes(remaining)}")

    if args.sli is not None:
        if not (0 <= args.sli <= 100):
            p.error("--sli must be between 0 and 100")
        observed_error = 1.0 - args.sli / 100.0
        burn = observed_error / budget_fraction if budget_fraction else float("inf")
        # Multi-window burn-rate severity (Google SRE workbook thresholds)
        if burn >= 14.4:
            sev = "PAGE (fast burn ~2% of budget/hr)"
        elif burn >= 6:
            sev = "PAGE (slower burn)"
        elif burn >= 1:
            sev = "TICKET (slow leak)"
        else:
            sev = "within budget (burn < 1x)"
        print(f"  measured SLI {args.sli}%  ->  burn rate = {burn:.2f}x  [{sev}]")
        if burn > 0:
            exhaust_days = args.window_days / burn
            print(f"  at this rate the FULL window budget is gone in {fmt_minutes(exhaust_days*24*60)}")

    if args.bad_minutes is None and args.sli is None:
        print("  (pass --bad-minutes for budget status and/or --sli for burn rate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
