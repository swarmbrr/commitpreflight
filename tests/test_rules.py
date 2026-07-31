import pytest

from commitpreflight.rules import Config, check


def rules(message, config=None):
    return {f.rule for f in check(message, config)}


def fix_for(message, rule, config=None):
    return next(f.fix for f in check(message, config) if f.rule == rule)


def test_clean_message_passes():
    assert check("feat(api): add retry budget to the upload path") == []


def test_clean_message_with_body_passes():
    assert (
        check("fix(cli): handle empty stdin\n\nThe parser assumed a trailing newline.")
        == []
    )


def test_scopeless_conventional_header_passes():
    assert check("chore: drop the unused lockfile") == []


def test_empty_message():
    assert "empty" in rules("")
    assert "empty" in rules("\n\n#comment\n")


def test_missing_conventional_format():
    assert "conventional-format" in rules("first pass at the parser")


def test_conventional_format_optional():
    assert check("first pass at the parser", Config(require_conventional=False)) == []


def test_unknown_and_uppercase_tags():
    assert "tag-unknown" in rules("wip(api): hold this")
    assert "tag-case" in rules("Feat(api): add a thing")
    assert check("wip(api): hold this", Config(allow_unknown_tags=True)) == []


def test_scope_rules():
    assert "scope-required" in rules("feat: add a thing", Config(require_scope=True))
    assert "scope-empty" in rules("feat(): add a thing")


@pytest.mark.parametrize("over", [1, 5, 11, 60])
def test_subject_length_flags_any_overshoot(over):
    header = "feat(api): " + "x" * (72 - 11 + over)
    findings = [f for f in check(header) if f.rule == "subject-length"]
    assert len(findings) == 1
    assert f"{over} over" in findings[0].message


def test_subject_length_boundary_is_inclusive():
    assert "subject-length" not in rules("feat(api): " + "x" * 61)  # exactly 72


def test_small_overshoot_yields_a_word_boundary_trim():
    # The dominant real-world case: over by a hair, so a trim is enough.
    header = "feat(api): add a retry budget to the streaming upload path today"
    header += " plus more"  # pushes it past 72 by a few chars
    fix = fix_for(header, "subject-length")
    assert fix is not None
    assert len(fix) <= 72
    assert not fix.endswith(" ")
    assert header.startswith(fix)


def test_huge_overshoot_offers_no_trim_because_it_would_be_a_rewrite():
    assert fix_for("feat(api): " + "word " * 80, "subject-length") is None


def test_trailing_period():
    findings = check("feat(api): add a retry budget.")
    assert [f.rule for f in findings] == ["subject-punctuation"]
    assert findings[0].fix == "add a retry budget"


def test_imperative_mood_suggests_the_verb():
    assert (
        fix_for("feat(api): added a retry budget", "imperative-mood")
        == "add a retry budget"
    )
    assert fix_for("fix(cli): Fixing the parser", "imperative-mood") == "fix the parser"


def test_subject_case_warns_but_acronyms_do_not():
    assert "subject-case" in rules("feat(api): Add a retry budget")
    assert "subject-case" not in rules("feat(api): API keys now rotate")


def test_imperative_takes_precedence_over_case():
    assert "subject-case" not in rules("feat(api): Added a retry budget")


def test_body_must_be_separated_by_a_blank_line():
    assert "body-blank-line" in rules("feat(api): add a thing\nand here is why")


def test_body_line_length_warns_once():
    body = "wrap me " * 15  # wrappable: the unbreakable-line exemption must not apply
    findings = [
        f
        for f in check(f"feat(api): add a thing\n\n{body}\n{body}")
        if f.rule == "body-line-length"
    ]
    assert len(findings) == 1


def test_unbreakable_body_line_is_not_flagged():
    # A long URL or hash cannot be wrapped; flagging it is noise.
    assert check("feat(api): add a thing\n\nhttps://example.com/" + "u" * 120) == []


def test_git_comment_lines_are_ignored():
    assert check("feat(api): add a thing\n# Please enter the commit message\n") == []


def test_disabled_rules_are_suppressed():
    config = Config(disabled=frozenset({"subject-length"}))
    assert "subject-length" not in rules("feat(api): " + "x" * 200, config)


def test_severity_split():
    findings = {f.rule: f.severity for f in check("feat(api): Added a thing.")}
    assert findings["subject-punctuation"] == "error"
    assert findings["imperative-mood"] == "warning"


def test_conventional_fix_preserves_the_whole_header():
    header = "Added a retry budget to the streaming upload path so flaky networks recover well"
    fix = fix_for(header, "conventional-format")
    assert fix.endswith("recover well")
    assert "added a retry budget" in fix
