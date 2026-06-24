# tools/

Standalone helper scripts that are **not** part of the agent/skill fleet taxonomy and are **outside**
`scripts/validate_fleet.py`'s scope (that validator checks the `.claude/` agents + skills only). Treat
anything here as ungoverned examples/utilities, not load-bearing fleet machinery.

CI runs a `py_compile` smoke check over these files (see [`.github/workflows/validate.yml`](../.github/workflows/validate.yml))
so they stay syntactically valid, but they are not behavior-tested and carry no stability guarantee.

## Contents
- **`chaos_game.py`** — an interactive terminal quiz of SRE incident-triage scenarios (PCF/TAS-flavored);
  a learning/onboarding toy. Run `python3 tools/chaos_game.py`. Not wired into any agent or skill; its
  scenarios are illustrative, not authoritative — defer to the skills/runbooks for real triage facts.
