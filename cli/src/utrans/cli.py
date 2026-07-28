"""Command-line interface for UTRANS tools."""

from __future__ import annotations

import argparse
import sys

from utrans import recent_edits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utrans",
        description="Tools for working with UTRANS data.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "get-recent-edits",
        help="Detect changed county roads between update and baseline feature classes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if not arguments:
        parser.print_help(sys.stderr)
        return 2

    if arguments[0] == "get-recent-edits":
        return recent_edits.main(arguments[1:], prog="utrans get-recent-edits")

    parser.parse_args(arguments)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
