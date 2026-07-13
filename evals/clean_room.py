#!/usr/bin/env python3
"""Isolate a harness trial from the operator's machine.

Both harnesses shell out to `claude -p ...`. With no explicit `env`, that inherits the operator's
entire Claude Code install: ~/.claude/skills, ~/.claude/agents, installed plugins (which may ship
those same skills AGAIN), and the operator's global CLAUDE.md. Those do not shadow the fleet by name
-- they COMPETE with it for skill discovery, which is the one thing discovery_probe.py exists to
measure. Every number it ever produced described the LAPTOP, not the fleet, and every recorded
baseline says so ("treat as a LOWER BOUND").

CLAUDE_CONFIG_DIR relocates the whole user config -- "If you set CLAUDE_CONFIG_DIR, every ~/.claude
path on this page lives under that directory instead" (code.claude.com/docs/en/claude-directory).
Point it at a temp dir holding ONLY the credentials and the model sees the project's .claude/ and
nothing else. Probed: sde-ladder (project) YES / eng-ladder (personal) NO / backend-craft
(personal + plugin) NO.

WHY THIS MODULE REFUSES RATHER THAN DEGRADES
An EMPTY config dir breaks auth, and that failure is silent in the worst possible way: `claude -p`
still emits a VALID stream-json trace (system/init and all), exits 1, and reports "Not logged in" in
the RESULT event -- while stderr carries only an unrelated stdin warning. A harness that parses that
trace finds no Skill() call and scores a clean NO-ROUTE. Every scenario "fails", and the report reads
as a devastating finding about the fleet rather than as a broken instrument. An eval harness that
converts its own breakage into findings about the thing it measures is the worst failure available to
it. So: no credentials -> AuthUnavailable, before a single trial runs; and an auth-failure trace is an
ERROR, never a routing outcome.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"

# Markers of an auth failure in a trial's output.
# NOT `subtype`: the result event of a not-logged-in run says subtype="success" while is_error=true.
AUTH_MARKERS = ("authentication_failed", "Not logged in")


class AuthUnavailable(RuntimeError):
    """Fatal: the harness cannot produce a valid measurement. Never scored as a result."""


def _warn_leftover(func, path, exc) -> None:
    """onexc handler for the clean-room rmtree: never fail silently, we're deleting a credential copy."""
    print(
        f"clean_room: WARNING -- failed to remove {path} ({func.__name__}: {exc}). "
        f"This directory holds a COPY OF THE AUTH CREDENTIALS and was left on disk.",
        file=sys.stderr,
    )


def user_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def credentials_path() -> Path:
    return user_config_dir() / CREDENTIALS


def require_credentials() -> Path:
    p = credentials_path()
    if not p.is_file():
        raise AuthUnavailable(
            f"no Claude credentials at {p}.\n"
            f"The clean room needs them. Without them every trial returns 'Not logged in', which "
            f"this harness would parse as a trace with no Skill() call and score as a no-route -- "
            f"turning a broken instrument into a fake finding about the fleet. Refusing to run.\n"
            f"Fix: run `claude` and /login, or point CLAUDE_CONFIG_DIR at a config dir containing "
            f"{CREDENTIALS}."
        )
    return p


def is_auth_failure(text: str, returncode: int | None = None) -> bool:
    """True if a trial's output shows the run never authenticated.

    Gated on a NON-ZERO exit. This is an SRE fleet: a healthy response can legitimately quote a log
    line containing "Not logged in" (an auth incident, a Splunk triage scenario), and aborting the
    suite on that would be a false fatal -- as bad as the fail-open this module exists to close. A
    real auth failure exits 1 (probed); a healthy run exits 0. rc == 0 is therefore never an auth
    failure, whatever the text says.

    `returncode=None` means "unknown" (e.g. a TimeoutExpired, which carries no rc) -- fall back to
    the marker scan, since a timed-out run has no exit code to gate on.
    """
    if returncode == 0:
        return False
    return any(m in (text or "") for m in AUTH_MARKERS)


@contextlib.contextmanager
def clean_env():
    """Yield an env whose CLAUDE_CONFIG_DIR holds ONLY the credentials.

    The model then sees the project's .claude/skills and .claude/agents and nothing else: no personal
    skills, no personal agents, no installed plugins, no personal CLAUDE.md.
    """
    creds = require_credentials()
    tmp = Path(tempfile.mkdtemp(prefix="fleet-cleanroom-"))
    try:
        # 0700 -- it holds an auth secret. Advisory only on non-POSIX filesystems (e.g. Windows/NTFS,
        # where os.chmod cannot enforce POSIX user/group/other bits); real protection there comes from
        # the temp dir already being user-scoped. Enforced for real on the POSIX CI runners this
        # harness targets.
        os.chmod(tmp, stat.S_IRWXU)
        dst = tmp / CREDENTIALS
        shutil.copyfile(creds, dst)
        os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR)       # 0600 -- same advisory-only caveat as above.
        yield dict(os.environ, CLAUDE_CONFIG_DIR=str(tmp))
    finally:
        shutil.rmtree(tmp, onexc=_warn_leftover)  # onexc (3.12+): repo/CI both pin Python 3.12.
