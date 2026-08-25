from importlib.metadata import version
from unittest.mock import Mock

import pytest

import utrans
from utrans import cli
from utrans.etl import _county_boundary_name
from utrans.etl_common import direction, parse_full_address, resolve_domain_value
from utrans.etl_handlers import HANDLERS
from utrans.profiles import load_profiles


def test_package_version_comes_from_distribution_metadata():
    assert utrans.__version__ == version("ugrc-utrans-tools")


def test_version(capsys):
    assert cli.main(["--version"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"utrans {utrans.__version__}\n"


@pytest.mark.parametrize(
    ("command", "main_name"),
    [
        ("get-recent-edits", "recent_edits_main"),
        ("etl", "etl_main"),
    ],
)
def test_subcommands_print_version_banner(monkeypatch, capsys, command, main_name):
    subcommand_main = Mock(return_value=0)
    monkeypatch.setattr(cli, main_name, subcommand_main)

    assert cli.main([command, "--example-option"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"utrans {utrans.__version__}\n"
    subcommand_main.assert_called_once_with(
        ["--example-option"], prog=f"utrans {command}"
    )


def test_get_recent_edits_help(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["get-recent-edits", "--help"])

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert "utrans get-recent-edits" in captured.out
    assert "--update-features" in captured.out


def test_etl_help(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["etl", "--help"])

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert "utrans etl" in captured.out
    assert "--source-features" in captured.out
    assert "--county-boundaries" in captured.out


@pytest.mark.parametrize(
    ("county", "expected"),
    [
        ("davis", "DAVIS"),
        ("boxelder", "BOX ELDER"),
        ("saltlake", "SALT LAKE"),
        ("sanjuan", "SAN JUAN"),
    ],
)
def test_county_boundary_name_is_uppercase(county, expected):
    assert _county_boundary_name(county) == expected


def test_saltlake_profile_replaces_vecc():
    profiles = load_profiles()

    assert profiles["saltlake"].require("fips") == "49035 - Salt Lake"
    assert "vecc" not in profiles


def test_every_profile_has_field_mappings():
    assert all(profile.get("field_mappings") for profile in load_profiles().values())


def test_profile_handlers_are_registered():
    handlers = {
        profile.get("custom_handler")
        for profile in load_profiles().values()
        if profile.get("custom_handler")
    }

    assert handlers <= HANDLERS.keys()


def test_legacy_address_helpers():
    parsed = parse_full_address("North 1200 West", {"RD"})

    assert parsed is not None
    assert parsed.predir == "N"
    assert parsed.name == "1200"
    assert parsed.postdir == "W"
    assert direction("SOUTH") == "S"
    assert resolve_domain_value("way", {"WAY": "WAY"}) == "WAY"


def test_parse_full_address_handles_posttype_aliases():
    parsed = parse_full_address("West Center Drive", {"DR", "DRIVE"})

    assert parsed is not None
    assert parsed.predir == "W"
    assert parsed.name == "CENTER"
    assert parsed.posttype == "DRIVE"
