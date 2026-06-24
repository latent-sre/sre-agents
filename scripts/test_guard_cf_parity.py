#!/usr/bin/env python3
"""Parity gate: the cf-write denylist must stay identical across the two guards.

scripts/readonly-guard.py and scripts/production-change-guard.py each carry the SAME
cf-write verb alternation, kept in sync today only by a comment
(production-change-guard.py: "Kept deliberately aligned"). If one guard later gains a
mutating `cf` verb the other misses, a state-changing command could slip the prod
speed-bump from an un-cleared session while CI stays green. This test fails the moment
the two cf-write classifications drift apart — the same kind of drift gate the Copilot
.agent.md wrappers already have.

    python scripts/test_guard_cf_parity.py   # exits 0 on pass, 1 on drift

Pure stdlib; imports the two guard modules directly (their main() is __main__-guarded,
so import is side-effect-free).
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _readonly_cf_write_pattern(ro):
    """The cf-write verb rule is the _DENY_PATTERNS element classifying `cf <write-verb>`."""
    cands = [p for p in ro._DENY_PATTERNS if p.startswith(r"\bcf\s+(?:v3-)?(push")]
    if len(cands) != 1:
        raise AssertionError(
            "expected exactly one cf-write verb pattern in readonly-guard _DENY_PATTERNS, "
            "found %d -- update this test if the pattern was refactored." % len(cands)
        )
    return cands[0]


def main():
    ro = _load("readonly_guard", "readonly-guard.py")
    pc = _load("production_change_guard", "production-change-guard.py")

    failures = []

    # 1) The verb alternation must be byte-identical (the high-risk shared string).
    ro_cf = _readonly_cf_write_pattern(ro)
    pc_cf = pc._CF_WRITE.pattern
    if ro_cf != pc_cf:
        failures.append(
            "cf-write verb alternation DRIFTED between guards:\n"
            "  readonly-guard.py:          %s\n"
            "  production-change-guard.py: %s" % (ro_cf, pc_cf)
        )

    # 2) Behavioral cross-check: every sampled cf write the prod guard treats as a state change
    #    must also be denied by the readonly guard (catches a refactor that keeps strings equal
    #    by luck but diverges in behavior, and covers the cf-curl-write path the two files express
    #    differently). A write the readonly guard misses but the prod guard catches (or vice versa)
    #    is exactly the asymmetric exposure this gate exists to prevent.
    SAMPLE = [
        "cf push checkout",
        "cf delete checkout -f",
        "cf scale checkout -i 5",
        "cf restart checkout",
        "cf restage checkout",
        "cf set-env checkout KEY value",
        "cf map-route checkout apps.example.com",
        "cf unmap-route checkout apps.example.com",
        "cf rollback checkout --version 3",
        "cf cancel-deployment checkout",
        "cf v3-push checkout",
        "cf delete-app checkout",
        "cf enable-feature-flag diego_docker",
        "cf curl /v3/apps -X POST -d '{}'",
        "cf curl /v3/apps --request PATCH --data '{}'",
    ]
    for cmd in SAMPLE:
        ro_blocks = ro._DENY_RE.search(cmd) is not None
        pc_blocks = pc._is_cf_write(cmd)
        if ro_blocks != pc_blocks:
            failures.append(
                "guards DISAGREE on %r: readonly_blocks=%s prod_is_write=%s"
                % (cmd, ro_blocks, pc_blocks)
            )

    if failures:
        print("FAIL: guard cf-write parity\n" + "\n".join(failures), file=sys.stderr)
        sys.exit(1)
    print(
        "OK: cf-write denylist in parity across both guards "
        "(verb alternation identical; %d sampled writes agree)." % len(SAMPLE)
    )


if __name__ == "__main__":
    main()
