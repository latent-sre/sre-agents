#!/usr/bin/env python3
"""Error-budget & burn-rate calculator for the slo-error-budget skill.

Pure stdlib, cross-platform.

TWO KINDS OF SLI — they are not interchangeable, and this tool will not mix them:

  TIME-based    (--bad-minutes)              "the service was down for N minutes"
      Budget is meaningfully expressed in MINUTES. Use for availability measured by probe/uptime.

  REQUEST-based (--bad-events / --total-events)   "N of M requests failed"
      Budget is a COUNT OF REQUESTS, not minutes. Converting a request-ratio SLO into "minutes of
      downtime" silently assumes uniform traffic, which is false for every real service (a 1%
      failure rate at 3am and at peak are not the same number of minutes). The old version of this
      tool did exactly that. It now refuses to.

BURN RATE requires TWO WINDOWS. Google's multi-window burn-rate thresholds (14.4x / 6x / 1x) are
only valid when a LONG window and a SHORT window both exceed the threshold; the short window is what
stops a brief blip from paging you. A severity verdict from a single window is not a weaker version
of the method — it is a different, wrong method. So --sli-short is REQUIRED for a PAGE/TICKET
verdict; supply one window and you get the arithmetic (burn rate) with no severity label.

Examples:
  # 99.9% over 28d, time-based, 12 minutes of badness so far
  python error_budget.py --slo 99.9 --window-days 28 --bad-minutes 12

  # 99.9% over 28d, request-based: 4,120 bad out of 9,300,000
  python error_budget.py --slo 99.9 --bad-events 4120 --total-events 9300000

  # burn rate + severity: long window (1h) measured 99.2%, short window (5m) measured 98.5%
  python error_budget.py --slo 99.9 --sli-long 99.2 --sli-short 98.5

  # burn rate only, no severity (one window is not enough to page on)
  python error_budget.py --slo 99.9 --sli-long 99.2
"""
import argparse
import math
import sys

# Google SRE workbook multi-window burn-rate thresholds.
# (burn_rate, severity, budget consumed at this rate)
_PAGE_FAST = 14.4   # ~2% of a 30d budget per hour
_PAGE_SLOW = 6.0
_TICKET = 1.0


def fmt_minutes(m: float) -> str:
    if m >= 1440:
        return f"{m/1440:.2f} d ({m:.0f} min)"
    if m >= 60:
        return f"{m/60:.2f} h ({m:.0f} min)"
    return f"{m:.1f} min"


def fmt_count(n: float) -> str:
    return f"{n:,.0f}"


