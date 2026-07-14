# Format-boundary acceptance evidence

- **Evidence date:** 2026-07-13
- **Branch:** `codex/copilot-claude-format-spike`
- **Claude Code:** 2.1.208
- **VS Code:** 1.128.0
- **GitHub Copilot extension:** `[unverified]`

This record separates structural evidence from runtime behavior. A loader that
registers components but cannot complete an API request does not prove routing,
delegation, skill/reference loading, or tool denial.

## Automated evidence

| Check | Result | Evidence |
|---|---|---|
| Red-first generator contract | OBSERVED / `[unverified—no durable raw log]` | 14/14 tests were observed erroring against the intentional stub before implementation, but the console transcript was not persisted. |
| Final generator contract | PASS | `[verified]` 28/28 focused tests passed, including execution of both materialized current-OS hook commands, rejection of misnamed/orphan canonical agent bodies, and canonical derivation of compatibility names. |
| Projection drift | PASS | `[verified]` `generate.py --check`: 10 generated files match `canonical/fleet.json`. |
| Model-field boundary | NOT IN SPIKE | `[sourced]` `compatibility.json` records that `model` is omitted so both runtimes inherit the session model; production mapping remains a separate generator/runtime gate. |
| Claude strict plugin schema | PASS | `[verified]` `claude plugin validate spikes/copilot-claude-format --strict`: `Validation passed`. Strict schema validation is not runtime-loader evidence. |
| Repository Gate A | PASS | 8/8 structural steps green, including the spike suite. |
| Diff whitespace | PASS | `[verified]` `git diff --check` produced no tracked-diff findings; `rg -n "[ \\t]+$"` produced no findings across the untracked spike and modified docs/scripts. |

### Materialized hook command evidence

In this root turn, the focused suite executed the command selected from the
checked-in Windows Copilot handler, with a 10-second timeout:

```text
py -3 -c "import json; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': 'FORMAT_BOUNDARY_SESSION_START:copilot'}}))"
```

