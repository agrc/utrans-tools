from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from utrans import etl_common


def _field(name, field_type="String", length=None):
    return SimpleNamespace(name=name, type=field_type, length=length, domain=None)


def _search_cursor(rows):
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=iter(rows))
    cursor.__exit__ = Mock(return_value=False)
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

    with pytest.raises(RuntimeError, match=r"ROAD_NAME.*String.*length=5.*invalid length"):
        etl_common.add_missing_template_fields("source", "target")

    add_field.assert_called_once_with("source", "ROAD_NAME", "String", field_length=5)