def _finite(p, name, value, *, minimum=None, exclusive_min=None, maximum=None):
    """argparse's float parser happily accepts 'nan' and 'inf'. Reject them, and range-check.

    Every numeric input goes through here. The old version validated --slo and --window-days but not
    --bad-minutes, so `--bad-minutes -50` and `--bad-minutes nan` were accepted and produced
    confident nonsense ('remaining: 90.3 min' from a negative consumption, NaN percentages).
    """
    if value is None:
        return None
    if not math.isfinite(value):
        p.error(f"{name} must be a finite number (got {value!r})")
    if minimum is not None and value < minimum:
        p.error(f"{name} must be >= {minimum} (got {value:g})")
    if exclusive_min is not None and value <= exclusive_min:
        p.error(f"{name} must be > {exclusive_min} (got {value:g})")
    if maximum is not None and value > maximum:
        p.error(f"{name} must be <= {maximum} (got {value:g})")
    return value


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="SLO error-budget & burn-rate calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--slo", type=float, required=True, help="SLO target percent, e.g. 99.9")
    p.add_argument("--window-days", type=float, default=28.0, help="rolling window in days (default 28)")

    status = p.add_argument_group("budget status — pick ONE kind of SLI")
    status.add_argument("--bad-minutes", type=float,
                        help="TIME-based: error minutes consumed this window")
    status.add_argument("--bad-events", type=float,
                        help="REQUEST-based: failed requests this window (needs --total-events)")
    status.add_argument("--total-events", type=float,
                        help="REQUEST-based: total requests this window")

    burn = p.add_argument_group("burn rate — BOTH windows required for a severity verdict")
    burn.add_argument("--sli-long", "--sli", dest="sli_long", type=float,
                      help="availability percent over the LONG window (e.g. 1h)")
    burn.add_argument("--sli-short", type=float,
                      help="availability percent over the SHORT window (e.g. 5m). Required to emit "
                           "PAGE/TICKET — a single window cannot distinguish an outage from a blip.")
    burn.add_argument("--long-window", default="1h", help="label for the long window (default 1h)")
    burn.add_argument("--short-window", default="5m", help="label for the short window (default 5m)")

    args = p.parse_args(argv)

    _finite(p, "--slo", args.slo, exclusive_min=0, maximum=100)
    if args.slo >= 100:
        p.error("--slo must be < 100 (a 100% SLO has a zero error budget)")
    _finite(p, "--window-days", args.window_days, exclusive_min=0)
    _finite(p, "--bad-minutes", args.bad_minutes, minimum=0)
    _finite(p, "--bad-events", args.bad_events, minimum=0)
    _finite(p, "--total-events", args.total_events, exclusive_min=0)
    _finite(p, "--sli-long", args.sli_long, minimum=0, maximum=100)
    _finite(p, "--sli-short", args.sli_short, minimum=0, maximum=100)

    request_mode = args.bad_events is not None or args.total_events is not None
    if request_mode and args.bad_minutes is not None:
        p.error("--bad-minutes (time-based SLI) cannot be combined with --bad-events/--total-events "
                "(request-based SLI). They are different SLIs; pick one.")
    if request_mode and (args.bad_events is None or args.total_events is None):
        p.error("request-based status needs BOTH --bad-events and --total-events")
    if request_mode and args.bad_events > args.total_events:
        p.error("--bad-events cannot exceed --total-events")

    budget_fraction = 1.0 - args.slo / 100.0          # e.g. 99.9 -> 0.001

    print(f"SLO {args.slo}%  ->  error budget = {budget_fraction*100:.4g}% of the SLI")

    # ---- budget status -------------------------------------------------------------------------
    if args.bad_minutes is not None:
        # TIME-based only. Minutes are a valid budget unit here because the SLI itself is time.
        window_minutes = args.window_days * 24 * 60
        budget_minutes = window_minutes * budget_fraction
        remaining = budget_minutes - args.bad_minutes
        pct = args.bad_minutes / budget_minutes * 100
        state = "OVER BUDGET" if remaining < 0 else "ok"
        print(f"  [time-based SLI] over {args.window_days:g}d the budget is {fmt_minutes(budget_minutes)}")
        print(f"  consumed:  {fmt_minutes(args.bad_minutes)}  ({pct:.1f}% of budget)  [{state}]")
        print(f"  remaining: {fmt_minutes(remaining)}")

    if request_mode:
        # REQUEST-based. Budget is a number of REQUESTS. Deliberately NOT converted to minutes:
        # that conversion assumes uniform traffic and is wrong for every real service.
        budget_events = args.total_events * budget_fraction
        remaining = budget_events - args.bad_events
        pct = args.bad_events / budget_events * 100 if budget_events else float("inf")
        state = "OVER BUDGET" if remaining < 0 else "ok"
        observed = (1 - args.bad_events / args.total_events) * 100
        print(f"  [request-based SLI] {fmt_count(args.total_events)} requests  ->  budget = "
              f"{fmt_count(budget_events)} failed requests")
        print(f"  consumed:  {fmt_count(args.bad_events)} bad  ({pct:.1f}% of budget)  [{state}]")
        print(f"  remaining: {fmt_count(remaining)} bad requests")
        print(f"  observed availability: {observed:.4f}%")

    # ---- burn rate -----------------------------------------------------------------------------
    if args.sli_long is not None:
        burn_long = (1.0 - args.sli_long / 100.0) / budget_fraction
        print(f"  burn ({args.long_window}):  SLI {args.sli_long}%  ->  {burn_long:.2f}x")

        if args.sli_short is None:
            # No severity from one window. This is the whole point of multi-window alerting: the
            # short window is what separates a real outage from a blip that already recovered.
            print(f"  severity: NOT EVALUATED — pass --sli-short (the {args.short_window} window) too.")
            print(f"            A single window cannot tell an outage from a blip, and the 14.4x/6x "
                  f"thresholds are only valid multi-window.")
        else:
            burn_short = (1.0 - args.sli_short / 100.0) / budget_fraction
            print(f"  burn ({args.short_window}): SLI {args.sli_short}%  ->  {burn_short:.2f}x")
            both = min(burn_long, burn_short)   # BOTH windows must exceed the threshold
            if both >= _PAGE_FAST:
                sev = f"PAGE (fast burn — both windows >= {_PAGE_FAST}x)"
            elif both >= _PAGE_SLOW:
                sev = f"PAGE (slower burn — both windows >= {_PAGE_SLOW}x)"
            elif both >= _TICKET:
                sev = f"TICKET (slow leak — both windows >= {_TICKET}x)"
            elif burn_long >= _PAGE_SLOW or burn_short >= _PAGE_SLOW:
                sev = ("no alert — only ONE window is burning; the other has recovered "
                       "(this is exactly the blip the short window exists to filter)")
            else:
                sev = "within budget (burn < 1x)"
            print(f"  severity: {sev}")

            if burn_long > 0:
                exhaust = args.window_days / burn_long
                print(f"  at the {args.long_window} rate, the full {args.window_days:g}d budget is "
                      f"gone in {fmt_minutes(exhaust*24*60)}")

    if args.bad_minutes is None and not request_mode and args.sli_long is None:
        print("  (pass --bad-minutes OR --bad-events/--total-events for status; "
              "--sli-long + --sli-short for burn rate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