`[verified]` It exited zero, wrote nothing to stderr, and emitted:

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "FORMAT_BOUNDARY_SESSION_START:copilot"}}
```

The same suite read the checked-in Claude exec form, substituted the actual
plugin root, and executed this configured command with a 10-second timeout:

```text
python F:\repos\sre-agents\spikes\copilot-claude-format\scripts\session_start_marker.py claude
```

`[verified]` It exited zero, wrote nothing to stderr, and emitted:

```json
{"hookSpecificOutput": {"additionalContext": "FORMAT_BOUNDARY_SESSION_START:claude", "hookEventName": "SessionStart"}}
```

These are local command-contract checks; they do not prove either runtime
discovered or invoked the hook.

## Runtime loader evidence

The first Claude loader run used:

```powershell
claude --plugin-dir "F:\repos\sre-agents\spikes\copilot-claude-format" --agent format-boundary-spike:format-boundary-coordinator -p "Run the format-boundary probe. Delegate exactly one lookup to format-boundary-worker. The worker must load format-boundary-probe, follow its linked reference, and return the exact marker with a sourced path. Do not read the reference in the coordinator." --output-format stream-json --verbose --include-hook-events --no-session-persistence --permission-mode dontAsk --max-budget-usd 1
```

Observed before the hook correction:

- [verified] Loader initialization registered both scoped agents and the
  `format-boundary-spike:format-boundary-probe` skill.
- [verified] `plugin_errors` reported: `Duplicate hooks file detected:
  ./hooks/hooks.json ... standard hooks/hooks.json is loaded automatically`.
  This is the red runtime evidence that caused both manifests to stop declaring
  their standard hook paths.
- [verified] The API connection was refused by the managed sandbox after 10
  retries over approximately 180 seconds; spend was `$0`.
- [blocked] No model response or behavioral trace was produced, so delegation,
  reference loading, terminal denial, and SessionStart execution remain
  unmeasured.

The corrected plugin passes strict schema validation, but corrected runtime
loading remains unverified. A requested external behavioral run was rejected by
the managed execution policy because model submission could exfiltrate
repository content. `[blocked]` A corrected loader/behavior run must therefore
be performed by a human in the trusted acceptance environment.

## Channel acceptance status

| Assertion | Claude CLI | Native VS Code plugin | VS Code fallback |
|---|---|---|---|
| Strict manifest/schema validation | PASS (strict) | PENDING | PENDING |
| Corrected runtime loader initializes without plugin errors | BLOCKED: policy rejected external run | PENDING | PENDING |
| Both agents and shared skill register | PARTIAL: pre-fix loader observed them | PENDING | PENDING |
| Exactly one coordinator-to-worker delegation | BLOCKED: API unavailable | PENDING | PENDING |
| Linked reference is actually read | BLOCKED: API unavailable | PENDING | PENDING |
| Terminal worker cannot delegate/edit/execute/network | BLOCKED: API unavailable | PENDING | PENDING |
| SessionStart marker fires exactly once | BLOCKED: corrected loader not run | PENDING | PENDING |
| Copilot handoff button appears | N/A | PENDING | PENDING |
| No scratch side effect | BLOCKED: negative runtime probe not run | PENDING | PENDING |

## Ten-pass review record

| Pass | Result | Scope and evidence |
|---:|---|---|
| 1 | PASS | `[verified]` Branch base and current remote `main` are both `1cfe7cbd08d54fa8c9dac0f5ca1a10587d5575e3`. |
| 2 | PASS | `[sourced]` Compared current [VS Code custom-agent](https://code.visualstudio.com/docs/agent-customization/custom-agents), [agent-plugin](https://code.visualstudio.com/docs/agent-customization/agent-plugins), [hook](https://code.visualstudio.com/docs/agent-customization/hooks), [Claude subagent](https://code.claude.com/docs/en/sub-agents), and [Claude plugin](https://code.claude.com/docs/en/plugins-reference) contracts. |
| 3 | PASS | `[verified]` Canonical identity, exact body/skill/reference inventory, dependency parity, and orphan rejection are covered by the focused suite. |
| 4 | PASS — static scope | `[verified]` Copilot root manifest uses an agent directory; Claude manifest uses explicit files and passes Claude strict validation. Native Copilot loading remains pending. |
| 5 | PASS — static scope | `[verified]` Every generated wrapper has an explicit name and byte-identical canonical body; suffix/frontmatter differences are generated. |
| 6 | PASS — static scope | `[verified]` Copilot emits `agent` + `agents`; Claude emits `Agent(target)`; the worker omits delegation in both. Behavioral enforcement remains pending. |
| 7 | PASS — static scope | `[verified]` The shared skill links the inventoried reference and runtime-qualified skill names derive from canonical data. Actual runtime reference reads remain pending. |
| 8 | PASS — local command scope | `[verified]` Both materialized hook commands emit the exact marker JSON. Runtime discovery/invocation remains pending. |
| 9 | PASS | `[verified]` Projection drift is 10/10, focused contracts are 28/28, Claude strict validation passes, Gate A is 8/8, and tracked/untracked whitespace checks are clean. |
| 10 | NOT CLEARED | `[blocked]/[pending]` Corrected Claude behavior is policy-blocked here; native plugin and fallback behavior require manual VS Code acceptance. |

Review execution is **10/10 (100%)**. Automated/static checks are green in
their declared scope. Cross-runtime behavior is **0/3 channels accepted (0%)**,
so the binary Phase-1 clearance remains **0%**.

## Exit ruling

**Phase 1 format boundary: NOT YET CLEARED.** Static generation and Claude strict
validation are green. Native plugin, fallback, and successful Claude behavioral
runs remain required. No pending or blocked row may be promoted to PASS from a
Claude proxy or from component-registration evidence alone.
