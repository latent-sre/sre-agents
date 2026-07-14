#!/usr/bin/env python3
"""Phase-2 5d gate: frontmatter, links, and direct bundle reachability.

This is intentionally a narrow, stdlib-only bridge to validator v2.  It checks
new shared skills and canonical command bodies; it does not validate generated
runtime projections.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):(?:[ \t]*(.*))?$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
CODE_PATH_RE = re.compile(
    r"`((?:references|assets|scripts)/[A-Za-z0-9._/-]+)`"
)
ALLOWED_KEYS = {
    "name",
    "description",
    "argument-hint",
    "disable-model-invocation",
    "compatibility",
}
MANUAL_ONLY = {"pcf-deploy", "service-onboarding"}


def _strip_fences(text: str) -> str:
    kept = []
    fence = None
    for line in text.splitlines(keepends=True):
        match = re.match(r"^[ \t]*(```+|~~~+)", line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            kept.append("\n" if line.endswith(("\n", "\r")) else "")
        elif fence is None:
            kept.append(line)
        else:
            kept.append("\n" if line.endswith(("\n", "\r")) else "")
    return "".join(kept)


def _yaml_string(raw: str, where: str, failures: list[str]) -> str | None:
    raw = raw.strip()
    if not raw:
        failures.append(f"{where}: value must be one nonblank YAML string")
        return None
    if raw.startswith("[") or raw.startswith("{"):
        failures.append(f"{where}: value must be a string, not a collection")
        return None
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            failures.append(f"{where}: invalid quoted string")
            return None
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{where}: value must be one nonblank YAML string")
            return None
        return value
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            failures.append(f"{where}: invalid quoted string")
            return None
        value = raw[1:-1].replace("''", "'")
        if not value.strip():
            failures.append(f"{where}: value must be one nonblank YAML string")
            return None
        return value
    return raw


def _frontmatter(text: str, path: Path) -> tuple[dict[str, str], str, list[str]]:
    failures: list[str] = []
    lines = text.splitlines()
    where = path.as_posix()
    if not lines or lines[0].strip() != "---":
        return {}, text, [f"{where}: missing frontmatter"]
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, text, [f"{where}: unterminated frontmatter"]

    values: dict[str, str] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        match = KEY_RE.fullmatch(line)
        if not match:
            failures.append(f"{where}:{index + 1}: malformed top-level frontmatter")
            index += 1
            continue
        key, raw = match.group(1), (match.group(2) or "")
        if key in values:
            failures.append(f"{where}:{index + 1}: duplicate frontmatter key '{key}'")
        if raw in {">", ">-", "|", "|-"}:
            chunks = []
            index += 1
            while index < end and (lines[index].startswith((" ", "\t")) or not lines[index]):
                chunks.append(lines[index].strip())
                index += 1
            value = " ".join(chunk for chunk in chunks if chunk)
            values[key] = value
            continue
        values[key] = raw.strip()
        index += 1

    unknown = sorted(set(values) - ALLOWED_KEYS)
    if unknown:
        failures.append(f"{where}: unknown frontmatter key(s): {', '.join(unknown)}")
    body = "\n".join(lines[end + 1 :])
    return values, body, failures


def _check_skill_frontmatter(path: Path, text: str) -> tuple[str, list[str]]:
    values, body, failures = _frontmatter(text, path)
    where = path.as_posix()
    expected_name = path.parent.name
    name = _yaml_string(values.get("name", ""), f"{where}: name", failures)
    if name and (not NAME_RE.fullmatch(name) or name != expected_name):
        failures.append(
            f"{where}: name must be kebab-case and equal directory '{expected_name}'"
        )
    description = _yaml_string(
        values.get("description", ""), f"{where}: description", failures
    )
    if description:
        if len(description.encode("utf-8")) > 600:
            failures.append(f"{where}: description exceeds 600 UTF-8 bytes")
        if "Triggers:" not in description:
            failures.append(f"{where}: description is missing literal 'Triggers:'")
        else:
            trigger_text = description.split("Triggers:", 1)[1]
            triggers = re.findall(r"(['\"])(.+?)\1", trigger_text)
            if not 2 <= len(triggers) <= 4:
                failures.append(f"{where}: Triggers must contain 2-4 quoted user phrasings")
    if "argument-hint" in values:
        _yaml_string(values["argument-hint"], f"{where}: argument-hint", failures)
    if "compatibility" in values:
        _yaml_string(values["compatibility"], f"{where}: compatibility", failures)
    if "disable-model-invocation" in values:
        raw = values["disable-model-invocation"]
        if raw != "true":
            failures.append(f"{where}: disable-model-invocation must be boolean true")
        if expected_name not in MANUAL_ONLY:
            failures.append(
                f"{where}: only pcf-deploy and service-onboarding may disable model invocation"
            )
    return body, failures


def _links(text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2).strip()) for match in LINK_RE.finditer(text)]


def _target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split()[0]


def _relative_target(raw: str) -> str | None:
    target = unquote(_target(raw))
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith(("/", "\\")):
        return None
    return target.split("#", 1)[0].split("?", 1)[0]


def _check_markdown(path: Path, text: str) -> list[str]:
    failures = []
    visible = _strip_fences(text)
    without_links = LINK_RE.sub("", visible)
    for match in CODE_PATH_RE.finditer(without_links):
        line = visible[: match.start()].count("\n") + 1
        failures.append(
            f"{path.as_posix()}:{line}: code-span pointer must be a Markdown link: {match.group(1)}"
        )
    for _label, raw_target in _links(visible):
        relative = _relative_target(raw_target)
        if relative is None:
            continue
        destination = path.parent / Path(relative.replace("/", os.sep))
        if not destination.exists():
            failures.append(
                f"{path.as_posix()}: dead link '{relative}'"
            )
    return failures


def _bundle_files(skill_root: Path):
    for kind in ("references", "assets", "scripts"):
        base = skill_root / kind
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                yield path


def _check_direct_bundle_links(skill_path: Path, body: str) -> list[str]:
    failures = []
    skill_root = skill_path.parent
    visible = _strip_fences(body)
    links = _links(visible)
    resolved = set()
    searchable = []
    for label, raw_target in links:
        relative = _relative_target(raw_target)
        searchable.append((label.replace("\\", "/"), _target(raw_target).replace("\\", "/")))
        if relative is not None:
            try:
                resolved.add((skill_path.parent / relative).resolve().relative_to(skill_root.resolve()).as_posix())
            except ValueError:
                pass
    for bundle in _bundle_files(skill_root):
        relative = bundle.relative_to(skill_root).as_posix()
        if relative in resolved:
            continue
        if any(relative in label or relative in target for label, target in searchable):
            continue
        failures.append(
            f"{skill_path.as_posix()}: bundled file not linked directly from SKILL.md body: {relative}"
        )
    return failures


def check(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    failures: list[str] = []
    skill_root = root / "skills"
    if skill_root.is_dir():
        for skill_path in sorted(skill_root.glob("*/SKILL.md")):
            try:
                text = skill_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                failures.append(f"{skill_path.as_posix()}: cannot read UTF-8: {exc}")
                continue
            body, frontmatter_failures = _check_skill_frontmatter(skill_path, text)
            failures.extend(frontmatter_failures)
            failures.extend(_check_markdown(skill_path, body))
            failures.extend(_check_direct_bundle_links(skill_path, body))
            references = skill_path.parent / "references"
            if references.is_dir():
                for reference in sorted(references.rglob("*.md")):
                    try:
                        failures.extend(
                            _check_markdown(reference, reference.read_text(encoding="utf-8"))
                        )
                    except (OSError, UnicodeError) as exc:
                        failures.append(f"{reference.as_posix()}: cannot read UTF-8: {exc}")
    command_root = root / "canonical" / "commands"
    if command_root.is_dir():
        for command in sorted(command_root.glob("*.md")):
            try:
                failures.extend(_check_markdown(command, command.read_text(encoding="utf-8")))
            except (OSError, UnicodeError) as exc:
                failures.append(f"{command.as_posix()}: cannot read UTF-8: {exc}")
    return failures


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("check_links: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("check_links: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
