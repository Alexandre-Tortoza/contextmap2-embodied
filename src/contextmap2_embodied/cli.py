"""Small CLI for validating repository-level contracts."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import ValidationError

from contextmap2_embodied.contracts import MissionPlan


def package_version() -> str:
    """Return the installed package version, including editable installs."""
    try:
        return version("contextmap2-embodied")
    except PackageNotFoundError:
        return "0.1.0.dev0"


def validate_plan(path: Path) -> int:
    """Validate and normalize a MissionPlan JSON document."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        plan = MissionPlan.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"invalid mission plan: {error}")
        return 2

    print(plan.model_dump_json(indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(prog="contextmap2-embodied")
    parser.add_argument("--version", action="version", version=package_version())

    subparsers = parser.add_subparsers(dest="command")
    validate = subparsers.add_parser("validate-plan", help="validate a MissionPlan JSON file")
    validate.add_argument("path", type=Path)

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "validate-plan":
        return validate_plan(args.path)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
