#!/usr/bin/env python3
"""Offline test for readonly-guard.py — the PreToolUse guard that enforces read-only agents.

Runs the real guard as a subprocess with the exact JSON shape Claude Code pipes on stdin,
and asserts each command is DENIED or ALLOWED. Pure stdlib; no network, no Claude Code needed:

    python scripts/test_readonly_guard.py      # exits 0 on pass, 1 on any failure
"""
import json
import os
import subprocess
import sys

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "readonly-guard.py")

# Commands a read-only agent legitimately runs for observation — must PASS THROUGH.
ALLOW = [
    "cf target",
    "cf app checkout",
    "cf events checkout",
    "cf logs checkout --recent",
    "cf logs checkout --recent | tail -n 120",
    "cf curl /v3/apps/abc",                 # GET via cf curl
    "git log --oneline -20",
    "git diff main...HEAD",
    "git status",
    "git show HEAD:manifest.yml",
    "grep -rn 'ERROR' .",
    "cat manifest.yml",
    "curl -s https://example.com/health",
    "curl -sS https://example.com/health 2>&1",
    "echo hello > /dev/null",
    "ps aux | grep java",
    "ls -la",
    "dig example.com",
]

# Commands that CHANGE STATE — must be DENIED.
DENY = [
    "cf push checkout -f manifest.yml",
    "cf delete checkout -f",
    "cf scale checkout -i 5",
    "cf restart checkout",
    "cf restage checkout",
    "cf set-env checkout KEY value",
    "cf map-route checkout apps.example.com --hostname checkout",
    "cf rollback checkout --version 3",
    "cf curl /v3/apps -X POST -d '{}'",
    "git push origin main",
    "git commit -m 'x'",
    "git reset --hard origin/main",
    "git checkout main",
    "git switch feature",
    "git add .",
    "git stash",
    "git pull",
    "rm -rf build/",
    "mv a b",
    "cp secrets.env /tmp/x",
    "chmod +x deploy.sh",
    "kill -9 1234",
    "systemctl restart nginx",
    "sudo reboot",
    "pip install requests",
    "npm install",
    "apt-get install -y curl",
    "curl -X POST https://example.com/api -d 'x=1'",
    "curl --data @payload.json https://example.com/api",
    "echo 'boom' > /etc/hosts",
    "echo 'log' >> app.log",
    "cf logs checkout --recent > capture.txt",
    "sed -i 's/foo/bar/g' config.yml",
    "perl -pi -e 's/a/b/' file",
    "some_command | tee out.txt",
]


def decision(command: str) -> str:
    """Return 'deny' if the guard denies the command, else 'allow'."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run(
        [sys.executable, GUARD], input=payload, capture_output=True, text=True
    ).stdout
    if out.strip():
        try:
            d = json.loads(out)
            if d.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
                return "deny"
        except json.JSONDecodeError:
            pass
    return "allow"


def main() -> int:
    failures = []
    for cmd in ALLOW:
        if decision(cmd) != "allow":
            failures.append(f"  FALSE POSITIVE (should ALLOW, was denied): {cmd!r}")
    for cmd in DENY:
        if decision(cmd) != "deny":
            failures.append(f"  FALSE NEGATIVE (should DENY, slipped through): {cmd!r}")

    # A non-Bash tool call must never be denied by this guard.
    other = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}})
    if subprocess.run([sys.executable, GUARD], input=other, capture_output=True, text=True).stdout.strip():
        failures.append("  guard emitted a decision for a non-Bash tool (should stay silent)")

    total = len(ALLOW) + len(DENY) + 1
    if failures:
        print(f"FAIL — {len(failures)}/{total} case(s) wrong:")
        print("\n".join(failures))
        return 1
    print(f"PASS — {total} cases ({len(ALLOW)} allow, {len(DENY)} deny, 1 non-Bash).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
