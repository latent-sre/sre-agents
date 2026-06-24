#!/usr/bin/env python3
"""chaos_game.py — a tiny SRE incident quiz for the PCF/Splunk/Wavefront stack.

Pick a random incident, answer a few multiple-choice questions, get a score
and a (slightly cheeky) on-call readiness rating. Pure stdlib, cross-platform.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass


# ---- color: ANSI with a Windows-safe fallback ---------------------------------

def _enable_ansi_on_windows() -> bool:
    """Try to enable VT processing on modern Windows terminals."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # 7 = STD_OUTPUT_HANDLE; 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


# Make sure non-ASCII (em-dashes etc.) prints cleanly on Windows cp1252 consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

_USE_COLOR = sys.stdout.isatty() and _enable_ansi_on_windows() and os.environ.get("NO_COLOR") is None


def c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(s: str) -> str:    return c(s, "1")
def dim(s: str) -> str:     return c(s, "2")
def red(s: str) -> str:     return c(s, "31")
def green(s: str) -> str:   return c(s, "32")
def yellow(s: str) -> str:  return c(s, "33")
def blue(s: str) -> str:    return c(s, "34")
def magenta(s: str) -> str: return c(s, "35")
def cyan(s: str) -> str:    return c(s, "36")


# ---- scenario data ------------------------------------------------------------

@dataclass
class Question:
    prompt: str
    options: list[str]
    correct: int  # 0-based index
    why: str


@dataclass
class Scenario:
    title: str
    severity: str          # the "true" SEV — used in feedback
    symptoms: list[str]
    signals: dict[str, str]  # golden signals: latency / traffic / errors / saturation
    questions: list[Question]


