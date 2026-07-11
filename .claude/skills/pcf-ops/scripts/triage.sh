#!/usr/bin/env bash
# Read-only PCF / TAS triage for ONE app. Runs only safe `cf` read commands and prints a
# structured summary — never changes state. Part of the pcf-ops skill.
#
# Usage:   triage.sh <app-name>
# Needs:   cf CLI v8, and you are already `cf login`'d and targeted at the right org/space
#          (run `cf target` to confirm BEFORE you trust the output).
#
# Note: intentionally NOT `set -e` — if one command fails we still want the rest of the picture.
set -uo pipefail

app="${1:-}"
if [[ -z "$app" ]]; then
  echo "usage: $0 <app-name>" >&2
  exit 2
fi

hr() { printf '\n==== %s ====\n' "$1"; }

hr "cf target (CONFIRM this is the intended foundation/org/space)"
cf target

hr "cf app $app  (instance health, memory/cpu/disk, routes)"
cf app "$app"

hr "cf events $app  (what changed? crashes, restarts, scaling, updates — newest first)"
cf events "$app" | head -n 25

hr "cf logs $app --recent  (last log buffer; look for stack traces / OOM / 5xx)"
cf logs "$app" --recent | tail -n 120

hr "done (read-only)"
cat <<'EOF'
Next steps:
  - Correlate the first event/error timestamp with your last deploy (release pipeline / git log).
  - Logs older than the buffer -> splunk-triage (SPL). Metrics over time -> wavefront-queries (ts()).
  - To MITIGATE (restart/scale/rollback/route remap) hand off to a human release owner — see
    rollback-mitigation and clear the production-change-gate. Do not mutate from here.
EOF
