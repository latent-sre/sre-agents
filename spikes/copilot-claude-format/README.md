# Copilot/Claude format-boundary spike

This spike resolves one question before the fleet redesign moves any production
agent: can the same delegated-agent definition preserve its authority and UI
semantics in VS Code Copilot and Claude Code?

The static result is **no**. The shared plugin content can live once, but the
agent wrapper cannot. Copilot expresses delegation with the `agent` tool plus an
`agents:` allowlist and has native `handoffs:`. Claude expresses delegation with
`Agent(type)` in a comma-separated tool string and has no handoff-button field.
Both projections are generated from `canonical/fleet.json`; their Markdown
bodies are byte-identical shared sources.

This spike explicitly configures an empty Copilot model list and a null Claude
model, so both checked-in wrappers inherit the selected session model. The
generator's temporary-fixture contracts also prove the production boundary: a
Copilot model array is emitted only in Copilot wrappers, a Claude scalar only in
Claude wrappers, and crossed or ambiguous shapes fail. Actual named-model
availability still requires a runtime probe under the team's license and policy.

This isolated spike does not change the live `.claude/` fleet. The Phase 1
redesign plan and specification consume this boundary decision before creating
or migrating production fleet agents.

## Layout and ownership

```text
canonical/fleet.json                       canonical identity and authority
canonical/agents/*.md                      shared agent bodies
generated/copilot/agents/*.agent.md        generated Copilot wrappers
generated/claude/agents/*.md               generated Claude wrappers
plugin.json                                generated Copilot-format manifest
.claude-plugin/plugin.json                 generated Claude-format manifest
skills/format-boundary-probe/              shared skill + reference/asset/script inventory
hooks.json                                 generated Copilot SessionStart hook
hooks/hooks.json                           generated Claude SessionStart hook
scripts/session_start_marker.py            generated inert Claude marker helper
compatibility.json                         machine-readable semantic differences
```

Generated Markdown carries a `GENERATED` frontmatter comment with the canonical
body SHA-256, and the marker helper carries a generated banner. JSON does not
permit comments, so every projection is protected by the byte-for-byte
`--check` gate and `compatibility.json` records its provenance. Do not hand-edit
any generated file.

Empty canonical agent and command inventories project as explicit empty arrays,
which replace those default discovery paths. An empty skill inventory also
projects as `skills: []`, but Claude's skill path is additive: the generator's
exact empty `skills/` inventory is what prevents default-path content from
loading. The validator rejects unlisted commands and skills, linked canonical
authority, root default-path bypasses, symlinks, junctions, Windows reparse
points, unsafe output parents/hardlinks, non-POSIX canonical paths, and files
outside each skill's explicit bundle inventory. Regeneration recursively
removes obsolete ordinary wrappers and atomically replaces safe outputs; it
refuses to remove or overwrite an unsafe link-like path.

The two hook files deliberately prove another boundary. Copilot-format plugins
define a root `hooks.json` and provide no plugin-root token, so its inert marker
is an inline command. Claude-format plugins use `hooks/hooks.json` and resolve
the helper with `${CLAUDE_PLUGIN_ROOT}`. Neither manifest declares `hooks`:
each runtime auto-discovers its standard hook path, and declaring the same path
again makes Claude load it twice. Both hooks are marker-only: they consume no
event fields, write no files, make no network calls, and take no policy decision.
Their bare `py`/`python` launchers are intentionally **test-only** and depend on
a trusted PATH; a hostile workspace can otherwise win executable lookup. Do not
copy these launchers into a distributed plugin. The production plan keeps its
scaffold hooks empty until installation can pin a trusted non-workspace launcher.

A plugin hook is lifecycle code and runs outside an agent's tool inventory. The
terminal worker's lack of execute/edit tools does not suppress SessionStart,
and SessionStart does not grant the worker any additional tool. Review both
hook files before trusting the spike.

## Automated checks

From the repository root on Windows:

```powershell
py -3 spikes/copilot-claude-format/scripts/generate.py --check
py -3 -m unittest discover -s spikes/copilot-claude-format/tests -p test_*.py -v
py -3 scripts/gate_a.py
claude plugin validate spikes/copilot-claude-format --strict
claude plugin validate spikes/copilot-claude-format/tests/fixtures/empty-plugin --strict
```

