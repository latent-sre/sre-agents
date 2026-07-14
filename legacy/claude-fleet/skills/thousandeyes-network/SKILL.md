---
name: thousandeyes-network
description: >-
  Using Cisco ThousandEyes to answer "is it the network, DNS, routing, or the app?" — test types,
  Cloud vs Enterprise agents, path visualization and BGP route monitoring, and reading synthetic/web
  results. Use during triage when the symptom looks external (reachability, latency from a region, DNS,
  a flaky dependency) or to design synthetic monitoring of a critical path.
---

# Cisco ThousandEyes — network & synthetic checks

ThousandEyes runs scheduled tests from **agents** and shows hop-by-hop network, routing, DNS, and
application-layer results. Use it to separate **network/path** problems from **app** problems.

## Agents
- **Cloud Agents** — Cisco-hosted, public vantage points (test from "the internet").
- **Enterprise Agents** — installed on **our** on-prem network / data centers; test the inside path
  (us → dependency) and source agent-to-agent tests. These matter most for our on-prem + PCF apps.

## Test types (pick by question)
| Question | Test type |
|---|---|
| Can users/agents reach the service, and how's loss/latency/jitter? | **Network: agent-to-server** |
| What's the path/latency between two of our sites/agents? | **Network: agent-to-agent** |
| Is it a routing problem? AS-path change, reachability, BGP update? | **Routing (BGP)** + **Path Visualization** |
| Is DNS resolving correctly and fast? | **DNS server** / **DNS trace** |
| Does the page/endpoint actually work end-to-end? | **Web: HTTP server / page load / transaction** |
| Is a specific API contract/latency holding? | **API test** |

## Reading results during an incident
1. **Path Visualization** — hop-by-hop loss/latency. Loss starting at a specific hop/AS points at the
   network, not your app. If the path is clean to your app, the problem is likely in the app (back to
   `pcf-ops`/`splunk-triage`).
2. **BGP route visualization** — an AS-path change or withdrawn prefix near incident start =
   routing/provider issue; escalate to network/provider, not a code fix.
3. **Cloud vs Enterprise comparison** — fails from Cloud (outside) but fine from Enterprise (inside) →
   ingress/edge/DNS; fine outside but failing inside → internal path/dependency.
4. **Web/transaction** — confirms real user-facing impact and which step breaks.

## Designing checks (with `sre-monitor`)
- Add a transaction/HTTP test for each **critical user journey** and a network test to each **key
  dependency**; alert on loss/latency/availability and link a runbook.
- The current REST API can script tests/alerts (confirm the version against ThousandEyes docs before
  relying on it — `[unverified]`); hand automation to a human release owner/`sde-engineer`.

## Concrete values
Our enterprise agents, test inventory, critical-journey coverage, and BGP monitors live in
`references/tests.md` (fill in; loaded on demand, no credentials).

## Tip
It tells you **where** (network vs app vs DNS vs routing), rarely the code-level **why** — use it to
route the investigation, then confirm cause on the indicated layer.

## A path difference is not a cause
Path Visualization will *always* show you differences — routes change constantly, and a diff between a
healthy and an unhealthy run is the **normal** state of the internet, not evidence. The trap is
reading "the path changed **and** the app broke" as "the path change **broke** the app".

Before you attribute an incident to the network, clear the same bar as any other correlation
(`moogsoft-correlation` states it in full):
- **Mechanism** — name the hop and the effect: *loss/latency at this hop, of this magnitude, is enough
  to breach this timeout*. A different-looking path with **no loss, no latency change, and no
  reachability change** is a different path, not an outage.
- **Corroboration** — the app's own signals agree (5xx/timeouts to *that* dependency in Splunk, latency
  to *that* hop in Wavefront), not just the synthetic.
- **Disconfirmation** — do healthy agents on the **same** path also fail? Do failing agents on a
  **different** path also fail? If the failure doesn't track the path, the path isn't the cause.
- **Blast radius** — one agent/region vs all. A single vantage point failing is far more often that
  vantage point.

If it clears the bar, escalate to the network/platform team **with the evidence** (agent, hop, loss/
latency deltas, timestamps). If it doesn't, say **"leading hypothesis"** and keep looking app-side.
