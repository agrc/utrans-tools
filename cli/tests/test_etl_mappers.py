import pytest

from utrans.etl_handlers import HANDLERS, profile_handler
from utrans.etl_mappers import _validate_value_mappings, _value_mappings
from utrans.etl_rules import apply_rules, profile_rules
from utrans.profiles import CountyProfile


def test_value_mappings_normalizes_fields_and_source_values():
    profile = CountyProfile(
        key="example",
        values={
            "value_mappings": {
                "oneway": {" One Direction ": "Y"},
            }
        },
    )

    assert _value_mappings(profile) == {"ONEWAY": {"ONE DIRECTION": "Y"}}


@pytest.mark.parametrize(
    "value, message",
    [
        ([], "must be an object"),
        ({"ONEWAY": []}, "map field names to objects"),
        ({"ONEWAY": {"ONE DIRECTION": 1}}, "must map strings to strings"),
    ],
)
def test_value_mappings_reject_invalid_configuration(value, message):
    profile = CountyProfile(key="example", values={"value_mappings": value})

    with pytest.raises(TypeError, match=message):
        _value_mappings(profile)


def test_value_mappings_validate_targets_and_domain_values():
    profile = CountyProfile(key="example", values={})

    with pytest.raises(ValueError, match="unknown target field"):
        _validate_value_mappings(profile, {"ONEWAY": {}}, {}, {})

    with pytest.raises(ValueError, match="outside the target domain"):
        _validate_value_mappings(
            profile,
            {"ONEWAY": {"ONE DIRECTION": "MAYBE"}},
            {"ONEWAY": "ONEWAY"},
            {"ONEWAY": {"Y": "Y", "YES": "Y"}},
        )


def test_rules_apply_legacy_name_cleanup():
    row: list[object] = ["1200", "RD", "N"]
    indexes = {"NAME": 0, "POSTTYPE": 1, "POSTDIR": 2}

    apply_rules(row, indexes, ["remove_posttype_if_numeric"])

    assert row == ["1200", "", "N"]


def test_rules_reject_unknown_and_duplicate_names():
    profile = CountyProfile(key="example", values={"rules": ["unknown"]})

    with pytest.raises(ValueError, match="unsupported"):
        profile_rules(profile)

    profile = CountyProfile(
        key="example", values={"rules": ["remove_posttype_if_numeric"] * 2}
    )
    with pytest.raises(ValueError, match="duplicates"):
        profile_rules(profile)


def test_profile_handler_uses_closed_registry():
    profile = CountyProfile(key="utah", values={"custom_handler": "utah_road_names"})

    assert profile_handler(profile) is HANDLERS["utah_road_names"]

    profile = CountyProfile(key="example", values={"custom_handler": "os.system"})
    with pytest.raises(ValueError, match="unsupported custom_handler"):
        profile_handler(profile)


def test_utah_handler_parses_numeric_primary_and_alias_names():
    row: list[object] = [
        "1200 NORTH",
        "300 WEST",
        "DR",
        "500 SOUTH",
        "",
        "",
        "",
        "RD",
        "",
        "",
        "",
        "",
    ]
    indexes = {
        "ROADNAME": 0,
        "ALTROADNAME": 1,
        "ALTROADTYPE": 2,
        "ALTROADNAME2": 3,
        "NAME": 4,
        "POSTDIR": 5,
        "A1_NAME": 6,
        "A1_POSTTYPE": 7,
        "A2_NAME": 8,
        "AN_NAME": 9,
        "AN_POSTDIR": 10,
        "POSTTYPE": 11,
    }

    HANDLERS["utah_road_names"].apply(
        row,
        indexes,
        {"A1_POSTTYPE": {"DR": "DR"}},
    )

    assert row[4:6] == ["1200", "N"]
    assert row[6:9] == ["", "", ""]
    assert row[9:11] == ["300", "W"]
    assert row[11] == ""
