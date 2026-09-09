from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .experiments import (
    acquire,
    audit_configuration,
    profile_cases,
    required_run_failures,
    run_experiments,
    verify_result_rows,
    write_report,
)
from .inputs import load_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collective-phase",
        description="Compile and assess equal-angle diagonal parity-phase blocks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("audit", "validate configuration, dependencies, and input readiness"),
        ("acquire", "download checksum-pinned public inputs without overwriting"),
        ("profile", "write structural diagnosis for all manifest cases"),
        ("run", "compile, verify, lower, and checkpoint experiment rows"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--config", required=True, help="YAML experiment configuration")
        if name == "run":
            command.add_argument(
                "--force",
                action="store_true",
                help="rebuild JSON checkpoints in the configured results directory",
            )
    verify = subparsers.add_parser("verify", help="validate stored result and circuit artifacts")
    verify.add_argument("--results", required=True, help="directory containing result JSON rows")
    report = subparsers.add_parser("report", help="write a concise Markdown result summary")
    report.add_argument("--results", required=True, help="directory containing result JSON rows")
    report.add_argument("--output", help="output Markdown path (default: RESULTS/report.md)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command in {"audit", "acquire", "profile", "run"}:
        config = load_config(args.config)
    if args.command == "audit":
        result = audit_configuration(config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["basic_run_ready"] else 2
    if args.command == "acquire":
        print(json.dumps(acquire(config), indent=2, sort_keys=True))
        return 0
    if args.command == "profile":
        result = profile_cases(config)
        print(
            json.dumps(
                {"profiled_cases": len(result), "output": config["diagnosis_path"]},
                indent=2,
            )
        )
        return 0
    if args.command == "run":
        rows = run_experiments(config, force=args.force)
        failures = required_run_failures(rows, config)
        print(
            json.dumps(
                {
                    "rows": len(rows),
                    "results": config["results_dir"],
                    "required_gate_failures": failures,
                },
                indent=2,
            )
        )
        return 0 if not failures else 2
    if args.command == "verify":
        result = verify_result_rows(Path(args.results).resolve(), Path.cwd().resolve())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "verified" else 2
    if args.command == "report":
        verification = verify_result_rows(
            Path(args.results).resolve(), Path.cwd().resolve()
        )
        if verification["status"] != "verified":
            print(json.dumps(verification, indent=2, sort_keys=True))
            return 2
        destination = write_report(args.results, args.output)
        print(destination)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
