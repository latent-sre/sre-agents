---
name: tool-design
description: >-
  Design tools an LLM agent can actually use well — clear names, prescriptive descriptions,
  token-efficient responses. Use when exposing a capability (cf/Splunk/Wavefront, an internal API, an MCP
  server) **as a tool an agent calls** — not an HTTP API for humans or services (that's `api-design`) —
  or fixing a tool the model misuses. Covers strategic selection, namespacing, meaningful context, token
  efficiency, and the prototype→evaluate loop. From Anthropic's "Writing effective tools for agents."
---

# Tool design

Agents are **non-deterministic users of deterministic tools** — the tool's name, description, inputs,
and output shape are the interface the model reasons over. Design for the model as you'd design an API
for a careful-but-literal junior engineer. *[sourced: Anthropic, "Writing effective tools for agents"]*

## Five principles
1. **Strategic selection.** Build a few high-signal tools for real workflows — don't wrap every endpoint.
   A `get_app_health(app)` that returns the answer beats five raw calls the agent must chain.
2. **Clear namespacing.** Prefix by domain so intent is unambiguous (`cf_restart_app`, `splunk_search`,
   `wavefront_query`) — prevents confusing similar tools.
3. **Meaningful context (prescriptive descriptions).** State **when to call it**, not just what it does:
   *"Use when investigating a degraded PCF app — returns instance states + recent crash events."* On
   recent models this measurably raises correct should-call rate.
4. **Token efficiency.** Return high-signal, bounded output. Implement pagination / range selection /
   filtering / truncation with sensible defaults; cap large responses (Claude Code defaults tool output
   to ~25K tokens). Give **helpful error messages** that steer the agent toward a better call.
   *[sourced: Anthropic, "Writing effective tools for agents" — token efficiency + actionable errors]*
5. **Engineer the surface, then iterate.** Treat the schema and description as a prompt you tune.

## Promote bash → a dedicated tool when you need to…
gate (hard-to-reverse/prod actions), staleness-check, render, or parallelize. A `cf_restart_app` tool
the harness can gate and audit is safer than `bash -c "cf restart ..."`; start with bash for breadth,
promote the actions that need control. *[sourced: Anthropic, "Writing effective tools for agents"]*

## Process
**Prototype → evaluate → collaborate.** Build the tool, run the agent against realistic tasks, watch
*how* it misuses it (wrong tool, over-broad query, context blown by huge output), and fix the
name/description/defaults. Repeat — `self-improve-loop` applied to a tool. *[sourced: Anthropic, "Writing effective tools for agents" — prototype→evaluate loop]*

## In this fleet
Reach for this when exposing `cf`/Splunk/Wavefront/ThousandEyes capability or an MCP server to an agent,
or building automation a human release owner/`sre-monitor` will drive. Pair with `agent-security`: gate and
allowlist anything that touches prod or sends data out; keep secrets out of tool inputs/outputs.

## Handoffs
- → `sde-engineer` to implement the tool. → `self-improve-loop` for the prototype→evaluate iteration.
- → `agent-security` for gating/allowlisting tools that act externally or read untrusted input.
