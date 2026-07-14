#!/usr/bin/env python3
"""Gate A -- the mechanical audit. One entrypoint, run by CI and by humans/agents alike.

WHY THIS EXISTS
---------------
The run protocol (spec Section 0) used to *transcribe* the CI steps into prose. That broke the repo's
own anti-rot doctrine -- "never transcribe an artifact that lives in the repo, point at it" -- and it
had already drifted on the day it was written: the transcription silently dropped the dependency
install step, so a cold checkout died with ModuleNotFoundError on the eval graders. Two sources of
truth for "what Gate A is" means they disagree, and the one a human reads is the one that rots.

So there is now exactly one: this file. `.github/workflows/validate.yml` calls it; the protocol points
at it. They cannot drift apart, because there is nothing to keep in sync.

It also settles the interpreter question for good. The repo's docs disagreed about how to invoke Python
on Windows (`python` vs `py -3` vs `python3`, the last being the Microsoft Store stub that once silently
disarmed the read-only guard). Sub-steps here run under `sys.executable` -- whichever interpreter you
started this script with, by construction the right one.

WHAT IT DOES NOT DO
-------------------
Gate A is STRUCTURAL. It proves the fleet is well-formed; it never proves the fleet is right. It passes
green over a skill that leaks the production password into argv. Gates B (content regression) and C
(adversarial review) are the ones that catch that -- see spec Section 0.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (label, argv-after-the-interpreter). Ordered cheapest-and-most-foundational first: a broken validator
# makes every downstream result meaningless, so it fails before we spend time on the eval harness.
STEPS = [
    ("Fleet structure",
     ["scripts/validate_fleet.py"]),
    ("Validator's own tests",
     ["-m", "unittest", "discover", "-s", "scripts", "-p", "test_validate_fleet.py"]),
    ("Format-spike projection contracts",
     ["-m", "unittest", "discover", "-s", "spikes/copilot-claude-format/tests",
      "-p", "test_*.py", "-v"]),
    ("Read-only guard",
     ["scripts/test_readonly_guard.py"]),
    ("Eval graders",
     ["evals/test_graders.py"]),
    ("Discovery probe",
     ["evals/test_discovery_probe.py"]),
    ("Clean-room rig",
     ["evals/test_clean_room.py"]),
    ("Eval suite parses",
     ["evals/run_evals.py", "--validate"]),
]


def preflight():
    """Fail loudly on missing deps, with the PINNED command -- never auto-install.

    The eval graders import yaml and FAIL (not skip) without it. An agent that hits a bare
    ModuleNotFoundError reaches for `pip install pyyaml`, unpinned, which requirements-dev.txt
    explicitly forbids. Hand it the right command instead of letting it invent a wrong one.
    """
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("Gate A: FAIL -- eval-harness dependencies are not installed.\n"
              "  The graders import yaml and fail (not skip) without it.\n"
              "  Install the PINNED set (do not `pip install pyyaml` bare):\n\n"
              "    %s -m pip install -r requirements-dev.txt\n" % sys.executable,
              file=sys.stderr)
        return False
    return True


def main():
    if not preflight():
        return 1

    failed = []
    for label, argv in STEPS:
        print("\n=== %s ===" % label, flush=True)
        # Run every step even after one fails: an agent fixing the fleet wants the whole list of what
        # is broken, not a bisect through one failure at a time.
        rc = subprocess.call([sys.executable] + argv, cwd=ROOT)
        if rc != 0:
            failed.append(label)

    print("\n" + "-" * 60)
    if failed:
        print("Gate A: FAIL -- %d of %d step(s) failed:" % (len(failed), len(STEPS)))
        for label in failed:
            print("  - %s" % label)
        print("\nGate A is structural only. Passing it would still not clear Gates B/C (spec Section 0).")
        return 1

    print("Gate A: PASS -- %d/%d structural steps green." % (len(STEPS), len(STEPS)))
    print("This proves the fleet is WELL-FORMED, not that it is CORRECT.")
    print("Gates B (content regression) and C (adversarial review) are still owed. Spec Section 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