SCENARIOS: list[Scenario] = [
    Scenario(
        title="5xx spike on payment-service immediately after a deploy",
        severity="SEV2",
        symptoms=[
            "Error rate jumped from 0.1% to 12% within 90s of `cf push`",
            "Affects checkout flow; revenue-impacting but not total outage",
            "Previous build (v412) was healthy; current is v413",
        ],
        signals={
            "latency": "p99 stable ~220ms",
            "traffic": "normal",
            "errors": "12% 5xx (was 0.1%)",
            "saturation": "CPU/mem normal",
        },
        questions=[
            Question(
                "What's the right SEV?",
                ["SEV1 — total outage", "SEV2 — major degradation", "SEV3 — minor", "SEV4 — cosmetic"],
                1,
                "Revenue-impacting partial failure with a clear blast radius is classic SEV2. SEV1 is reserved for full outage / data loss.",
            ),
            Question(
                "First action?",
                [
                    "Open Splunk and read every error",
                    "Roll back to v412 via `cf` (mitigate first, RCA after)",
                    "Page the database team",
                    "Restart all instances",
                ],
                1,
                "Post-deploy regression with a known-good prior build = rollback first, investigate after. Mitigation beats curiosity.",
            ),
            Question(
                "Which signal do you pull up to confirm the deploy correlation?",
                ["ThousandEyes path trace", "`cf events payment-service`", "Grafana node CPU", "Moogsoft topology"],
                1,
                "`cf events` shows the push timestamp; align it against the error-rate jump in Wavefront. That's your 'what changed' in 5 seconds.",
            ),
        ],
    ),
    Scenario(
        title="OOM restarts on 3 of 4 instances of orders-api",
        severity="SEV2",
        symptoms=[
            "`cf app` shows memory ~100% and `cf logs --recent` shows 'Exited with status 137' on 3 of 4 instances; `cf events` shows the crash/restart events (not an 'out of memory' reason string)",
            "Memory grew steadily over 6 hours — looks like a leak, not a spike",
            "No recent deploy",
        ],
        signals={
            "latency": "elevated during restarts",
            "traffic": "normal",
            "errors": "503s during restart windows",
            "saturation": "memory at 100% before each crash",
        },
        questions=[
            Question(
                "What's the right SEV?",
                ["SEV1", "SEV2", "SEV3", "SEV4"],
                1,
                "Repeated crashes affecting most instances of a customer-facing app = SEV2. Not full outage (one instance still up) but clearly major.",
            ),
            Question(
                "First action?",
                [
                    "`cf scale -m 2G` to buy time, then hunt the leak",
                    "Roll back (no deploy to roll back to)",
                    "Delete the app and re-push",
                    "File a ticket and go to lunch",
                ],
                0,
                "Bumping memory is a legitimate stop-the-bleed for a leak with no recent deploy. It's a band-aid — file the leak hunt as the follow-up.",
            ),
            Question(
                "Which tool do you reach for first to find the leak pattern?",
                ["ThousandEyes", "Wavefront memory time series + Splunk for GC/heap logs", "Grafana node disk I/O", "`cf ssh` and `top`"],
                1,
                "Memory growth shape over hours lives in Wavefront; correlate with app-level GC/heap log lines in Splunk. `cf ssh` is fine but slower and only shows now.",
            ),
        ],
    ),
    Scenario(
        title="p99 latency on search-api jumped from 200ms to 4s",
        severity="SEV2",
        symptoms=[
            "p50 unchanged at 80ms; only p99 is bad",
            "Error rate flat",
            "Started 20 minutes ago, no deploy in 48h",
        ],
        signals={
            "latency": "p99 4s (was 200ms), p50 normal",
            "traffic": "normal",
            "errors": "0.05% (normal)",
            "saturation": "app CPU normal; downstream DB CPU at 95%",
        },
        questions=[
            Question(
                "What's the right SEV?",
                ["SEV1", "SEV2", "SEV3", "SEV4"],
                1,
                "Tail latency at 20x baseline is user-visible degradation for a meaningful slice of traffic. SEV2.",
            ),
            Question(
                "First action?",
                [
                    "Roll back search-api",
                    "Investigate the downstream DB — saturation signal points there",
                    "Restart all search-api instances",
                    "Clear the CDN cache",
                ],
                1,
                "p50 normal + p99 bad + downstream DB at 95% CPU = the symptom is in your app but the cause is downstream. Don't roll back something that didn't change.",
            ),
            Question(
                "Which signal confirms it's the DB, not the network?",
                ["ThousandEyes test from edge", "Wavefront DB query latency + connection pool wait", "Grafana host uptime", "`cf logs --recent`"],
                1,
                "DB-side query latency and pool-wait time isolate compute-bound DB from network. ThousandEyes would only help if you suspected the path itself.",
            ),
        ],
    ),
    Scenario(
        title="Dependency timeout: auth-service can't reach the user-db",
        severity="SEV1",
        symptoms=[
            "100% of login attempts failing with connection timeout",
            "Started 4 minutes ago, sudden cliff",
            "auth-service itself is healthy; the DB endpoint is unreachable",
        ],
        signals={
            "latency": "infinite (timeouts)",
            "traffic": "normal inbound",
            "errors": "100% on login path",
            "saturation": "auth-service idle (waiting on socket)",
        },
        questions=[
            Question(
                "What's the right SEV?",
                ["SEV1 — total auth outage", "SEV2", "SEV3", "SEV4"],
                0,
                "No one can log in. That's a full user-facing outage on a critical path = SEV1, page the on-call, start the bridge.",
            ),
            Question(
                "First action?",
                [
                    "Open the incident bridge and page on-call; start parallel triage",
                    "Read Splunk for an hour to be sure",
                    "Roll back auth-service",
                    "Email the DB team and wait for reply",
                ],
                0,
                "SEV1 = process first. Bridge + page + comms in parallel with triage. Don't serialize a SEV1 behind log reading.",
            ),
            Question(
                "Which tool tells you fastest if it's a network path issue vs DB down?",
                ["ThousandEyes (path + reachability)", "Grafana app dashboards", "`cf logs auth-service`", "Moogsoft alone"],
                0,
                "ThousandEyes shows path/reachability between foundations and dependencies — exactly the question 'is the network the problem'.",
            ),
        ],
    ),
    Scenario(
        title="Certificate for api.example.com expires in 6 hours",
        severity="SEV3",
        symptoms=[
            "Wavefront alert: cert TTL < 24h",
            "Nothing is broken yet",
            "Cert is on the public ingress route",
        ],
        signals={
            "latency": "normal",
            "traffic": "normal",
            "errors": "none",
            "saturation": "normal",
        },
        questions=[
            Question(
                "What's the right SEV right now?",
                ["SEV1", "SEV2", "SEV3 — imminent risk, no impact yet", "SEV4"],
                2,
                "No customer impact yet, but the clock is the problem. SEV3 with a hard deadline. If you blow past the deadline, it becomes SEV1.",
            ),
            Question(
                "First action?",
                [
                    "Rotate the cert now via the documented runbook",
                    "Wait for it to actually expire and then panic",
                    "Roll back the app",
                    "Open a SEV1 bridge",
                ],
                0,
                "Pre-impact mitigations have runbooks for a reason. Rotate calmly inside the window.",
            ),
            Question(
                "Which signal do you watch right after rotation to verify?",
                ["ThousandEyes TLS handshake test + Splunk TLS handshake errors", "Grafana host CPU", "`cf events`", "Moogsoft topology graph"],
                0,
                "TLS handshake success from outside (ThousandEyes) plus handshake error logs (Splunk) is the closed-loop check that the new cert is actually serving.",
            ),
        ],
    ),
    Scenario(
        title="Many apps on one foundation suddenly throwing 503s",
        severity="SEV1",
        symptoms=[
            "12 unrelated apps all reporting 5xx in the same 60s window",
            "Your app's `cf app` shows healthy instances",
            "Moogsoft has correlated 30+ alerts to one cluster",
        ],
        signals={
            "latency": "elevated across the foundation",
            "traffic": "normal",
            "errors": "5xx across many apps",
            "saturation": "your app: normal",
        },
        questions=[
            Question(
                "What's the right SEV?",
                ["SEV1 — platform-wide", "SEV2", "SEV3", "SEV4"],
                0,
                "Multi-app simultaneous failure with your app healthy = platform-side event. SEV1 from the user's perspective.",
            ),
            Question(
                "First action?",
                [
                    "Roll back your app — surely it's you",
                    "Escalate to the platform team with evidence (timestamps, blast radius, `cf app` showing your app healthy)",
                    "Restart all your instances",
                    "Open a Splunk dashboard and stare",
                ],
                1,
                "This is the platform boundary. Your job is recognize-and-escalate-with-evidence, not operate BOSH/Diego/Gorouter yourself.",
            ),
            Question(
                "What evidence package do you hand the platform team?",
                [
                    "Just a Slack message saying 'something is broken'",
                    "Timestamps + blast-radius list + Moogsoft correlation + `cf app`/`cf events` showing your app healthy",
                    "A screenshot of one error",
                    "Your opinion",
                ],
                1,
                "Evidence over assertion. The handoff lands fast when it's structured: when, who's affected, what you've ruled out.",
            ),
        ],
    ),
]


