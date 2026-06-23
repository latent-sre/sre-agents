#!/usr/bin/env python3
"""Offline test for production-change-guard.py — the prod-executor speed-bump.

Runs the real guard as a subprocess with the exact JSON shape Claude Code pipes on stdin
(PreToolUse contract: exit 0 to allow, exit 2 + stderr to block). Pure stdlib; no network,
no Claude Code needed:

    python scripts/test_production_change_guard.py   # exits 0 on pass, 1 on any failure

Covers: state-changing `cf` commands are BLOCKED without clearance; the same commands are
ALLOWED once a human clears the gate (PCF_GATE_CLEARED=1 or a .gate-cleared sentinel);
read-only `cf` commands (app/apps/logs/events/target, cf curl GET) always pass.
"""
import json
import os
import subprocess
import sys
import tempfile

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production-change-guard.py")

# State-changing cf commands — BLOCKED unless the gate is cleared.
CF_WRITES = [
    "cf push checkout -f manifest.yml",
    "cf delete checkout -f",
    "cf scale checkout -i 5",
    "cf restart checkout",
    "cf restage checkout",
    "cf stop checkout",
    "cf start checkout",
    "cf set-env checkout KEY value",
    "cf map-route checkout apps.example.com --hostname checkout",
    "cf unmap-route checkout apps.example.com --hostname checkout",
    "cf rollback checkout --version 3",
    "cf cancel-deployment checkout",
    "cf continue-deployment checkout",
    "cf ssh checkout -i 0",
    "cf delete-app checkout",
    "cf curl /v3/apps -X POST -d '{}'",
    "cf curl /v3/apps --request PATCH --data '{}'",
    "cf curl /v3/apps --request=DELETE",
]

# Read-only cf commands — must ALWAYS pass, gate cleared or not.
CF_READS = [
    "cf app checkout",
    "cf apps",
    "cf logs checkout --recent",
    "cf logs checkout --recent | tail -n 120",
    "cf events checkout",
    "cf target",
    "cf curl /v3/apps/abc",                 # GET via cf curl
    "cf curl /v3/apps --request GET",
]

# Non-cf commands are out of this guard's narrow scope — must pass (the gate + creds cover them).
NON_CF = [
    "git log --oneline -20",
    "ls -la",
    "echo deploying",
]


def run(command: str, env_extra=None, cwd=None) -> int:
    """Run the guard for a command; return its exit code."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = dict(os.environ)
    # Ensure no ambient clearance leaks in from the test runner's environment.
    env.pop("PCF_GATE_CLEARED", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, GUARD], input=payload, capture_output=True, text=True,
        env=env, cwd=cwd,
    ).returncode


def main() -> int:
    failures = []

    # 1. cf writes BLOCKED (exit 2) without any clearance.
    for cmd in CF_WRITES:
        if run(cmd) != 2:
            failures.append(f"  SHOULD BLOCK (no clearance): {cmd!r}")

    # 2. cf writes ALLOWED (exit 0) with PCF_GATE_CLEARED=1.
    for cmd in CF_WRITES:
        if run(cmd, env_extra={"PCF_GATE_CLEARED": "1"}) != 0:
            failures.append(f"  SHOULD ALLOW (PCF_GATE_CLEARED=1): {cmd!r}")

    # 3. cf writes ALLOWED with a .gate-cleared sentinel file in cwd.
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, ".gate-cleared"), "w").close()
        for cmd in CF_WRITES:
            if run(cmd, cwd=d) != 0:
                failures.append(f"  SHOULD ALLOW (.gate-cleared sentinel): {cmd!r}")

    # 4. Read-only cf commands ALWAYS pass — cleared or not.
    for cmd in CF_READS:
        if run(cmd) != 0:
            failures.append(f"  SHOULD ALLOW (read-only cf, no clearance): {cmd!r}")
        if run(cmd, env_extra={"PCF_GATE_CLEARED": "1"}) != 0:
            failures.append(f"  SHOULD ALLOW (read-only cf, cleared): {cmd!r}")

    # 5. Non-cf commands pass (out of scope for this guard).
    for cmd in NON_CF:
        if run(cmd) != 0:
            failures.append(f"  SHOULD ALLOW (non-cf, out of scope): {cmd!r}")

    # 6. A non-Bash tool call is never blocked.
    other = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}})
    env = dict(os.environ); env.pop("PCF_GATE_CLEARED", None)
    if subprocess.run([sys.executable, GUARD], input=other, capture_output=True, text=True, env=env).returncode != 0:
        failures.append("  guard blocked a non-Bash tool call (should stay silent)")

    total = (len(CF_WRITES) * 3) + (len(CF_READS) * 2) + len(NON_CF) + 1
    if failures:
        print(f"FAIL — {len(failures)} case(s) wrong (of {total}):")
        print("\n".join(failures))
        return 1
    print(f"PASS — {total} cases "
          f"({len(CF_WRITES)} writes x3 modes, {len(CF_READS)} reads x2, "
          f"{len(NON_CF)} non-cf, 1 non-Bash).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
