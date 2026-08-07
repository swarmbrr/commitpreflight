"""Command line entry point: `commitpreflight [MESSAGE_FILE]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # stdlib from 3.11; `tomli` is the declared backport on 3.9/3.10
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only reachable on <3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

from commitpreflight import __version__
from commitpreflight.rules import DEFAULT_TAGS, Config, check


def load_config(start: Path | None = None) -> Config:
    """Read [tool.commitpreflight] from the nearest pyproject.toml walking upward."""
    if tomllib is None:
        return Config()
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        candidate = directory / "pyproject.toml"
        if not candidate.is_file():
            continue
        try:
            table = (
                tomllib.loads(candidate.read_text())
                .get("tool", {})
                .get("commitpreflight")
            )
        except (OSError, tomllib.TOMLDecodeError):
            return Config()
        if not table:
            return Config()
        return Config(
            max_subject=int(table.get("max_subject", 72)),
            max_body_line=int(table.get("max_body_line", 100)),
            tags=tuple(table.get("tags", DEFAULT_TAGS)),
            require_conventional=bool(table.get("require_conventional", True)),
            require_scope=bool(table.get("require_scope", False)),
            allow_unknown_tags=bool(table.get("allow_unknown_tags", False)),
            disabled=frozenset(table.get("disable", ())),
        )
    return Config()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="commitpreflight",
        description="Lint a commit message before you commit it.",
    )
    parser.add_argument(
        "message_file",
        nargs="?",
        help="file holding the message (git passes .git/COMMIT_EDITMSG); omit to read stdin",
    )
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero on warnings as well as errors",
    )
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.message_file:
        path = Path(args.message_file)
        if not path.is_file():
            print(f"commitpreflight: no such file: {path}", file=sys.stderr)
            return 2
        message = path.read_text(encoding="utf-8", errors="replace")
        config = load_config(path.resolve().parent)
    else:
        message = sys.stdin.read()
        config = load_config()

    findings = check(message, config)

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "rule": f.rule,
                        "severity": f.severity,
                        "message": f.message,
                        "fix": f.fix,
                    }
                    for f in findings
                ],
                indent=2,
            )
        )
    else:
        for finding in findings:
            print(finding, file=sys.stderr)

    blocking = [f for f in findings if f.severity == "error" or args.strict]
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