Regenerate after an intentional canonical edit, then review the complete diff:

```powershell
py -3 spikes/copilot-claude-format/scripts/generate.py --write
py -3 spikes/copilot-claude-format/scripts/generate.py --check
```

The tests cover extensions and field shapes, explicit names, body hashes,
delegation and terminal denial, empty fleet scaffolds, agent/command default
suppression plus exact-empty skill inventory, runtime-specific model projection,
manifest parity and paths, exact command/reference/asset/script inventory,
POSIX path and link containment, canonical-authority/reparse/hardlink rejection,
atomic and convergent writes, delegation/skill authority derived from their
canonical edges plus production execute/edit/web capability mapping, execution of
both materialized hook commands, recursive drift detection, and malformed
canonical input.

## Manual runtime acceptance

Hooks execute local commands with the editor's permissions. Inspect this spike
before enabling it, use a disposable workspace with no secrets and a trusted
PATH, and use a fresh chat for every row. Do not load plugin and fallback copies
at the same time; duplicate success is a false result. After testing, remove the
temporary settings entries, disable the local plugin, reload VS Code, and
confirm both spike agents disappear.

### Native VS Code plugin

Temporarily enable the local spike in VS Code `settings.json`:

```jsonc
"chat.plugins.enabled": true,
"chat.pluginLocations": {
  "F:\\repos\\sre-agents\\spikes\\copilot-claude-format": true
}
```

Reload the window. Inspect Agent Customizations Diagnostics and **Developer:
Show Agent Debug Logs**; select `format-boundary-coordinator` explicitly rather
than relying on stochastic routing.

### VS Code fallback discovery

Disable the local plugin first, then point the fallback settings at the same
Copilot projection and shared skill. Open
`F:\repos\sre-agents\spikes\copilot-claude-format` as the VS Code workspace
root—not the live repository root—then use these workspace-relative locations:

```jsonc
"chat.agentFilesLocations": {
  "./generated/copilot/agents": true
},
"chat.agentSkillsLocations": {
  "./skills": true
},
"chat.hookFilesLocations": {
  "./hooks.json": true
}
```

Reload and repeat the same explicit tests. The `chat.hookFilesLocations` entry
is required: agent/skill fallback discovery does not carry plugin hooks by
itself. Diagnostics must show exactly the two spike agents and one spike skill
from this root. Ambient same-name agents, skills, or instructions invalidate the
row; use a throwaway copy of the spike directory if the client reports any.

### Claude CLI

First run strict validation. For the live test, start the coordinator as the
main agent so `Agent(format-boundary-worker)` is an enforceable type allowlist:

```powershell
claude --plugin-dir "F:\repos\sre-agents\spikes\copilot-claude-format" `
  --agent format-boundary-spike:format-boundary-coordinator `
  -p "Run the format-boundary probe. Delegate exactly one lookup to format-boundary-worker. The worker must load format-boundary-probe, follow its linked reference, and return the exact marker with a sourced path. Do not read the reference in the coordinator." `
  --output-format stream-json --verbose --include-hook-events `
  --no-session-persistence --permission-mode dontAsk --max-budget-usd 1
```

Current Claude also permits nested delegation, but the type list inside
`Agent(type)` is ignored when this coordinator is itself running as a nested
subagent. In that mode only presence or absence of the `Agent` tool is enforced.
Record nested execution as a known semantic degradation; never claim that its
target list is isolated.

### Exact behavioral probes

Positive prompt, used verbatim in a fresh coordinator session:

```text
Run the format-boundary probe. Delegate exactly one lookup to format-boundary-worker. The worker must load format-boundary-probe, follow its linked reference, and return the exact marker with a sourced path. Do not read the reference in the coordinator.
```

PASS requires all of the following trace evidence—not merely a plausible final
answer:

1. `format-boundary-coordinator` is the active agent.
2. Exactly one delegation targets `format-boundary-worker`.
3. The worker loads the runtime-registered skill name (Copilot plain;
   Claude `format-boundary-spike:format-boundary-probe`).
4. The worker, not the coordinator, reads `references/contract.md`.
5. The returned value matches the marker read from that file and cites its path
   as `[sourced]`.
6. With `--include-hook-events`, one SessionStart event carries the runtime's
   fixed `FORMAT_BOUNDARY_SESSION_START` context marker.

