from importlib.metadata import version

import pytest

import utrans
from utrans import cli
from utrans.etl_common import direction, parse_full_address, resolve_domain_value
from utrans.profiles import load_profiles


def test_package_version_comes_from_distribution_metadata():
    assert utrans.__version__ == version("ugrc-utrans-tools")


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


def test_saltlake_profile_replaces_vecc():
    profiles = load_profiles()

    assert profiles["saltlake"].require("fips") == "49035"
    assert "vecc" not in profiles


def test_every_profile_has_field_mappings():
    assert all(profile.get("field_mappings") for profile in load_profiles().values())


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
