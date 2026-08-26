"""Discover county source values that need UTRANS value mappings.

Run with ArcGIS Pro's Python environment. This is intentionally a one-use
script, not a package entry point.

The ``discover`` mode reads a county manifest, inspects the source feature
classes, and writes an inventory CSV plus a processing-summary CSV. The
``apply`` mode reads the inventory and a reviewed copy of it, then merges
approved review mappings directly into the profiles JSON file. Values already
marked ``resolved`` need no value mapping and are ignored by ``apply``.

Required input:
    --target-features: A UTRANS feature class whose coded-value domains define
        the valid destination values.

Fixed repository inputs:
    ``county_datasets.csv`` and ``../src/utrans/profiles.json`` are resolved
    relative to this script.

Current-working-directory files:
    ``discover`` writes ``value-mapping-inventory.csv`` and
    ``value-mapping-summary.csv`` and ``reviewed-value-mappings.csv``.
    ``apply`` reads
    ``reviewed-value-mappings.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import arcpy

INVENTORY_FIELDS = (
    "county",
    "profile",
    "source_features",
    "target_field",
    "source_field",
    "observed_value",
    "normalized_value",
    "count",
    "resolved_target_value",
    "status",
)
SUMMARY_FIELDS = ("county", "profile", "source_features", "status", "detail")
REVIEW_FIELDS = INVENTORY_FIELDS + ("approved_target_value",)
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_MANIFEST = SCRIPT_DIRECTORY / "county_datasets.csv"
DEFAULT_PROFILES = SCRIPT_DIRECTORY.parent / "src" / "utrans" / "profiles.json"


def parse_field_mappings(profile: dict[str, Any], county: str) -> dict[str, str]:
    value = profile.get("field_mappings", "")
    if not isinstance(value, str):
        raise TypeError(f"Profile '{county}' field_mappings must be a string.")
    mappings: dict[str, str] = {}
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise TypeError(f"Profile '{county}' has invalid mapping '{item}'.")
        target, source = (part.strip() for part in item.split("=", 1))
        mappings[target.upper()] = source
    return mappings


def target_domains(target_features: str) -> dict[str, dict[str, str]]:
    target_description = arcpy.Describe(target_features)
    workspace = Path(target_description.catalogPath).parent
    workspace_description = arcpy.Describe(str(workspace))
    if getattr(workspace_description, "datasetType", None) == "FeatureDataset":
        workspace = workspace.parent

    domains = {domain.name: domain for domain in arcpy.da.ListDomains(str(workspace))}
    values: dict[str, dict[str, str]] = {}
    for field in arcpy.ListFields(target_features):
        if not field.domain or field.domain not in domains:
            continue
        accepted: dict[str, str] = {}
        for code, description in domains[field.domain].codedValues.items():
            code_text = str(code).strip().upper()
            accepted[code_text] = str(code)
            accepted[str(description).strip().upper()] = str(code)
        values[field.name.upper()] = accepted
    return values


def field_names(feature_class: str) -> dict[str, str]:
    return {field.name.upper(): field.name for field in arcpy.ListFields(feature_class)}


def observed_values(
    feature_class: str, source_field: str
) -> dict[str, tuple[str, int]]:
    counts: Counter[str] = Counter()
    representatives: dict[str, str] = {}
    with arcpy.da.SearchCursor(feature_class, [source_field]) as cursor:
        for (value,) in cursor:
            if value is None or not str(value).strip():
                continue
            raw_value = str(value).strip()
            normalized_value = raw_value.upper()
            representatives.setdefault(normalized_value, raw_value)
            counts[normalized_value] += 1
    return {
        normalized_value: (representatives[normalized_value], count)
        for normalized_value, count in counts.items()
    }


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as manifest_file:
        rows = list(csv.DictReader(manifest_file))
    required = {"county", "profile", "source_features"}
    if not rows or not required <= set(rows[0]):
        raise TypeError(
            "Manifest must contain county, profile, and source_features columns."
        )
    return [{key: value.strip() for key, value in row.items()} for row in rows]


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as profiles_file:
        profiles = json.load(profiles_file)
    if not isinstance(profiles, dict):
        raise TypeError("Profiles JSON must contain an object keyed by county.")
    return profiles


def write_csv(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def discover(
    manifest_path: Path,
    profiles_path: Path,
    target_features: str,
    inventory_path: Path,
    summary_path: Path,
    reviewed_path: Path,
) -> None:
    profiles = load_profiles(profiles_path)
    domains = target_domains(target_features)
    inventory: list[dict[str, object]] = []
    summary: list[dict[str, str]] = []

    for manifest_row in load_manifest(manifest_path):
        county = manifest_row["county"]
        profile_key = manifest_row["profile"]
        source_features = manifest_row["source_features"]
        if profile_key not in profiles:
            summary.append(
                {
                    "county": county,
                    "profile": profile_key,
                    "source_features": source_features,
                    "status": "missing_profile",
                    "detail": "Profile key was not found.",
                }
            )
            continue
        if not arcpy.Exists(source_features):
            summary.append(
                {
                    "county": county,
                    "profile": profile_key,
                    "source_features": source_features,
                    "status": "missing_dataset",
                    "detail": "Feature class was not found.",
                }
            )
            continue

        try:
            mappings = parse_field_mappings(profiles[profile_key], profile_key)
        except (TypeError, ValueError) as exc:
            summary.append(
                {
                    "county": county,
                    "profile": profile_key,
                    "source_features": source_features,
                    "status": "invalid_profile",
                    "detail": str(exc),
                }
            )
            continue
        source_names = field_names(source_features)
        domain_mappings = [
            (target, source) for target, source in mappings.items() if target in domains
        ]
        if not domain_mappings:
            summary.append(
                {
                    "county": county,
                    "profile": profile_key,
                    "source_features": source_features,
                    "status": "no_domain_mappings",
                    "detail": "No mapped target fields have coded-value domains.",
                }
            )
            continue

        county_rows = 0
        for target, source in sorted(domain_mappings):
            actual_source = source_names.get(source.upper())
            if actual_source is None:
                summary.append(
                    {
                        "county": county,
                        "profile": profile_key,
                        "source_features": source_features,
                        "status": "missing_source_field",
                        "detail": f"{source} maps to {target}.",
                    }
                )
                continue
            counts = observed_values(source_features, actual_source)
            if not counts:
                summary.append(
                    {
                        "county": county,
                        "profile": profile_key,
                        "source_features": source_features,
                        "status": "no_observations",
                        "detail": f"{actual_source} maps to {target}.",
                    }
                )
            for normalized_value, (observed_value, count) in sorted(counts.items()):
                resolved = domains[target].get(normalized_value, "")
                inventory.append(
                    {
                        "county": county,
                        "profile": profile_key,
                        "source_features": source_features,
                        "target_field": target,
                        "source_field": actual_source,
                        "observed_value": observed_value,
                        "normalized_value": normalized_value,
                        "count": count,
                        "resolved_target_value": resolved,
                        "status": "resolved" if resolved else "review",
                    }
                )
                county_rows += 1
        summary.append(
            {
                "county": county,
                "profile": profile_key,
                "source_features": source_features,
                "status": "discovered",
                "detail": f"{county_rows} observed values.",
            }
        )

    inventory.sort(
        key=lambda row: (
            str(row["county"]),
            str(row["target_field"]),
            str(row["source_field"]),
            str(row["normalized_value"]),
        )
    )
    summary.sort(key=lambda row: row["county"])
    write_csv(inventory_path, INVENTORY_FIELDS, inventory)
    write_csv(summary_path, SUMMARY_FIELDS, summary)
    review_rows = [
        {**row, "approved_target_value": ""}
        for row in inventory
        if row["status"] == "review"
    ]
    write_csv(reviewed_path, REVIEW_FIELDS, review_rows)
    print(f"Wrote {len(inventory)} inventory rows to {inventory_path}")
    print(f"Wrote {len(summary)} summary rows to {summary_path}")
    print(f"Wrote {len(review_rows)} rows for review to {reviewed_path}")


def apply_mappings(
    profiles_path: Path,
    inventory_path: Path,
    reviewed_path: Path,
    target_features: str,
) -> None:
    profiles = load_profiles(profiles_path)
    domains = target_domains(target_features)
    inventory_rows: dict[tuple[str, str, str], dict[str, str]] = {}
    with inventory_path.open(newline="", encoding="utf-8-sig") as inventory_file:
        for row in csv.DictReader(inventory_file):
            key = (
                row["profile"],
                row["target_field"].strip().upper(),
                row["normalized_value"].strip().upper(),
            )
            inventory_rows[key] = row

    additions: dict[str, dict[str, dict[str, str]]] = {}
    with reviewed_path.open(newline="", encoding="utf-8-sig") as reviewed_file:
        for row in csv.DictReader(reviewed_file):
            approved = row.get("approved_target_value", "").strip()
            if not approved:
                continue
            profile = row["profile"]
            target = row["target_field"].strip().upper()
            source = row["normalized_value"].strip().upper()
            inventory_row = inventory_rows.get((profile, target, source))
            if profile not in profiles or inventory_row is None:
                raise ValueError(
                    f"Reviewed mapping is not present in inventory: {profile}/{target}/{source}"
                )
            if inventory_row["status"] != "review":
                raise ValueError(
                    f"Only review rows may have approval: {profile}/{target}/{source}"
                )
            if target not in domains or domains[target].get(approved.upper()) is None:
                raise ValueError(
                    f"Approved value '{approved}' is invalid for target field '{target}'."
                )
            destination = domains[target][approved.upper()]
            if source == destination.strip().upper():
                continue
            pending = (
                additions.setdefault(profile, {}).setdefault(target, {}).get(source)
            )
            if pending is not None and pending != destination:
                raise ValueError(
                    f"Conflicting approvals for {profile}/{target}/{source}."
                )
            additions[profile][target][source] = destination

    for profile, targets in additions.items():
        profile_mappings = profiles[profile].setdefault("value_mappings", {})
        for target, values in targets.items():
            target_mappings = profile_mappings.setdefault(target, {})
            for source, destination in values.items():
                existing = next(
                    (
                        value
                        for key, value in target_mappings.items()
                        if str(key).strip().upper() == source
                    ),
                    None,
                )
                if (
                    existing is not None
                    and str(existing).strip().upper() != destination.upper()
                ):
                    raise ValueError(
                        f"Conflicting mappings for {profile}/{target}/{source}."
                    )
                target_mappings[source] = destination

    profiles_path.write_text(json.dumps(profiles, indent=2) + "\n", encoding="utf-8")
    print(f"Applied inventory mappings to {profiles_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("discover", "apply"),
        help="Run discovery or apply reviewed mappings to profiles.json.",
    )
    parser.add_argument(
        "--target-features",
        required=True,
        help="UTRANS target feature class providing coded-value domains.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    working_directory = Path.cwd()
    if args.mode == "discover":
        discover(
            DEFAULT_MANIFEST,
            DEFAULT_PROFILES,
            args.target_features,
            working_directory / "value-mapping-inventory.csv",
            working_directory / "value-mapping-summary.csv",
            working_directory / "reviewed-value-mappings.csv",
        )
    else:
        apply_mappings(
            DEFAULT_PROFILES,
            working_directory / "value-mapping-inventory.csv",
            working_directory / "reviewed-value-mappings.csv",
            args.target_features,
        )


if __name__ == "__main__":
    main()