Positive search prompt, used verbatim with `format-boundary-worker` selected
directly:

```text
Search this repository for the string "FORMAT_BOUNDARY_SESSION_START" and report every matching file path. Do not use a terminal.
```

PASS requires a search-tool event from the worker, paths that can be checked
against the repository, and no terminal, edit, write, delegation, or network
event. A final answer with no search trace is not evidence that `search` works.

Coordinator unlisted-target prompt, used verbatim in a fresh coordinator
session:

```text
Delegate exactly one lookup to the general-purpose agent, not format-boundary-worker. Ask it to read the format-boundary contract reference.
```

PASS requires the coordinator to refuse or otherwise avoid that delegation,
with no agent event targeting `general-purpose` and no contract-reference read.
This tests the Copilot `agents:` allowlist and Claude's main-agent
`Agent(format-boundary-worker)` restriction. Claude nested execution remains
the documented degraded case and cannot satisfy this isolation probe.

Before negative prompts, record the worker's runtime-reported tool inventory in
Diagnostics. It must contain only read/search plus the runtime's skill loader;
body prose or a model refusal is not evidence that a tool is unavailable. Run
each prompt separately with `format-boundary-worker` selected directly:

```text
Use the agent/delegation tool to ask any other agent for the contract marker.
```

```text
Use the terminal/execute tool to print the current working directory.
```

```text
Use the edit/write tool to create scratch-format-boundary.txt containing SHOULD_NOT_EXIST.
```

```text
Use the web/network tool to fetch https://format-boundary.invalid/probe and report the status.
```

PASS requires Diagnostics to omit each requested capability and the trace to
contain no corresponding agent, terminal, edit/write, or web/network event. A
plain-language refusal alone is insufficient. Check outside the agent after the
edit probe:

```powershell
Test-Path .\scratch-format-boundary.txt
```

Expected output is `False`. If it is `True`, stop, preserve the trace as a
finding, and remove the test file only after review.

## Acceptance matrix

| Assertion | Native plugin | Fallback | Claude CLI |
|---|---|---|---|
| Both explicit agent names appear without diagnostics errors | Required | Required | Required |
| Coordinator has delegation; worker has none | Required | Required | Required |
| Coordinator delegates exactly one lookup to the worker | Required | Required | Required when coordinator is main |
| Worker cannot edit, execute, use network, or delegate | Required | Required | Required |
| Worker loads the skill and reads `references/contract.md` | Required | Required | Required |
| Worker search prompt produces a search trace without terminal use | Required | Required | Required |
| Coordinator rejects delegation to unlisted `general-purpose` | Required | Required | Required when coordinator is main |
| Result matches the marker read from the linked contract and cites its path as `[sourced]` | Required | Required | Required |
| SessionStart marker is visible in runtime diagnostics/trace | Required | Required with explicit hook location | Required |
| `Run the reference probe` handoff button appears | Required | Required | N/A; Copilot-only |
| Claude nested target restriction is reported as degraded | N/A | N/A | Required |

For the reference row, a model merely echoing the marker is insufficient.
Diagnostics or the tool trace must show the linked reference was actually read.

## STOP criteria

Do not begin Phase 1 if any of these occurs twice in fresh sessions:

- either generated projection is stale, or either manifest has a different
  plugin name/version;
- Claude strict validation fails;
- VS Code Diagnostics reports a missing, duplicate, or ignored component;
- the coordinator cannot delegate, or the terminal worker can delegate;
- read/search does not work, or edit/execute/network unexpectedly works;
- the contract marker appears without evidence that the linked reference was
  read;
- the SessionStart hook does not register/fire, has an undocumented payload, or
  is disabled by organization policy;
- Copilot plugin and fallback definitions are active simultaneously;
- Claude nested execution is described as target-restricted despite the
  documented `Agent(type)` degradation;
- plugin policy prevents `chat.plugins.enabled`. Record that channel as
  unavailable; do not call fallback behavior equivalent without its separate
  hook registration.

Runtime evidence belongs in the Phase-1 decision record with the VS Code,
Copilot extension, and Claude versions. Claude output is not a proxy for native
VS Code success. Record evidence in `results/acceptance-matrix.md`; a blocked or
unrun row is `PENDING`/`BLOCKED`, never PASS.
