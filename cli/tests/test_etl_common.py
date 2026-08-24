from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from utrans import etl_common
from utrans.etl_mappers import _fits_field_length


def _field(name, field_type="String", length=None):
    return SimpleNamespace(name=name, type=field_type, length=length, domain=None)


def _update_cursor(rows):
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.__iter__.return_value = iter(rows)
    return cursor


def test_add_missing_template_fields_reports_failed_field(monkeypatch):
    source_fields = []
    target_fields = [_field("ROAD_NAME", length=5)]
    add_field = Mock(side_effect=etl_common.arcpy.ExecuteError("invalid length"))
    monkeypatch.setattr(
        etl_common.arcpy,
        "ListFields",
        Mock(side_effect=[source_fields, target_fields]),
    )
    monkeypatch.setattr(etl_common.arcpy.management, "AddField", add_field)

    with pytest.raises(
        RuntimeError, match=r"ROAD_NAME.*String.*length=5.*invalid length"
    ):
        etl_common.add_missing_template_fields("source", "target")

    add_field.assert_called_once_with("source", "ROAD_NAME", "String", field_length=5)


def test_normalize_target_fields_reports_overlong_values(monkeypatch):
    source_fields = [_field("ONEWAY", length=2)]
    target_fields = [_field("ONEWAY", length=1)]
    cursor = _update_cursor([["FT"]])
    update_cursor = Mock(return_value=cursor)
    monkeypatch.setattr(
        etl_common.arcpy,
        "ListFields",
        Mock(side_effect=[source_fields, target_fields]),
    )
    monkeypatch.setattr(etl_common.arcpy.da, "UpdateCursor", update_cursor)

    with pytest.raises(RuntimeError, match=r"ONEWAY.*'FT'"):
        etl_common.normalize_target_fields("source", "target")


@pytest.mark.parametrize(
    ("value", "length", "expected"),
    [("F", 1, True), ("FT", 1, False), ("FT", 2, True)],
)
def test_fits_field_length(value, length, expected):
    assert _fits_field_length(value, {"ONEWAY": length}, "oneway") is expected
