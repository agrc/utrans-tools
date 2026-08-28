"""Deploy every attribute rule script under attribute-rules using script metadata.

Each .arcade file is assigned a rule type by its first folder: calculation,
constraint, or validation. Optional // KEY: value metadata comments override
the remaining deployment settings without requiring per-rule command-line args.

USAGE: python attribute-rules/deploy_all_ar.py --in-table "Z:/data/County.gdb/Roads"
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from deploy_ar import ATTRIBUTE_RULES_ROOT, main as deploy_rule


TYPE_BY_FOLDER = {
	"calculation": "CALCULATION",
	"constraint": "CONSTRAINT",
	"validation": "VALIDATION",
}
METADATA_PATTERN = re.compile(r"^\s*//\s*([A-Z][A-Z0-9_ ]*)\s*:\s*(.*?)\s*$")


@dataclass(frozen=True)
class RuleDeployment:
	arcade_path: Path
	rule_type: str
	metadata: dict[str, str]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Idempotently deploy every .arcade attribute rule under attribute-rules.",
	)
	parser.add_argument(
		"--in-table",
		required=True,
		help="Target feature class or table where all rules will be managed.",
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Preview each deploy action without writing changes.",
	)
	parser.add_argument(
		"--no-recreate",
		action="store_true",
		help="Fail rather than delete and recreate a rule with immutable differences.",
	)
	return parser.parse_args(argv)


def _read_metadata(arcade_path: Path) -> dict[str, str]:
	metadata: dict[str, str] = {}
	for line in arcade_path.read_text(encoding="utf-8").splitlines():
		match = METADATA_PATTERN.match(line)
		if match is None:
			continue
		key = re.sub(r"\s+", "_", match.group(1).strip())
		metadata[key] = match.group(2).strip()
	return metadata


def _rule_type_for_path(arcade_path: Path) -> str:
	try:
		category = arcade_path.relative_to(ATTRIBUTE_RULES_ROOT).parts[0].casefold()
	except (ValueError, IndexError) as error:
		raise ValueError(f"Cannot determine rule type for {arcade_path}") from error

	try:
		return TYPE_BY_FOLDER[category]
	except KeyError as error:
		allowed = ", ".join(sorted(TYPE_BY_FOLDER))
		raise ValueError(
			f"{arcade_path} must be below one of these folders: {allowed}"
		) from error


def _discover_rules() -> list[RuleDeployment]:
	rules: list[RuleDeployment] = []
	for arcade_path in sorted(ATTRIBUTE_RULES_ROOT.rglob("*.arcade")):
		rules.append(
			RuleDeployment(
				arcade_path=arcade_path,
				rule_type=_rule_type_for_path(arcade_path),
				metadata=_read_metadata(arcade_path),
			)
		)
	if not rules:
		raise RuntimeError(f"No .arcade scripts found under {ATTRIBUTE_RULES_ROOT}")
	return rules


def _normalize_events(events: str) -> str:
	return ";".join(part.strip().upper() for part in re.split(r"[;,]", events) if part.strip())


def _deployment_argv(deployment: RuleDeployment, args: argparse.Namespace) -> list[str]:
	metadata = deployment.metadata
	folder = deployment.arcade_path.parent.relative_to(ATTRIBUTE_RULES_ROOT).as_posix()
	argv = [
		deployment.arcade_path.name,
		"--in-table",
		args.in_table,
		"--mode",
		"deploy",
		"--folder",
		folder,
		"--type",
		metadata.get("TYPE", deployment.rule_type).upper(),
	]

	if metadata.get("TYPE", deployment.rule_type).upper() != deployment.rule_type:
		raise ValueError(
			f"{deployment.arcade_path}: TYPE must match its {deployment.rule_type.lower()} folder"
		)

	for metadata_key, option in (
		("RULE_NAME", "--rule-name"),
		("FIELD", "--field"),
		("EVENTS", "--triggering-events"),
		("IS_EDITABLE", "--is-editable"),
		("ERROR_NUMBER", "--error-number"),
		("ERROR_MESSAGE", "--error-message"),
		("DESCRIPTION", "--description"),
		("SUBTYPE", "--subtype"),
	):
		if metadata_key in metadata:
			value = metadata[metadata_key]
			if metadata_key == "EVENTS":
				value = _normalize_events(value)
			argv.extend([option, value])
 
	if args.dry_run:
		argv.append("--dry-run")
	if args.no_recreate:
		argv.append("--no-recreate")
	return argv


def main(argv: list[str] | None = None) -> None:
	args = _parse_args(argv)
	rules = _discover_rules()

	# Build every command before changing the target so invalid metadata fails cleanly.
	deployments = [(rule, _deployment_argv(rule, args)) for rule in rules]
	print(f"Deploying {len(deployments)} attribute rule(s) to: {args.in_table}", flush=True)
	for deployment, deploy_argv in deployments:
		print(f"\n=== {deployment.arcade_path.relative_to(ATTRIBUTE_RULES_ROOT)} ===", flush=True)
		deploy_rule(deploy_argv)


if __name__ == "__main__":
	main()