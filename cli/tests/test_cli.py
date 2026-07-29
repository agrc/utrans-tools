from importlib.metadata import version

import pytest

import utrans
from utrans import cli


def test_package_version_comes_from_distribution_metadata():
    assert utrans.__version__ == version("ugrc-utrans-tools")


def test_get_recent_edits_help(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["get-recent-edits", "--help"])

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert "utrans get-recent-edits" in captured.out
    assert "--update-features" in captured.out
