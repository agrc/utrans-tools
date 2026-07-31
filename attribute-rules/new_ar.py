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
			"- If --folder is omitted, the script is searched recursively under attribute-rules.\n"
			"- Exclude from client evaluation should be used for server workflows, not local/file geodatabases."
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
		"--replace",
		action="store_true",
		help="Replace an existing rule with the same name.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview the resolved script, rule name, and parameters without writing changes.",
	)
	parser.add_argument(
		"--server",
		action="store_true",
		help="Convenience flag for server workflows (AUTO client evaluation resolves to EXCLUDE).",
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
		"--exclude-from-client-evaluation",
		default="AUTO",
		choices=["AUTO", "EXCLUDE", "INCLUDE"],
		help=(
			"AUTO resolves to INCLUDE locally and EXCLUDE with --server. "
			"Use EXCLUDE for server workflows only."
		),
	)
	parser.add_argument(
		"--batch",
		default="NOT_BATCH",
		choices=["BATCH", "NOT_BATCH"],
		help="Whether calculation rule runs in batch mode.",
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


def _delete_rule_if_exists(in_table: str, rule_name: str) -> None:
	if rule_name not in _get_rule_names(in_table):
		return
	_log(f"Deleting existing rule '{rule_name}'")
	arcpy.management.DeleteAttributeRule(in_table, rule_name)


def _add_attribute_rule(args: argparse.Namespace, script_text: str, rule_name: str) -> None:
	effective_exclude = _resolve_exclude_from_client_evaluation(args)
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
		field=args.field,
		exclude_from_client_evaluation=effective_exclude,
		batch=args.batch,
	)


def _resolve_exclude_from_client_evaluation(args: argparse.Namespace) -> str:
	if args.exclude_from_client_evaluation in {"EXCLUDE", "INCLUDE"}:
		return args.exclude_from_client_evaluation
	if args.server:
		return "EXCLUDE"
	return "INCLUDE"


def main() -> None:
	args = _parse_args()

	if not arcpy.Exists(args.in_table):
		raise RuntimeError(f"Target dataset does not exist: {args.in_table}")

	arcade_path = _resolve_arcade_path(args.script_name, args.folder)
	rule_name = args.rule_name or _default_rule_name_from_stem(arcade_path.stem)
	effective_exclude = _resolve_exclude_from_client_evaluation(args)
	existing_rules = _get_rule_names(args.in_table)

	if args.dry_run:
		_log("Dry run: no changes will be written")
		_log(f"- in_table: {args.in_table}")
		_log(f"- arcade_path: {arcade_path}")
		_log(f"- rule_name: {rule_name}")
		_log(f"- type: {args.type}")
		_log(f"- field: {args.field or '(none)'}")
		_log(f"- triggering_events: {args.triggering_events}")
		_log(f"- exclude_from_client_evaluation: {effective_exclude}")
		_log(f"- existing_rule_found: {'yes' if rule_name in existing_rules else 'no'}")
		_log(f"- replace: {'yes' if args.replace else 'no'}")
		return

	if rule_name in existing_rules and not args.replace:
		raise RuntimeError(
			f"Attribute rule '{rule_name}' already exists on {args.in_table}. "
			"Use --replace to update it."
		)

	script_text = arcade_path.read_text(encoding="utf-8")

	if args.replace:
		_delete_rule_if_exists(args.in_table, rule_name)

	_log(f"Adding rule '{rule_name}' from script: {arcade_path}")
	_add_attribute_rule(args, script_text, rule_name)
	_log(f"Successfully added attribute rule '{rule_name}' to: {args.in_table}")


if __name__ == "__main__":
	main()
