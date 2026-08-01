# commitpreflight

Pre-flight lint for commit messages written by AI coding agents.

Your agent writes a commit message, calls `git commit`, gets rejected by a hook, and burns a
turn rewriting it. `commitpreflight` catches the message *before* the commit, and returns a
concrete fix rather than a complaint.

```bash
pip install commitpreflight
```

```bash
$ echo "Added retry budget to the upload path so that flaky networks recover." | commitpreflight
error: header is not `tag(scope): subject` — got: 'Added retry budget to the upload path so' [conventional-format]
  try: feat(scope): added retry budget to the upload path so that flaky networks recover.
error: subject must not end with a period [subject-punctuation]
  try: Added retry budget to the upload path so that flaky networks recover
warning: subject opens with 'added'; conventional commits use the imperative [imperative-mood]
  try: add retry budget to the upload path so that flaky networks recover.
```

## Why these rules

The rule set is not a style opinion. It is seeded by what actually breaks: **10,976 CLI
failures logged over 7 days by a fleet of autonomous coding agents.** Roughly **1 in 5 was a
malformed commit message** — the single largest class of agent CLI failure in the corpus.

| failure | share of all agent CLI failures |
| --- | --- |
| subject over the length limit | 13.8% |
| missing `tag(scope):` format | 8.1% |

The useful detail is the shape of the overshoot, not its existence:

| how far over the 72-char limit | share of overshoots |
| --- | --- |
| 1–5 chars | 57% |
| 6–10 chars | 24% |
| 11+ chars | 19% |

**81% of overshoots miss by 10 characters or fewer.** Agents do not write essays into the
subject line; they miss the limit by a hair. So the right intervention is a trim at the last
word boundary, which is what `commitpreflight` suggests — and why it declines to suggest one
when the overshoot is large enough that trimming would be a rewrite.

## Use it as a git hook

```bash
printf '#!/bin/sh\nexec commitpreflight "$1"\n' > .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Exit code is `1` when any error-severity finding fires, `0` otherwise. `--strict` makes
warnings blocking too.

## Use it from an agent

`--json` gives a machine-readable list your agent can act on without parsing prose:

```bash
$ commitpreflight --json .git/COMMIT_EDITMSG
[
  {
    "rule": "imperative-mood",
    "severity": "warning",
    "message": "subject opens with 'added'; conventional commits use the imperative",
    "fix": "add retry budget to the upload path"
  }
]
```

Or call it directly:

```python
from commitpreflight import check

for finding in check("feat(api): Added a thing."):
    print(finding.rule, finding.severity, finding.fix)
```

## Rules

| rule | severity | what it catches |
| --- | --- | --- |
| `empty` | error | no message at all |
| `conventional-format` | error | header is not `tag(scope): subject` |
| `tag-case` | error | tag is not lowercase |
| `tag-unknown` | error | tag outside the allowed set |
| `scope-required` | error | scope missing when required |
| `scope-empty` | error | `tag(): subject` |
| `subject-empty` | error | nothing after the tag |
| `subject-length` | error | header over the limit |
| `subject-punctuation` | error | subject ends with a period |
| `body-blank-line` | error | body not separated from the subject |
| `imperative-mood` | warning | `added` / `fixing` / `updates` openers |
| `subject-case` | warning | subject starts capitalised |
| `body-line-length` | warning | wrappable body line over the limit |

## Configuration

Optional, in `pyproject.toml`:

```toml
[tool.commitpreflight]
max_subject = 72
max_body_line = 100
require_conventional = true
require_scope = false
allow_unknown_tags = false
tags = ["feat", "fix", "docs", "refactor", "test", "chore"]
disable = ["subject-case"]
```

## Teams

Running `commitpreflight` across a fleet of AI agents at scale? Team subscription: $100/mo.

→ [Subscribe](https://buy.stripe.com/28EbJ1fxggKX8U0e11gfu00)

## License

MIT
