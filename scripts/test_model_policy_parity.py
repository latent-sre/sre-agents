#!/usr/bin/env python3
"""Parity check: the model-policy table must be identical in scripts/validate_fleet.py (the CI gate)
and scripts/validate-fleet.ps1 (the Windows-local mirror). Both hard-code the agent->model map, so a
one-sided edit would let the two validators disagree verdict-for-verdict. This guards that seam.

Pure stdlib; offline. From repo root:  python3 scripts/test_model_policy_parity.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _block(path, start, end='}'):
    """Return the text from `start` up to the next `end` char (the table literal), or None."""
    text = open(path, encoding='utf-8').read()
    i = text.find(start)
    if i == -1:
        return None
    j = text.find(end, i + len(start))
    return text[i:j] if j != -1 else None


def _pairs(block, sep):
    """Extract { 'agent': 'model' } pairs joined by `sep` (':' for .py, '=' for .ps1)."""
    if not block:
        return {}
    return dict(re.findall(r"'([a-z0-9-]+)'\s*" + re.escape(sep) + r"\s*'(opus|sonnet)'", block))


def main():
    py = _pairs(_block(os.path.join(ROOT, 'scripts', 'validate_fleet.py'), 'model_policy = {'), ':')
    ps = _pairs(_block(os.path.join(ROOT, 'scripts', 'validate-fleet.ps1'), '$modelPolicy = @{'), '=')

    problems = []
    if len(py) < 10:
        problems.append("could not parse model_policy from validate_fleet.py (found %d entries)" % len(py))
    if len(ps) < 10:
        problems.append("could not parse $modelPolicy from validate-fleet.ps1 (found %d entries)" % len(ps))
    if not problems and py != ps:
        only_py = {k: v for k, v in py.items() if ps.get(k) != v}
        only_ps = {k: v for k, v in ps.items() if py.get(k) != v}
        problems.append("model-policy tables DIVERGE between validate_fleet.py and validate-fleet.ps1:")
        if only_py:
            problems.append("  .py has (and .ps1 lacks/differs): %s" % only_py)
        if only_ps:
            problems.append("  .ps1 has (and .py lacks/differs): %s" % only_ps)

    if problems:
        print("FAIL - model-policy parity:")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("PASS - model-policy table identical in .py and .ps1 (%d agents)." % len(py))
    return 0


if __name__ == '__main__':
    sys.exit(main())