# ---- game loop ----------------------------------------------------------------

BANNER = r"""
   ___ _                       ___
  / __\ |__   __ _  ___  ___  / _ \__ _ _ __ ___   ___
 / /  | '_ \ / _` |/ _ \/ __|/ /_\/ _` | '_ ` _ \ / _ \
/ /___| | | | (_| | (_) \__ \ /_\\ (_| | | | | | |  __/
\____/|_| |_|\__,_|\___/|___/\____/\__,_|_| |_| |_|\___|
        SRE incident quiz — PCF / Splunk / Wavefront
"""


def ask_question(q: Question, qnum: int) -> bool:
    print(bold(f"\nQ{qnum}. {q.prompt}"))
    for i, opt in enumerate(q.options):
        print(f"  {cyan(str(i + 1))}) {opt}")
    while True:
        raw = input(dim("your answer [1-{}] (or q to quit): ".format(len(q.options)))).strip().lower()
        if raw in ("q", "quit", "exit"):
            print(yellow("\nbailing out — see you on the bridge."))
            sys.exit(0)
        if raw.isdigit() and 1 <= int(raw) <= len(q.options):
            choice = int(raw) - 1
            break
        print(red("  please enter a number from the list."))

    correct = choice == q.correct
    if correct:
        print(green("  correct!  ") + dim(q.why))
    else:
        right = q.options[q.correct]
        print(red("  not quite.  ") + bold(f"answer: {right}"))
        print(dim("  " + q.why))
    return correct


def rate(score: int, total: int) -> str:
    pct = score / total
    if pct == 1.0:
        return green("Senior SRE material — buy yourself a coffee.")
    if pct >= 0.75:
        return green("On-call ready. Solid instincts.")
    if pct >= 0.5:
        return yellow("Getting there. Re-read the runbooks before next rotation.")
    if pct > 0:
        return yellow("Need more runbook practice. Pair with a senior on the next incident.")
    return red("Step away from the bridge. Today is a learning day.")


def play_one() -> tuple[int, int]:
    s = random.choice(SCENARIOS)
    print(magenta("\n" + "=" * 64))
    print(bold("INCIDENT: ") + s.title)
    print(magenta("=" * 64))
    print(bold("symptoms:"))
    for sym in s.symptoms:
        print(f"  - {sym}")
    print(bold("\ngolden signals:"))
    for k, v in s.signals.items():
        print(f"  {cyan(k):<22} {v}")

    score = 0
    for i, q in enumerate(s.questions, start=1):
        if ask_question(q, i):
            score += 1
    total = len(s.questions)
    print(bold(f"\nscenario score: {score}/{total}"))
    return score, total


def main() -> None:
    print(cyan(BANNER))
    print(dim("answer the questions; press q at any prompt to quit.\n"))
    total_score = 0
    total_q = 0
    while True:
        s, t = play_one()
        total_score += s
        total_q += t
        print(bold(f"\nrunning total: {total_score}/{total_q}  —  {rate(total_score, total_q)}"))
        again = input(dim("\nanother scenario? [Y/n/q]: ")).strip().lower()
        if again in ("n", "no", "q", "quit", "exit"):
            break
    print(bold("\nfinal: ") + f"{total_score}/{total_q}  —  {rate(total_score, total_q)}")
    print(dim("stay blameless out there.\n"))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print(yellow("\ninterrupted — see you on the bridge."))
        sys.exit(130)
