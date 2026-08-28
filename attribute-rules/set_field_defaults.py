"""Assign field defaults programmatically based on ArcGIS field types.

Example:
	python attribute-rules/set_field_defaults.py \
		--in-table "Z:/data/County.gdb/Roads" \
		--dry-run
"""

from __future__ import annotations

import argparse

import arcpy


TEXT_FIELD_TYPES = {"String"}
INTEGER_FIELD_TYPES = {"SmallInteger", "Integer", "BigInteger"}
SKIP_FIELD_TYPES = {"OID", "Geometry", "Blob", "Raster", "Date", "GUID", "GlobalID"}
SKIP_FIELD_NAMES = {"Shape_Length", "Shape_Area"}
FIELD_DEFAULT_OVERRIDES = {"CARTOCODE": "11"}


def _log(message: str) -> None:
	print(message)


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Assign default values to fields based on ArcGIS field types.",
		epilog=(
			"Notes:\n"
			"- Required input: --in-table.\n"
			"- Preview mode is the default; use --apply to write schema changes.\n"
			"- Text fields default to an empty string; integer fields default to 0.\n"
			"- Domain-controlled fields are only updated when that default is a valid coded value.\n"
			"- CARTOCODE is overridden to default to 11."
		),
		formatter_class=argparse.RawDescriptionHelpFormatter,
		add_help=False,
	)
	required_args = parser.add_argument_group("required arguments")
	optional_args = parser.add_argument_group("optional arguments")

	optional_args.add_argument(
		"-h",
		"--help",
		action="help",
		help="show this help message and exit",
	)
	required_args.add_argument(
		"--in-table",
		required=True,
		help="Target feature class or table whose field defaults will be assigned.",
	)
	optional_args.add_argument(
		"--apply",
		action="store_true",
		help="Write changes to the dataset. If omitted, only preview the planned changes.",
	)
	optional_args.add_argument(
		"--all-subtypes",
		action="store_true",
		help="Assign the default separately to every subtype code on the dataset.",
	)
	optional_args.add_argument(
		"--field",
		action="append",
		default=[],
		help="Limit processing to one field name. Repeat the flag to target multiple fields.",
	)

	return parser.parse_args()


def _normalize_selected_fields(field_names: list[str]) -> set[str]:
	return {name.upper() for name in field_names}


def _get_candidate_default(field: arcpy.Field) -> object | None:
	override = FIELD_DEFAULT_OVERRIDES.get(field.name.upper())
	if override is not None:
		return override
	if field.type in TEXT_FIELD_TYPES:
		return ""
	if field.type in INTEGER_FIELD_TYPES:
		return 0
	return None


def _get_domains(in_table: str) -> dict[str, object]:
	workspace = arcpy.Describe(in_table).path
	return {domain.name: domain for domain in arcpy.da.ListDomains(workspace)}


def _get_subtype_codes(in_table: str) -> list[int | str]:
	subtypes = arcpy.da.ListSubtypes(in_table)
	return [code for code in subtypes if code is not None]


def _field_is_selected(field_name: str, selected_fields: set[str]) -> bool:
	if not selected_fields:
		return True
	return field_name.upper() in selected_fields


def _can_assign_domain_default(field: arcpy.Field, candidate: object, domains: dict[str, object]) -> bool:
	if not field.domain:
		return True

	domain = domains.get(field.domain)
	if domain is None or domain.domainType != "CodedValue":
		return False

	return candidate in domain.codedValues


def _assign_default(
	args: argparse.Namespace,
	field: arcpy.Field,
	candidate: object,
	subtype_codes: list[int | str],
) -> None:
	if args.all_subtypes and subtype_codes:
		for subtype_code in subtype_codes:
			arcpy.management.AssignDefaultToField(args.in_table, field.name, candidate, subtype_code)
			_log(f"SET subtype {subtype_code}: {field.name} = {candidate!r}")
		return

	arcpy.management.AssignDefaultToField(args.in_table, field.name, candidate)
	_log(f"SET: {field.name} = {candidate!r}")
def main() -> None:
	args = _parse_args()

	if not arcpy.Exists(args.in_table):
		raise RuntimeError(f"Target dataset does not exist: {args.in_table}")

	selected_fields = _normalize_selected_fields(args.field)
	domains = _get_domains(args.in_table)
	subtype_codes = _get_subtype_codes(args.in_table) if args.all_subtypes else []
	mode = "Apply" if args.apply else "Dry run"

	_log(f"{mode}: {'writing schema changes' if args.apply else 'no changes will be written'}")
	_log(f"- in_table: {args.in_table}")
	_log(f"- all_subtypes: {'yes' if args.all_subtypes else 'no'}")
	_log(f"- selected_fields: {', '.join(args.field) if args.field else '(all eligible fields)'}")

	for field in arcpy.ListFields(args.in_table):
		if field.required:
			continue
		if field.name in SKIP_FIELD_NAMES:
			continue
		if field.type in SKIP_FIELD_TYPES:
			continue
		if not _field_is_selected(field.name, selected_fields):
			continue

		candidate = _get_candidate_default(field)
		if candidate is None:
			_log(f"SKIP unsupported type: {field.name} ({field.type})")
			continue

		if not _can_assign_domain_default(field, candidate, domains):
			if field.domain:
				_log(
					f"SKIP domain mismatch: {field.name} -> {candidate!r} is not a valid code in {field.domain}"
				)
			else:
				_log(f"SKIP unsupported domain type: {field.name} ({field.domain})")
			continue

		if not args.apply:
			if args.all_subtypes and subtype_codes:
				for subtype_code in subtype_codes:
					_log(f"WOULD SET subtype {subtype_code}: {field.name} = {candidate!r}")
			else:
				_log(f"WOULD SET: {field.name} = {candidate!r}")
			continue

		_assign_default(args, field, candidate, subtype_codes)


if __name__ == "__main__":
	main()