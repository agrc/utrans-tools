import pytest

from utrans import recent_edits


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
