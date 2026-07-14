# Format-boundary acceptance evidence

- **Evidence window:** 2026-07-13 through 2026-07-14
- **Final hardening rerun:** 2026-07-14
- **Branch:** `codex/copilot-claude-format-spike`
- **Claude Code:** 2.1.208
- **VS Code:** 1.128.0
- **GitHub Copilot extension:** `[unverified]`
- **Acceptance-owner clearance:** 2026-07-14 (`[sourced]`, human-attested)

This record separates structural evidence from runtime behavior. A loader that
registers components but cannot complete an API request does not prove routing,
delegation, skill/reference loading, or tool denial.

## Automated evidence

| Check | Result | Evidence |
|---|---|---|
| Red-first generator contract | OBSERVED / `[unverified—no durable raw log]` | The original 28/28 contracts stayed green while all 9 new reusable-generator test methods failed against the old implementation (17 failures and 6 errors across their subtests); the console transcript was observed in-session but not persisted as a repository artifact. |
| Adversarial red-first contract | OBSERVED / `[unverified—no durable raw log]` | After read-only review, 48 tests reproduced 19 failures and 4 errors for default-path discovery, recursive stale files, non-convergent writes, link/path containment, unsafe model strings, body exactness, and ambiguous compatibility counts. One real Windows symlink fixture initially skipped for missing privilege; its parent setup was corrected before the green run. |
| Supply-chain red-first contract | OBSERVED / `[unverified—no durable raw log]` | Six new focused methods failed in the intended gaps (10 subtest failures and 2 errors): command inventory, canonical-root/manifest redirection, Windows reparse detection, atomic replacement, and trimmed single-line frontmatter validation. The same six methods passed after implementation. |
| Final generator contract | PASS | `[verified]` 60 focused tests were discovered: 59 passed and the real Windows symlink-creation case skipped because this account lacks symlink privilege; deterministic tests cover fail-closed link/junction/reparse rejection and prove link-like directories are pruned before traversal. Coverage includes explicit agent/command default suppression, validator-enforced exact-empty skill inventory, delegation/skill authority derived from canonical edges, production execute/edit/web capability mapping, atomic/convergent writes, recursive any-suffix drift, exact command/reference/asset/script inventory, canonical-authority/POSIX/link/hardlink containment, runtime-specific model projection, materialized hook commands, and malformed canonical input. |
| Projection drift | PASS | `[verified]` `generate.py --check`: 10 generated files match `canonical/fleet.json`. |
| Model-field boundary | PASS — structural | `[verified]` The checked-in spike explicitly configures an empty Copilot list and null Claude value, so both wrappers inherit. Temporary fixtures prove a Copilot array is emitted only to Copilot, a Claude scalar only to Claude, and crossed/blank/duplicate/agent-local shapes fail. Named-model runtime availability remains pending. |
| Claude strict plugin schema | PASS | `[verified]` `claude plugin validate spikes/copilot-claude-format --strict`: `Validation passed`, including explicit `commands: []`. Strict schema validation is not runtime-loader evidence. |
| Empty-registration Claude schema | PASS | `[verified]` The checked-in `tests/fixtures/empty-plugin` scaffold with explicit empty agents/skills/commands passed `claude plugin validate spikes/copilot-claude-format/tests/fixtures/empty-plugin --strict`. Native Copilot behavior remains a separate runtime row. |
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

The acceptance owner subsequently reported that the trusted-environment checks
were completed and explicitly cleared all three channels on 2026-07-14.
`[sourced]` Human-attested. No durable raw runtime packet was added to this
checkout, so this record preserves the earlier locally observed
`[verified]`/`[blocked]` evidence above instead of relabeling it as independently
verified by this repository session.

## Channel acceptance status

| Assertion | Claude CLI | Native VS Code plugin | VS Code fallback |
|---|---|---|---|
| Strict manifest/schema validation | PASS (strict) | PASS — human-attested | PASS — human-attested |
| Corrected runtime loader initializes without plugin errors | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| Both agents and shared skill register | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| Exactly one coordinator-to-worker delegation | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| Linked reference is actually read | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| Terminal worker cannot delegate/edit/execute/network | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| SessionStart marker fires exactly once | PASS — human-attested | PASS — human-attested | PASS — human-attested |
| Copilot handoff button appears | N/A | PASS — human-attested | N/A |
| No scratch side effect | PASS — human-attested | PASS — human-attested | PASS — human-attested |

## Ten-pass review record

| Pass | Result | Scope and evidence |
|---:|---|---|
| 1 | PASS | `[verified]` Branch base and current remote `main` are both `1cfe7cbd08d54fa8c9dac0f5ca1a10587d5575e3`. |
| 2 | PASS | `[sourced]` Compared current [VS Code custom-agent](https://code.visualstudio.com/docs/agent-customization/custom-agents), [agent-plugin](https://code.visualstudio.com/docs/agent-customization/agent-plugins), [hook](https://code.visualstudio.com/docs/agent-customization/hooks), [Claude subagent](https://code.claude.com/docs/en/sub-agents), and [Claude plugin](https://code.claude.com/docs/en/plugins-reference) contracts. |
| 3 | PASS | `[verified]` Canonical identity, exact body/command/skill/reference/asset/script inventory, explicit agent/command default suppression, exact-empty Claude skill-tree control, canonical-root/link/reparse/hardlink containment, dependency parity, wrong-extension/orphan rejection, and atomic/convergent writes are covered by the focused suite. |
| 4 | PASS — static scope | `[verified]` Copilot root manifest uses an agent directory; Claude manifest uses explicit files and passes Claude strict validation. Native Copilot loading remains pending. |
| 5 | PASS — static scope | `[verified]` Every generated wrapper has an explicit name and byte-identical canonical body; suffix/frontmatter differences are generated. |
| 6 | PASS — static scope | `[verified]` Copilot emits `agent` + `agents`; Claude emits `Agent(target)`; the worker omits delegation in both. Behavioral enforcement remains pending. |
| 7 | PASS — static scope | `[verified]` The shared skill links its inventoried reference and inert asset/script markers; runtime-qualified skill names derive from canonical data. Actual runtime reference reads remain pending. |
| 8 | PASS — local command scope | `[verified]` Both materialized hook commands emit the exact marker JSON. Runtime discovery/invocation remains pending. |
| 9 | PASS | `[verified]` Projection drift is 10/10, focused contracts discover 60 tests (59 pass, 1 OS-privilege skip with deterministic branch coverage), Claude strict validation passes for the populated and explicit-empty manifests, Gate A is 8/8, and tracked/untracked whitespace checks are clean. |
| 10 | CLEARED | `[sourced]` Human-attested: the acceptance owner reports that corrected Claude behavior plus native-plugin and fallback behavior passed in the trusted acceptance environment. |

Review execution is **10/10 (100%)**. Automated/static checks are green in
their declared scope. Cross-runtime behavior is **3/3 channels accepted (100%)**
by acceptance-owner attestation, so the binary Phase-1 clearance is **100%**.

## Exit ruling

**Phase 1 format boundary: CLEARED.** Static generation and Claude strict
validation are `[verified]`; native plugin, fallback, and successful Claude
behavioral acceptance are `[sourced]` and human-attested from the acceptance owner's
2026-07-14 clearance. The earlier blocked local execution history remains above
so the handoff does not upgrade unobserved repository-session evidence to
`[verified]`.
