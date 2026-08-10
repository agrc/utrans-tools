"""Command-line interface for UTRANS tools."""

from __future__ import annotations

import argparse
import sys

from utrans import __version__
from utrans.etl import main as etl_main
from utrans.recent_edits import main as recent_edits_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="utrans",
        description="Tools for working with UTRANS data.",
    )
    parser.add_argument("--version", action="version", version=f"utrans {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "get-recent-edits",
        help="Detect changed county roads between update and baseline feature classes.",
    )
    subparsers.add_parser(
        "etl",
        help="Transform county roads into the UTRANS schema.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if not arguments:
        parser.print_help(sys.stderr)
        return 2

    if arguments[0] == "get-recent-edits":
        print(f"utrans {__version__}")
        return recent_edits_main(arguments[1:], prog="utrans get-recent-edits")
    if arguments[0] == "etl":
        print(f"utrans {__version__}")
        return etl_main(arguments[1:], prog="utrans etl")

    try:
        parser.parse_args(arguments)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
