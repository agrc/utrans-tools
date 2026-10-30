from importlib.metadata import version
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import utrans
from utrans import cli, detect_changes, etl
from utrans.etl import _county_boundary_name
from utrans.etl_common import direction, parse_full_address, resolve_domain_value
from utrans.etl_handlers import HANDLERS
from utrans.profiles import load_profiles


@pytest.mark.parametrize(
    ("command", "options", "invalid_option"),
    [
        ("etl", ("--source-features", "--utrans-roads", "--county-boundaries"), option)
        for option in ("--source-features", "--utrans-roads", "--county-boundaries")
    ]
    + [
        (
            "detect-changes",
            ("--update-features", "--utrans-features", "--append-target"),
            option,
        )
        for option in ("--update-features", "--utrans-features", "--append-target")
    ],
)
@pytest.mark.parametrize(
    "invalid_type", [None, "Workspace", "FeatureDataset", "Table", "unreadable"]
)
def test_feature_class_options_fail_before_processing(
    monkeypatch, capsys, command, options, invalid_option, invalid_type
):
    invalid_path = r"C:\data\invalid.gdb"
    monkeypatch.setattr(
        etl.arcpy,
        "Exists",
        Mock(side_effect=lambda path: path != invalid_path or invalid_type is not None),
    )

    def describe(path):
        if path == invalid_path and invalid_type == "unreadable":
            raise OSError("Cannot read dataset")
        return SimpleNamespace(
            dataType=invalid_type if path == invalid_path else "FeatureClass"
        )

    monkeypatch.setattr(etl.arcpy, "Describe", describe)
    workspace = Mock()
    check_license = Mock()
    run_detection = Mock()
    monkeypatch.setattr(etl, "get_output_workspace", workspace)
    monkeypatch.setattr(
        detect_changes, "ensure_detect_feature_changes_license", check_license
    )
    monkeypatch.setattr(detect_changes, "run_detect_changes", run_detection)
    arguments = [command, "--county", "saltlake"]
    for option in options:
        arguments.extend(
            [
                option,
                invalid_path
                if option == invalid_option
                else rf"C:\data\roads.gdb\{option[2:]}",
            ]
        )

    assert cli.main(arguments) == 2

    output = capsys.readouterr().out
    assert invalid_option in output
    assert invalid_path in output
    assert "feature class" in output
    if invalid_type == "unreadable":
        assert "Cannot read dataset" in output
    workspace.assert_not_called()
    check_license.assert_not_called()
    run_detection.assert_not_called()


def test_detect_changes_accepts_feature_class_options(monkeypatch):
    monkeypatch.setattr(detect_changes.arcpy, "Exists", Mock(return_value=True))
    monkeypatch.setattr(
        detect_changes.arcpy,
        "Describe",
        Mock(return_value=SimpleNamespace(dataType="FeatureClass")),
    )
    check_license = Mock()
    run = Mock()
    monkeypatch.setattr(
        detect_changes, "ensure_detect_feature_changes_license", check_license
    )
    monkeypatch.setattr(detect_changes, "run_detect_changes", run)

    assert (
        cli.main(
            [
                "detect-changes",
                "--county",
                "saltlake",
                "--update-features",
                "update",
                "--utrans-features",
                "utrans",
                "--append-target",
                "target",
            ]
        )
        == 0
    )

    check_license.assert_called_once_with()
    run.assert_called_once_with("update", "utrans", "49035", "target")


def test_package_version_comes_from_distribution_metadata():
    assert utrans.__version__ == version("ugrc-utrans-tools")


def test_version(capsys):
    assert cli.main(["--version"]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"utrans {utrans.__version__}\n"


@pytest.mark.parametrize(
    ("command", "main_name"),
    [
        ("detect-changes", "detect_changes_main"),
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
    assert "--search-distance" not in captured.out
    assert "--match-fields" not in captured.out
    assert "--change-tolerance" not in captured.out
    assert "--compare-fields" not in captured.out
    assert "--dfc-output-name" not in captured.out
    assert "--stats-table-name" not in captured.out
    assert "--recents-name" not in captured.out


def test_etl_help(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["etl", "--help"])

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert "utrans etl" in captured.out
    assert "--source-features" in captured.out
    assert "--county-boundaries" in captured.out
    assert "--output-workspace" not in captured.out


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
