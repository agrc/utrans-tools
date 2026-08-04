"""Create an ArcGIS attribute rule from a local .arcade script.

Example:
	python attribute-rules/new_ar.py fullname_calculation \
		--in-table "Z:/data/County.gdb/Roads" \
		--field FULLNAME
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import arcpy


ATTRIBUTE_RULES_ROOT = Path(__file__).resolve().parent


def _log(message: str) -> None:
	print(message)


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Add an ArcGIS attribute rule from a .arcade script in the attribute-rules directory."
		),
		epilog=(
			"Notes:\n"
			"- script_name can be either name or name.arcade.\n"
			"- If --folder is omitted, the script is searched recursively under attribute-rules."
		),
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)

	parser.add_argument(
		"script_name",
		help="Arcade script filename with or without .arcade extension.",
	)
	parser.add_argument(
		"--in-table",
		required=True,
		help="Target feature class or table where the rule will be created.",
	)
	parser.add_argument(
		"--folder",
		default="",
		help="Optional subfolder under attribute-rules that contains the .arcade file.",
	)
	parser.add_argument(
		"--rule-name",
		help="Optional explicit rule name. Defaults to a title-cased name from the script filename.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview the resolved script, rule name, and parameters without writing changes.",
	)

	parser.add_argument(
		"--type",
		default="CALCULATION",
		choices=["CALCULATION", "CONSTRAINT", "VALIDATION"],
		help="Attribute rule type.",
	)
	parser.add_argument(
		"--field",
		default="",
		help="Target field for the rule when applicable (commonly used for CALCULATION).",
	)
	parser.add_argument(
		"--triggering-events",
		default="INSERT;UPDATE",
		help="Semicolon-delimited events, e.g. INSERT;UPDATE or UPDATE.",
	)
	parser.add_argument(
		"--is-editable",
		default="NONEDITABLE",
		choices=["EDITABLE", "NONEDITABLE"],
		help="Whether users can manually edit values managed by the rule.",
	)
	parser.add_argument(
		"--error-number",
		type=int,
		default=1,
		help="Error number for CONSTRAINT/VALIDATION rules.",
	)
	parser.add_argument(
		"--error-message",
		default="Attribute rule violation.",
		help="Error message for CONSTRAINT/VALIDATION rules.",
	)
	parser.add_argument(
		"--description",
		default="",
		help="Optional attribute rule description.",
	)
	parser.add_argument(
		"--subtype",
		default="",
		help="Optional subtype code.",
	)

	return parser.parse_args()


def _normalize_script_name(script_name: str) -> str:
	script_path = Path(script_name)
	stem = script_path.stem
	if not stem:
		raise ValueError("script_name must not be empty")
	return f"{stem}.arcade"


def _default_rule_name_from_stem(stem: str) -> str:
	# Convert snake/kebab/camel-ish names into user-friendly ArcGIS rule names.
	spaced = re.sub(r"[_-]+", " ", stem)
	spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", spaced)
	return " ".join(word.capitalize() for word in spaced.split())


def _resolve_arcade_path(script_name: str, folder: str) -> Path:
	arcade_filename = _normalize_script_name(script_name)
	if folder:
		candidate = (ATTRIBUTE_RULES_ROOT / folder / arcade_filename).resolve()
		if not candidate.is_relative_to(ATTRIBUTE_RULES_ROOT):
			raise ValueError("Resolved script path must stay within the attribute-rules directory")
		if not candidate.exists():
			raise FileNotFoundError(f"Arcade script not found: {candidate}")
		return candidate

	matches = sorted(path.resolve() for path in ATTRIBUTE_RULES_ROOT.rglob(arcade_filename))
	if not matches:
		raise FileNotFoundError(
			f"Arcade script '{arcade_filename}' was not found under {ATTRIBUTE_RULES_ROOT}"
		)
	if len(matches) > 1:
		match_list = "\n".join(str(path) for path in matches)
		raise RuntimeError(
			"Multiple matching scripts found. Use --folder to disambiguate:\n"
			f"{match_list}"
		)

	return matches[0]


def _get_rule_names(in_table: str) -> set[str]:
	desc = arcpy.Describe(in_table)
	rules = getattr(desc, "attributeRules", None) or []
	return {rule.name for rule in rules}


def _add_attribute_rule(args: argparse.Namespace, script_text: str, rule_name: str) -> None:
	arcpy.management.AddAttributeRule(
		in_table=args.in_table,
		name=rule_name,
		type=args.type,
		script_expression=script_text,
		is_editable=args.is_editable,
		triggering_events=args.triggering_events,
		error_number=args.error_number,
		error_message=args.error_message,
		description=args.description,
		subtype=args.subtype,
		field=args.field
	)


def main() -> None:
	args = _parse_args()

	if not arcpy.Exists(args.in_table):
		raise RuntimeError(f"Target dataset does not exist: {args.in_table}")

	arcade_path = _resolve_arcade_path(args.script_name, args.folder)
	rule_name = args.rule_name or _default_rule_name_from_stem(arcade_path.stem)
	existing_rules = _get_rule_names(args.in_table)

	if args.dry_run:
		_log("Dry run: no changes will be written")
		_log(f"- in_table: {args.in_table}")
		_log(f"- arcade_path: {arcade_path}")
		_log(f"- rule_name: {rule_name}")
		_log(f"- type: {args.type}")
		_log(f"- field: {args.field or '(none)'}")
		_log(f"- triggering_events: {args.triggering_events}")
		_log("- exclude_from_client_evaluation: default fixed value (unchecked)")
		_log("- batch: default fixed value (unchecked)")
		_log(f"- existing_rule_found: {'yes' if rule_name in existing_rules else 'no'}")
		return

	if rule_name in existing_rules:
		raise RuntimeError(
			f"Attribute rule '{rule_name}' already exists on {args.in_table}. "
			"Choose a different --rule-name or remove the existing rule first."
		)

	script_text = arcade_path.read_text(encoding="utf-8")

	_log(f"Adding rule '{rule_name}' from script: {arcade_path}")
	_add_attribute_rule(args, script_text, rule_name)
	_log(f"Successfully added attribute rule '{rule_name}' to: {args.in_table}")


if __name__ == "__main__":
	main()
