"""Commit message rules, ordered by measured failure prevalence in AI-agent commits.

Prevalence figures in each rule's docstring come from 10,976 CLI failures logged over
7 days by a fleet of autonomous coding agents. They are why the defaults are what they
are -- not style preference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CONVENTIONAL = re.compile(
    r"^(?P<tag>[a-zA-Z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<subject>.*)$"
)

DEFAULT_TAGS = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

# Past-tense / gerund openers agents reach for instead of the imperative.
NON_IMPERATIVE = {
    "added": "add",
    "adds": "add",
    "adding": "add",
    "fixed": "fix",
    "fixes": "fix",
    "fixing": "fix",
    "updated": "update",
    "updates": "update",
    "updating": "update",
    "removed": "remove",
    "removes": "remove",
    "removing": "remove",
    "changed": "change",
    "changes": "change",
    "changing": "change",
    "created": "create",
    "creates": "create",
    "creating": "create",
    "implemented": "implement",
    "implements": "implement",
    "implementing": "implement",
    "refactored": "refactor",
    "refactors": "refactor",
    "refactoring": "refactor",
    "moved": "move",
    "moves": "move",
    "moving": "move",
    "renamed": "rename",
    "renames": "rename",
    "renaming": "rename",
    "deleted": "delete",
    "deletes": "delete",
    "deleting": "delete",
    "bumped": "bump",
    "bumps": "bump",
    "bumping": "bump",
}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # "error" | "warning"
    message: str
    fix: str | None = None

    def __str__(self) -> str:
        line = f"{self.severity}: {self.message} [{self.rule}]"
        return f"{line}\n  try: {self.fix}" if self.fix else line


@dataclass(frozen=True)
class Config:
    max_subject: int = 72
    max_body_line: int = 100
    tags: tuple[str, ...] = DEFAULT_TAGS
    require_conventional: bool = True
    require_scope: bool = False
    allow_unknown_tags: bool = False
    disabled: frozenset[str] = field(default_factory=frozenset)


def _trim_to(subject: str, limit: int) -> str | None:
    """Longest whole-word prefix of subject that fits in limit, or None if that loses too much."""
    if len(subject) <= limit:
        return None
    cut = subject[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    # Measured against the original, not the limit: discarding a third of what the author
    # wrote is a rewrite, and suggesting it as a "trim" silently drops meaning.
    return cut if cut and len(cut) >= len(subject) * 0.66 else None


def check(message: str, config: Config | None = None) -> list[Finding]:
    """Lint a commit message. Empty list means it will pass a conventional-commit gate."""
    cfg = config or Config()
    out: list[Finding] = []

    def add(rule: str, severity: str, msg: str, fix: str | None = None) -> None:
        if rule not in cfg.disabled:
            out.append(Finding(rule, severity, msg, fix))

    lines = message.replace("\r\n", "\n").split("\n")
    # Comment lines are stripped by git before the message is stored.
    lines = [ln for ln in lines if not ln.startswith("#")]
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines or not lines[0].strip():
        add("empty", "error", "commit message is empty")
        return out

    header = lines[0].rstrip()
    match = CONVENTIONAL.match(header)
    subject = match.group("subject") if match else header

    if not match:
        if cfg.require_conventional:
            add(
                "conventional-format",
                "error",
                f"header is not `tag(scope): subject` — got: {header[:40]!r}",
                # Truncate what we complain about, never what we suggest: a shortened
                # repair silently deletes the author's words.
                f"{cfg.tags[0]}(scope): {header[:1].lower()}{header[1:]}",
            )
    else:
        tag = match.group("tag")
        if tag != tag.lower():
            add("tag-case", "error", f"tag {tag!r} must be lowercase", tag.lower())
        elif not cfg.allow_unknown_tags and tag not in cfg.tags:
            add(
                "tag-unknown",
                "error",
                f"unknown tag {tag!r}; allowed: {', '.join(cfg.tags)}",
            )
        if cfg.require_scope and match.group("scope") is None:
            add(
                "scope-required",
                "error",
                "scope is required — use `tag(scope): subject`",
            )
        if match.group("scope") == "":
            add("scope-empty", "error", "scope parentheses are empty")

    if not subject.strip():
        add("subject-empty", "error", "subject is empty after the tag")
        return out

    # Highest-prevalence failure class: 1,516 of 10,976 (13.8%). 81% of these overshoot
    # by <=10 chars and 57% by <=5, so the actionable fix is a trim, never a rewrite.
    if len(header) > cfg.max_subject:
        over = len(header) - cfg.max_subject
        trimmed = _trim_to(header, cfg.max_subject)
        add(
            "subject-length",
            "error",
            f"subject is {len(header)} chars, {over} over the {cfg.max_subject} limit",
            trimmed,
        )

    if subject.endswith("."):
        add(
            "subject-punctuation",
            "error",
            "subject must not end with a period",
            subject.rstrip("."),
        )

    first = subject.split(" ", 1)[0].strip().lower()
    if first in NON_IMPERATIVE:
        imperative = NON_IMPERATIVE[first]
        rest = subject.split(" ", 1)[1] if " " in subject else ""
        add(
            "imperative-mood",
            "warning",
            f"subject opens with {first!r}; conventional commits use the imperative",
            f"{imperative} {rest}".strip(),
        )
    elif subject[:1].isupper() and not subject.split(" ", 1)[0].isupper():
        add(
            "subject-case",
            "warning",
            "subject starts with a capital letter",
            subject[0].lower() + subject[1:],
        )

    if len(lines) > 1 and lines[1].strip():
        add(
            "body-blank-line",
            "error",
            "body must be separated from the subject by a blank line",
        )

    for i, line in enumerate(lines[2:], start=3):
        if len(line) > cfg.max_body_line and " " in line.strip():
            add(
                "body-line-length",
                "warning",
                f"body line {i} is {len(line)} chars, over the {cfg.max_body_line} limit",
            )
            break

    return out
