---
name: python-craft
description: >-
  Idiomatic, production-grade Python conventions for this team — typing, linting/formatting, testing,
  errors, structure, and operational safety. Use whenever writing, reviewing, or refactoring Python,
  especially for ops tooling, automation, and services. Covers type hints, ruff/black, pytest, pathlib,
  exceptions, subprocess/HTTP safety, and logging without leaking secrets.
metadata:
  domain: language
  language: python
---

# Python craft

Write Python a reviewer approves on the first pass. Match the repo's existing tooling first; the
defaults below apply when none is set.

## Style & tooling
- **Type hints everywhere** public; check with `mypy`/`pyright` (or the faster Rust checkers `ty`
  (Astral) / `pyrefly` (Meta) for editor-speed feedback — preview-grade, not for CI gating yet). Prefer
  precise types; avoid `Any`.
- **Format + lint** with `ruff` (lint+format) or `black`+`ruff`. Don't hand-format.
- **Structure:** small functions, early returns, no deep nesting. Prefer `dataclasses`/`pydantic` for
  structured data over loose dicts/tuples.
- **Paths & resources:** `pathlib.Path` over `os.path`; always context managers (`with`) for files,
  locks, connections.
- **Respect the env manager** in the repo; **`uv`** is the fast default (envs, locking, running tools —
  replaces pip/venv/pipx), `poetry` is fine for published libraries. Never `pip install` into system Python.

## Correctness traps to avoid
- Mutable default args (`def f(x=[])`) — use `None` + assign inside.
- **Swallowing** exceptions — bare `except:` or `except Exception: pass` hides bugs. Catch specific
  types; a top-level boundary may catch broadly but must **log and re-raise** (or convert), never
  silently continue.
- `==` vs `is` (use `is` only for `None`/singletons); truthiness bugs on `0`/`""`/empty collections.
- Generator exhaustion; modifying a list while iterating; floating-point equality.
- Blocking calls inside `async` code.

## Errors & logging
- Raise specific exceptions with context; don't return sentinel error codes.
- Use the `logging` module (not `print`) with structured/levelled logs. **Never log secrets, tokens,
  PII, or full request bodies.**
- Fail loud in tooling: non-zero exit + a clear stderr message.

## Operational safety (ops/automation code)
- `subprocess.run([...], check=True)` with a **list** (never `shell=True` on untrusted input).
- HTTP (`requests`/`httpx`): **always set timeouts**; retry idempotent calls with backoff; check status.
- Parameterize SQL — never f-string user input into a query.
- Make scripts idempotent and re-runnable; guard destructive actions behind an explicit flag.
- **Separate decision from effect** so logic is testable without side effects: a pure function computes
  *what* to do (e.g. `desired_replicas(...)`), a thin wrapper *does* it. `--dry-run` then becomes trivial,
  and you can prove it with a spy: `spy = mocker.patch("mod.subprocess.run"); run(dry_run=True); spy.assert_not_called()`.

## Tests
- `pytest`: arrange-act-assert, `parametrize` for cases, fixtures for setup, `tmp_path` for files,
  `monkeypatch`/`unittest.mock` for boundaries, `freezegun`/injected clock for time. See `tdd-workflow`.
- Test behavior and error paths, not internals. `pytest --cov` to find untested branches that matter.
