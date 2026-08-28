"""Deploy ArcGIS attribute rules from local .arcade scripts.

Examples:
	# idempotent deploy (add if missing, update if present)
	python attribute-rules/deploy_ar.py fullname_calculation \
		--in-table "Z:/data/County.gdb/Roads" \
		--field FULLNAME

	# strict add-only behavior
	python attribute-rules/deploy_ar.py fullname_calculation \
		--in-table "Z:/data/County.gdb/Roads" \
		--mode add
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import arcpy


ATTRIBUTE_RULES_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class RuleState:
	name: str
	type: str
	field: str
	subtype: str
	is_editable: str
	triggering_events: str
	script_expression: str
	error_number: str
	error_message: str
	description: str


def _log(message: str) -> None:
	# Flush so progress is visible during slow enterprise deploys and when output is piped.
	print(message, flush=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description=(
			"Deploy an ArcGIS attribute rule from a .arcade script in the attribute-rules directory."
		),
		epilog=(
			"Modes:\n"
			"- deploy (default): add if missing, alter if mutable changes, recreate if immutable changes.\n"
			"- add: add only and fail when the rule already exists.\n"
			"- alter: alter only and fail when the rule is missing.\n"
			"\n"
			"Notes:\n"
			"- Required inputs: script_name and --in-table.\n"
			"- script_name can be either name or name.arcade.\n"
			"- If --folder is omitted, the script is searched recursively under attribute-rules."
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
	parser.add_argument(
		"script_name",
		help="Arcade script filename with or without .arcade extension.",
	)
	required_args.add_argument(
		"--in-table",
		required=True,
		help="Target feature class or table where the rule will be managed.",
	)
	optional_args.add_argument(
		"--mode",
		default="deploy",
		choices=["deploy", "add", "alter"],
		help="Rule management mode.",
	)
	optional_args.add_argument(
		"--folder",
		default="",
		help="Optional subfolder under attribute-rules that contains the .arcade file.",
	)
	optional_args.add_argument(
		"--rule-name",
		help="Optional explicit rule name. Defaults to a title-cased name from the script filename.",
	)
	optional_args.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview actions without writing changes.",
	)
	optional_args.add_argument(
		"--no-recreate",
		action="store_true",
		help=(
			"In deploy mode, fail instead of delete/recreate when immutable properties differ."
		),
	)

	optional_args.add_argument(
		"--type",
		default="CALCULATION",
		choices=["CALCULATION", "CONSTRAINT", "VALIDATION"],
		help="Attribute rule type.",
	)
	optional_args.add_argument(
		"--field",
		default="",
		help="Target field for the rule when applicable (commonly used for CALCULATION).",
	)
	optional_args.add_argument(
		"--triggering-events",
		default="INSERT;UPDATE",
		help="Semicolon-delimited events, e.g. INSERT;UPDATE or UPDATE.",
	)
	optional_args.add_argument(
		"--is-editable",
		default="EDITABLE",
		choices=["EDITABLE", "NONEDITABLE"],
		help="Whether users can manually edit values managed by the rule.",
	)
	optional_args.add_argument(
		"--error-number",
		type=int,
		default=1,
		help="Error number for CONSTRAINT/VALIDATION rules.",
	)
	optional_args.add_argument(
		"--error-message",
		default="Attribute rule violation.",
		help="Error message for CONSTRAINT/VALIDATION rules.",
	)
	optional_args.add_argument(
		"--description",
		default="",
		help="Optional attribute rule description.",
	)
	optional_args.add_argument(
		"--subtype",
		default="",
		help="Optional subtype code.",
	)

	return parser.parse_args(argv)


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


def _normalize_rule_name_for_lookup(name: str) -> str:
	# ArcGIS treats rule names effectively case-insensitively; normalize lookups for idempotency.
	return _as_text(name).strip().casefold()


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


def _as_text(value: object) -> str:
	if value is None:
		return ""
	return str(value)


def _normalize_type(value: object) -> str:
	text = _as_text(value).strip().upper()
	if text.startswith("ESRIART"):
		return text.removeprefix("ESRIART")
	return text


def _normalize_subtype(value: object) -> str:
	text = _as_text(value).strip()
	if text in {"", "-1"}:
		return ""
	return text


def _normalize_events(value: object) -> str:
	if isinstance(value, (list, tuple, set)):
		raw_parts = [_as_text(part) for part in value]
	else:
		text = _as_text(value)
		if "[" in text and "]" in text:
			raw_parts = re.findall(r"[A-Za-z0-9_]+", text)
		else:
			raw_parts = re.split(r"[;,]", text)

	events: list[str] = []
	for part in raw_parts:
		token = part.strip().strip("\"'").upper()
		if not token:
			continue
		if token.startswith("ESRIARTE"):
			token = token.removeprefix("ESRIARTE")
		events.append(token)

	return ";".join(sorted(set(events)))


def _normalize_editable(value: object) -> str:
	if isinstance(value, bool):
		return "EDITABLE" if value else "NONEDITABLE"
	text = _as_text(value).strip().upper()
	if text in {"TRUE", "1", "EDITABLE"}:
		return "EDITABLE"
	if text in {"FALSE", "0", "NONEDITABLE"}:
		return "NONEDITABLE"
	return text


def _normalize_script(script_expression: str) -> str:
	return script_expression.replace("\r\n", "\n").strip()


def _rule_state_from_args(args: argparse.Namespace, rule_name: str, script_text: str) -> RuleState:
	type_name = _normalize_type(args.type)
	triggering_events = _normalize_events(args.triggering_events)
	if type_name == "VALIDATION":
		triggering_events = ""

	error_number = _as_text(args.error_number).strip()
	error_message = _as_text(args.error_message)
	if type_name == "CALCULATION":
		# ArcGIS commonly stores calc-rule error metadata as unset/sentinel values.
		error_number = "-1"
		error_message = ""

	return RuleState(
		name=rule_name,
		type=type_name,
		field=_as_text(args.field).strip(),
		subtype=_normalize_subtype(args.subtype),
		is_editable=_normalize_editable(args.is_editable),
		triggering_events=triggering_events,
		script_expression=_normalize_script(script_text),
		error_number=error_number,
		error_message=error_message,
		description=_as_text(args.description),
	)


def _rule_state_from_existing(rule: object) -> RuleState:
	return RuleState(
		name=_as_text(getattr(rule, "name", "")).strip(),
		type=_normalize_type(getattr(rule, "type", "")),
		field=_as_text(getattr(rule, "fieldName", "")).strip(),
		subtype=_normalize_subtype(getattr(rule, "subtypeCode", "")),
		is_editable=_normalize_editable(getattr(rule, "isEditable", "")),
		triggering_events=_normalize_events(getattr(rule, "triggeringEvents", "")),
		script_expression=_normalize_script(_as_text(getattr(rule, "scriptExpression", ""))),
		error_number=_as_text(getattr(rule, "errorNumber", "")).strip(),
		error_message=_as_text(getattr(rule, "errorMessage", "")),
		description=_as_text(getattr(rule, "description", "")),
	)


# Describe round trips cost seconds against an enterprise geodatabase, so cache static lookups.
_DESCRIBE_CACHE: dict[str, object] = {}


def _describe_cached(path: str) -> object:
	if path not in _DESCRIBE_CACHE:
		_DESCRIBE_CACHE[path] = arcpy.Describe(path)
	return _DESCRIBE_CACHE[path]


def _validate_in_table(in_table: str) -> None:
	data_type = _as_text(getattr(_describe_cached(in_table), "dataType", ""))
	if data_type in {"FeatureClass", "Table", "FeatureLayer", "TableView"}:
		return

	if data_type in {"Workspace", "FeatureDataset"}:
		raise RuntimeError(
			f"--in-table must name a feature class or table, but {in_table} is a "
			f"{data_type}. Append the dataset name, for example "
			f"{in_table}\\TRANSADMIN.Roads_Edit"
		)

	raise RuntimeError(f"--in-table must be a feature class or table, but found {data_type}: {in_table}")


def _describe_workspace(in_table: str) -> object | None:
	path = _as_text(getattr(_describe_cached(in_table), "path", ""))
	# Walk up past any feature dataset until the workspace itself is described.
	for _ in range(3):
		if not path:
			return None
		desc = _describe_cached(path)
		if hasattr(desc, "connectionProperties"):
			return desc
		path = _as_text(getattr(desc, "path", ""))
	return None


def _warn_enterprise_preconditions(in_table: str, rule_type: str) -> None:
	workspace = _describe_workspace(in_table)
	if workspace is None:
		return

	desc = _describe_cached(in_table)
	connection = getattr(workspace, "connectionProperties", None)

	if (
		rule_type == "VALIDATION"
		and getattr(desc, "isVersioned", False)
		and not getattr(connection, "branch", None)
	):
		_log(
			"WARNING: validation rules require branch versioning on an enterprise "
			"geodatabase, but this dataset is not branch versioned."
		)

	owner = _as_text(getattr(desc, "name", "")).split(".")[0]
	user = _as_text(getattr(connection, "user", ""))
	if owner and user and owner.casefold() != user.casefold():
		_log(
			f"WARNING: connected as {user!r} but the dataset owner is {owner!r}. "
			"Attribute rule changes must be made by the data owner."
		)


def _get_rule_states(in_table: str) -> dict[str, RuleState]:
	desc = arcpy.Describe(in_table)
	rules = getattr(desc, "attributeRules", None) or []
	states: dict[str, RuleState] = {}
	for rule in rules:
		state = _rule_state_from_existing(rule)
		states[_normalize_rule_name_for_lookup(state.name)] = state
	return states


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
		field=args.field,
	)


def _alter_attribute_rule(args: argparse.Namespace, script_text: str, rule_name: str) -> None:
	triggering_events = args.triggering_events if args.type != "VALIDATION" else ""
	error_number = str(args.error_number) if args.type != "CALCULATION" else ""
	error_message = args.error_message if args.type != "CALCULATION" else ""
	description = args.description if args.description else ""

	arcpy.management.AlterAttributeRule(
		in_table=args.in_table,
		name=rule_name,
		description=description,
		error_number=error_number,
		error_message=error_message,
		triggering_events=triggering_events,
		script_expression=script_text,
	)


def _delete_attribute_rule(
	args: argparse.Namespace,
	rule_name: str,
	rule_type: str,
) -> None:
	arcpy.management.DeleteAttributeRule(args.in_table, rule_name, rule_type)


def _diffs(existing: RuleState, desired: RuleState) -> tuple[list[str], list[str]]:
	immutable_diffs: list[str] = []
	mutable_diffs: list[str] = []

	if existing.type != desired.type:
		immutable_diffs.append(f"type: existing={existing.type!r} desired={desired.type!r}")
	if existing.field != desired.field:
		immutable_diffs.append(f"field: existing={existing.field!r} desired={desired.field!r}")
	if existing.subtype != desired.subtype:
		immutable_diffs.append(f"subtype: existing={existing.subtype!r} desired={desired.subtype!r}")
	if existing.is_editable and desired.is_editable and existing.is_editable != desired.is_editable:
		immutable_diffs.append(
			f"is_editable: existing={existing.is_editable!r} desired={desired.is_editable!r}"
		)

	if existing.triggering_events != desired.triggering_events:
		mutable_diffs.append(
			f"triggering_events: existing={existing.triggering_events!r} desired={desired.triggering_events!r}"
		)
	if existing.script_expression != desired.script_expression:
		mutable_diffs.append("script_expression differs")
	if existing.error_number != desired.error_number:
		mutable_diffs.append(
			f"error_number: existing={existing.error_number!r} desired={desired.error_number!r}"
		)
	if existing.error_message != desired.error_message:
		mutable_diffs.append(
			f"error_message: existing={existing.error_message!r} desired={desired.error_message!r}"
		)
	if existing.description != desired.description:
		mutable_diffs.append(
			f"description: existing={existing.description!r} desired={desired.description!r}"
		)

	return immutable_diffs, mutable_diffs


def _log_deploy_context(
	args: argparse.Namespace,
	arcade_path: Path,
	rule_name: str,
	desired: RuleState,
	existing: RuleState | None,
	immutable_diffs: list[str],
	mutable_diffs: list[str],
) -> None:
	mode = "Dry run" if args.dry_run else "Apply"
	_log(f"{mode}: {'no changes will be written' if args.dry_run else 'changes will be applied'}")
	_log(f"- mode: {args.mode}")
	_log(f"- in_table: {args.in_table}")
	_log(f"- arcade_path: {arcade_path}")
	_log(f"- rule_name: {rule_name}")
	_log(f"- type: {desired.type}")
	_log(f"- field: {desired.field or '(none)'}")
	_log(f"- subtype: {desired.subtype or '(none)'}")
	_log(f"- is_editable: {desired.is_editable}")
	_log(f"- triggering_events: {desired.triggering_events or '(none)'}")
	_log(f"- existing_rule_found: {'yes' if existing else 'no'}")

	if existing:
		if not immutable_diffs and not mutable_diffs:
			_log("- diff: no changes")
		else:
			for item in immutable_diffs:
				_log(f"- immutable_diff: {item}")
			for item in mutable_diffs:
				_log(f"- mutable_diff: {item}")


def _run_add_mode(
	args: argparse.Namespace,
	rule_name: str,
	script_text: str,
	existing: RuleState | None,
) -> None:
	if existing:
		raise RuntimeError(
			f"Attribute rule '{rule_name}' already exists on {args.in_table}. "
			"Choose a different --rule-name or run deploy mode."
		)

	if args.dry_run:
		_log(f"WOULD ADD: {rule_name}")
		return

	_log(f"Adding rule '{rule_name}' from script")
	_add_attribute_rule(args, script_text, rule_name)
	_log(f"Successfully added attribute rule '{rule_name}' to: {args.in_table}")


def _run_alter_mode(
	args: argparse.Namespace,
	rule_name: str,
	script_text: str,
	existing: RuleState | None,
	immutable_diffs: list[str],
	mutable_diffs: list[str],
) -> None:
	if not existing:
		raise RuntimeError(
			f"Attribute rule '{rule_name}' does not exist on {args.in_table}. "
			"Use --mode deploy or --mode add instead."
		)
	if immutable_diffs:
		raise RuntimeError(
			"Alter mode cannot apply immutable changes:\n"
			+ "\n".join(f"- {item}" for item in immutable_diffs)
		)
	if not mutable_diffs:
		_log(f"No-op: rule '{rule_name}' already matches desired state")
		return

	if args.dry_run:
		_log(f"WOULD ALTER: {rule_name}")
		return

	_log(f"Altering rule '{rule_name}'")
	_alter_attribute_rule(args, script_text, rule_name)
	_log(f"Successfully altered attribute rule '{rule_name}' on: {args.in_table}")


def _run_deploy_mode(
	args: argparse.Namespace,
	rule_name: str,
	script_text: str,
	existing: RuleState | None,
	immutable_diffs: list[str],
	mutable_diffs: list[str],
) -> None:
	if not existing:
		if args.dry_run:
			_log(f"WOULD ADD: {rule_name}")
			return
		_log(f"Deploy action: ADD '{rule_name}'")
		_add_attribute_rule(args, script_text, rule_name)
		_log(f"Successfully added attribute rule '{rule_name}' to: {args.in_table}")
		return

	if immutable_diffs:
		if args.no_recreate:
			raise RuntimeError(
				"Immutable differences found and --no-recreate was specified:\n"
				+ "\n".join(f"- {item}" for item in immutable_diffs)
			)
		if args.dry_run:
			_log(f"WOULD RECREATE: {rule_name}")
			return
		_log(f"Deploy action: RECREATE '{rule_name}' (delete + add)")
		_delete_attribute_rule(args, rule_name, existing.type)
		_add_attribute_rule(args, script_text, rule_name)
		_log(f"Successfully recreated attribute rule '{rule_name}' on: {args.in_table}")
		return

	if not mutable_diffs:
		_log(f"No-op: rule '{rule_name}' already matches desired state")
		return

	if args.dry_run:
		_log(f"WOULD ALTER: {rule_name}")
		return

	_log(f"Deploy action: ALTER '{rule_name}'")
	_alter_attribute_rule(args, script_text, rule_name)
	_log(f"Successfully altered attribute rule '{rule_name}' on: {args.in_table}")


def main(argv: list[str] | None = None) -> None:
	args = _parse_args(argv)

	if not arcpy.Exists(args.in_table):
		raise RuntimeError(f"Target dataset does not exist: {args.in_table}")

	_validate_in_table(args.in_table)
	_warn_enterprise_preconditions(args.in_table, _normalize_type(args.type))

	arcade_path = _resolve_arcade_path(args.script_name, args.folder)
	rule_name = args.rule_name or _default_rule_name_from_stem(arcade_path.stem)
	script_text = arcade_path.read_text(encoding="utf-8")

	rules = _get_rule_states(args.in_table)
	existing = rules.get(_normalize_rule_name_for_lookup(rule_name))
	desired = _rule_state_from_args(args, rule_name, script_text)
	immutable_diffs: list[str] = []
	mutable_diffs: list[str] = []
	if existing is not None:
		immutable_diffs, mutable_diffs = _diffs(existing, desired)

	_log_deploy_context(
		args=args,
		arcade_path=arcade_path,
		rule_name=rule_name,
		desired=desired,
		existing=existing,
		immutable_diffs=immutable_diffs,
		mutable_diffs=mutable_diffs,
	)

	if args.mode == "add":
		_run_add_mode(args, rule_name, script_text, existing)
		return
	if args.mode == "alter":
		_run_alter_mode(args, rule_name, script_text, existing, immutable_diffs, mutable_diffs)
		return
	_run_deploy_mode(args, rule_name, script_text, existing, immutable_diffs, mutable_diffs)


if __name__ == "__main__":
	main()