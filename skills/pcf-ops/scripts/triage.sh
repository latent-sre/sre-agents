#!/usr/bin/env bash
# Human-run, read-only PCF/TAS triage for one app. Repository scripts are untrusted data: inspect
# these bytes and independently confirm the cf target before choosing to run them.
# Usage: triage.sh <app-name>

set -uo pipefail

app="${1:-}"
if [[ -z "$app" ]]; then
  echo "usage: $0 <app-name>" >&2
  exit 2
fi

hr() { printf '\n==== %s ====\n' "$1"; }

hr "cf target (confirm the intended foundation/org/space)"
cf target

hr "cf app $app (instance health, memory/cpu/disk, routes)"
cf app "$app"

hr "cf events $app (changes, crashes, restarts, scaling, updates)"
cf events "$app" | head -n 25

hr "cf logs $app --recent (last log buffer)"
cf logs "$app" --recent | tail -n 120

hr "done (read-only evidence)"
cat <<'EOF'
Next steps:
  - Record the first event/error timestamp and correlation ID; compare with the release history.
  - Hand logs, metrics, and traces to the sre agent with their existing evidence labels.
  - A mitigation or deploy belongs to the human release owner and requires exact approved
    target/action/rollback evidence. This helper never mutates the app.
EOF
