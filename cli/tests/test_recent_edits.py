from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from utrans import recent_edits


@pytest.mark.parametrize("option", ["--update-features", "--base-features"])
@pytest.mark.parametrize("data_type", [None, "Workspace", "FeatureDataset", "Table"])
def test_main_rejects_invalid_feature_class_before_processing(
    monkeypatch, capsys, option, data_type
):
    invalid_path = r"C:\roads\invalid.gdb"
    exists = Mock(
        side_effect=lambda path: path != invalid_path or data_type is not None
    )
    describe = Mock(
        side_effect=lambda path: SimpleNamespace(
            dataType=data_type if path == invalid_path else "FeatureClass"
        )
    )
    check_license = Mock()
    run = Mock()
    monkeypatch.setattr(recent_edits.arcpy, "Exists", exists)
    monkeypatch.setattr(recent_edits.arcpy, "Describe", describe)
    monkeypatch.setattr(
        recent_edits, "ensure_detect_feature_changes_license", check_license
    )
    monkeypatch.setattr(recent_edits, "run_change_detection", run)
    arguments = {
        "--update-features": r"C:\roads\update.gdb\Roads",
        "--base-features": r"C:\roads\base.gdb\Roads",
    }
    arguments[option] = invalid_path

    assert (
        recent_edits.main(
            ["--county", "saltlake"]
            + [value for pair in arguments.items() for value in pair]
        )
        == 2
    )

    output = capsys.readouterr().out
    assert option in output
    assert invalid_path in output
    assert "feature class" in output
    if data_type is None:
        assert "does not exist or is not accessible" in output
        assert all(call.args != (invalid_path,) for call in describe.call_args_list)
    else:
        assert data_type in output
        assert "not just a geodatabase or feature dataset" in output
    check_license.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize(
    "error_type", [OSError, RuntimeError, recent_edits.arcpy.ExecuteError]
)
def test_main_reports_unreadable_feature_class(monkeypatch, capsys, error_type):
    path = r"C:\roads\update.gdb\Roads"
    monkeypatch.setattr(recent_edits.arcpy, "Exists", Mock(return_value=True))
    monkeypatch.setattr(
        recent_edits.arcpy,
        "Describe",
        Mock(side_effect=error_type("Cannot read dataset")),
    )
    run = Mock()
    monkeypatch.setattr(recent_edits, "run_change_detection", run)

    assert (
        recent_edits.main(
            [
                "--county",
                "saltlake",
                "--update-features",
                path,
                "--base-features",
                "base",
            ]
        )
        == 2
    )

    output = capsys.readouterr().out
    assert "--update-features" in output
    assert path in output
    assert "Cannot read dataset" in output
    run.assert_not_called()


def test_main_accepts_feature_classes(monkeypatch):
    update = r"C:\roads\update.gdb\Roads"
    base = r"C:\roads\base.gdb\Transportation\Roads"
    monkeypatch.setattr(recent_edits.arcpy, "Exists", Mock(return_value=True))
    monkeypatch.setattr(
        recent_edits.arcpy,
        "Describe",
        Mock(return_value=SimpleNamespace(dataType="FeatureClass")),
    )
    check_license = Mock()
    run = Mock()
    monkeypatch.setattr(
        recent_edits, "ensure_detect_feature_changes_license", check_license
    )
    monkeypatch.setattr(recent_edits, "run_change_detection", run)

    assert (
        recent_edits.main(
            [
                "--county",
                "saltlake",
                "--update-features",
                update,
                "--base-features",
                base,
            ]
        )
        == 0
    )

    check_license.assert_called_once_with()
    assert run.call_args.kwargs["update_features"] == update
    assert run.call_args.kwargs["base_features"] == base


def _profile_fields(*names):
    return {name.lower(): name for name in names}


def test_ensure_configured_fields_accepts_case_insensitive_matches(monkeypatch):
    feature_fields = {
        "update": _profile_fields("RoadName", "LeftFrom"),
        "base": _profile_fields("ROADNAME", "LEFTFROM"),
    }
    monkeypatch.setattr(
        recent_edits,
        "get_field_name_map",
        lambda feature_class: feature_fields[feature_class],
    )

    recent_edits.ensure_configured_fields(
        "update",
        "base",
        ("roadname roadname", "LeftFrom leftfrom"),
    )


@pytest.mark.parametrize(
    ("missing_dataset", "expected_message"),
    [
        ("update", "Update features are missing configured fields: LeftFrom"),
        ("base", "Base features are missing configured fields: LeftFrom"),
    ],
)
def test_ensure_configured_fields_reports_missing_mapping_fields(
    monkeypatch, missing_dataset, expected_message
):
    feature_fields = {
        "update": _profile_fields("RoadName")
        if missing_dataset == "update"
        else _profile_fields("RoadName", "LeftFrom"),
        "base": _profile_fields("ROADNAME")
        if missing_dataset == "base"
        else _profile_fields("ROADNAME", "LEFTFROM"),
    }
    monkeypatch.setattr(
        recent_edits,
        "get_field_name_map",
        lambda feature_class: feature_fields[feature_class],
    )

    with pytest.raises(RuntimeError, match=expected_message):
        recent_edits.ensure_configured_fields(
            "update", "base", ("RoadName RoadName", "LeftFrom LeftFrom")
        )


def test_recent_edits_profile_no_longer_exposes_required_fields():
    profile = recent_edits._load_profiles()["davis"]

    assert not hasattr(profile, "required_fields")
