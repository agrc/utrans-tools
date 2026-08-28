import os
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from utrans import detect_changes
from utrans.utilities import get_output_workspace


def _cursor(rows):
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.__iter__.return_value = iter(rows)
    return cursor


def test_extract_fips_from_profile_value():
    assert detect_changes.extract_fips("49035 - Salt Lake") == "49035"
    assert detect_changes.extract_fips("56041 - Uinta") == "56041"


def test_parser_does_not_require_county_field_configuration():
    parser = detect_changes.build_parser()

    actions = {action.dest for action in parser._actions}

    assert "required_fields" not in actions
    assert "match_fields" not in actions
    assert "compare_fields" not in actions
    assert "base_features" not in actions
    assert "search_distance" not in actions
    assert "change_tolerance" not in actions
    assert "dfc_output_name" not in actions
    assert "stats_table_name" not in actions
    assert "test_output_name" not in actions
    assert "append_target" in actions
    assert "utrans_features" in actions
    assert "output_workspace" not in actions


@pytest.mark.parametrize(
    ("feature_class", "descriptions", "expected"),
    [
        (
            r"C:\data\roads.gdb\roads",
            [
                SimpleNamespace(catalogPath=r"C:\data\roads.gdb\roads"),
                SimpleNamespace(),
            ],
            r"C:\data\roads.gdb",
        ),
        (
            r"C:\data\roads.gdb\transportation\roads",
            [
                SimpleNamespace(catalogPath=r"C:\data\roads.gdb\transportation\roads"),
                SimpleNamespace(datasetType="FeatureDataset"),
            ],
            r"C:\data\roads.gdb",
        ),
    ],
)
def test_get_output_workspace_returns_containing_geodatabase(
    monkeypatch, feature_class, descriptions, expected
):
    monkeypatch.setattr(
        detect_changes.arcpy, "Describe", Mock(side_effect=descriptions)
    )

    assert get_output_workspace(feature_class) == expected


def test_add_dfc_fields_creates_legacy_fields_and_populates_metadata(monkeypatch):
    add_field = Mock()
    update_cursor = _cursor([[None, None]])
    monkeypatch.setattr(detect_changes.arcpy, "ListFields", Mock(return_value=[]))
    monkeypatch.setattr(detect_changes.arcpy.management, "AddField", add_field)
    monkeypatch.setattr(
        detect_changes.arcpy.da, "UpdateCursor", Mock(return_value=update_cursor)
    )

    detect_changes.add_dfc_fields("dfc", "49035")

    assert [call.args[:3] for call in add_field.call_args_list] == [
        ("dfc", "CURRENT_NOTES", "TEXT"),
        ("dfc", "PREV__NOTES", "TEXT"),
        ("dfc", "EDITOR", "TEXT"),
        ("dfc", "EDIT_DATE", "DATE"),
        ("dfc", "DATE_ADDED", "DATE"),
        ("dfc", "COFIPS", "TEXT"),
    ]
    assert update_cursor.__iter__.return_value is not None
    assert update_cursor.updateRow.call_count == 1
    assert update_cursor.updateRow.call_args.args[0][1] == "49035"


def test_run_detect_changes_uses_shared_filter_and_appends_to_utrans(monkeypatch):
    management = detect_changes.arcpy.management
    make_feature_layer = Mock()
    copy_features = Mock()
    append = Mock()
    detect_feature_changes = Mock()
    monkeypatch.setattr(management, "MakeFeatureLayer", make_feature_layer)
    monkeypatch.setattr(management, "CopyFeatures", copy_features)
    monkeypatch.setattr(management, "Append", append)
    monkeypatch.setattr(management, "DetectFeatureChanges", detect_feature_changes)
    monkeypatch.setattr(
        detect_changes,
        "_resolve_field_mapping",
        Mock(side_effect=["NAME NAME", "NAME NAME"]),
    )
    monkeypatch.setattr(detect_changes, "add_dfc_fields", Mock())
    monkeypatch.setattr(detect_changes.arcpy, "AlterAliasName", Mock())
    monkeypatch.setattr(detect_changes.arcpy, "Exists", Mock(return_value=False))

    monkeypatch.setattr(
        detect_changes,
        "get_output_workspace",
        Mock(return_value="workspace"),
    )
    detect_changes.run_detect_changes("update", "base", "49035", "append-target")

    make_feature_layer.assert_any_call(
        "base", "detect_changes_base", "COUNTY_L = '49035' OR COUNTY_R = '49035'"
    )
    make_feature_layer.assert_any_call(
        os.path.join("workspace", "DFC_RESULT"),
        "detect_changes_output",
        detect_changes.CHANGE_FILTER,
    )
    copy_features.assert_called_once_with(
        "detect_changes_output", os.path.join("workspace", "TEST_DFC_RESULT")
    )
    append.assert_called_once_with("detect_changes_output", "append-target", "NO_TEST")


def test_extract_fips_rejects_invalid_profile_value():
    import pytest

    with pytest.raises(RuntimeError, match="Invalid county FIPS"):
        detect_changes.extract_fips("Salt Lake")
