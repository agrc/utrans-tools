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


def test_handlers_declare_cursor_target_fields():
    assert "AN_NAME" in HANDLERS["utah_road_names"].target_fields


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


def test_davis_handler_parses_alpha_and_numeric_aliases():
    row: list[object] = ["Main WY", "", "", "", ""]
    indexes = {
        "ROADALIASNAME": 0,
        "A1_NAME": 1,
        "A1_POSTTYPE": 2,
        "AN_NAME": 3,
        "AN_POSTDIR": 4,
    }
    handler = HANDLERS["davis_alias"]

    handler.apply(row, indexes, {"A1_POSTTYPE": {"WAY": "WAY"}})

    assert row[1:3] == ["Main", "WAY"]

    row[0] = "1200 N"
    handler.apply(row, indexes, {})

    assert row[3:5] == ["1200", "N"]


def test_washington_handler_prefers_suffix_direction_and_deduplicates_aliases():
    row: list[object] = ["NORTH", "WEST", "1200", "1200 W", "", "", "", "", ""]
    indexes = {
        "POSTDIR_": 0,
        "SUFFIXDIR": 1,
        "AN_NAME": 2,
        "A1_NAME": 3,
        "A1_PREDIR": 4,
        "A1_POSTTYPE": 5,
        "A1_POSTDIR": 6,
        "POSTDIR": 7,
        "A2_NAME": 8,
    }

    HANDLERS["washington_postdir_and_aliases"].apply(row, indexes, {})

    assert row[3:7] == ["", "", "", ""]
    assert row[7] == "W"


def test_weber_handler_uses_acs_alias_for_numeric_aliases():
    row: list[object] = ["1200", "1200 W", "MAIN", "S", "", "", "", ""]
    indexes = {
        "ALIAS": 0,
        "ACS_ALIAS": 1,
        "S_NAME": 2,
        "SUFDIR": 3,
        "A1_NAME": 4,
        "A1_POSTTYPE": 5,
        "AN_NAME": 6,
        "AN_POSTDIR": 7,
    }

    HANDLERS["weber_alias"].apply(row, indexes, {})

    assert row[6:8] == ["1200", "W"]


def test_remaining_handlers_apply_verified_legacy_conditions():
    summit_row: list[object] = ["US", "89", "ALT 89", "", "", "", "", ""]
    summit_indexes = {
        "PRE_TYPE": 0,
        "NAME": 1,
        "OTHER_NAME": 2,
        "STREET": 1,
        "A1_PREDIR": 3,
        "A1_NAME": 4,
        "A1_POSTTYPE": 5,
        "A1_POSTDIR": 6,
        "AN_NAME": 7,
    }
    HANDLERS["summit_names"].apply(summit_row, summit_indexes, {})
    assert summit_row[1] == "US 89"

    emery_row: list[object] = ["100N", "", "", "", ""]
    emery_indexes = {
        "ACS_ALIAS": 0,
        "ALIAS1": 1,
        "ALIAS2": 2,
        "AN_NAME": 3,
        "AN_POSTDIR": 4,
    }
    HANDLERS["emery_compact_aliases"].apply(emery_row, emery_indexes, {})
    assert emery_row[3:5] == ["100", "N"]

    kane_row: list[object] = ["K7000", "RD", "", "", ""]
    kane_indexes = {
        "A1_NAME": 0,
        "A1_POSTTYPE": 1,
        "A1_PREDIR": 2,
        "A1_POSTDIR": 3,
        "A2_NAME": 4,
    }
    HANDLERS["kane_alias_cleanup"].apply(kane_row, kane_indexes, {})
    assert kane_row[:2] == ["", ""]
