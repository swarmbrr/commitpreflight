"""Config loading must degrade, never crash, when no TOML parser is importable.

`tomllib` is stdlib only from 3.11. On 3.9/3.10 the `tomli` backport is a declared
dependency, but a user can still land in an environment without either -- and config
files are optional, so that must cost them the config, not the tool.
"""

from pathlib import Path

from commitpreflight import cli
from commitpreflight.rules import Config


def test_load_config_returns_defaults_without_a_toml_parser(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.commitpreflight]\nmax_subject = 20\n"
    )
    monkeypatch.setattr(cli, "tomllib", None)

    assert cli.load_config(tmp_path) == Config()


def test_load_config_reads_the_table_when_a_parser_is_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.commitpreflight]\nmax_subject = 20\n"
    )

    assert cli.load_config(Path(tmp_path)).max_subject == 20
