"""Command line interface for pisama-verifier-gym."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

from .agreement import (
    AgreementStats,
    VerdictBalance,
    agreement_table,
    load_verdict_rows,
    verdict_balance,
)
from .assets import load_builtin_verdicts
from .compare import ComparisonRow, GateIssue, compare_artifacts, gate_artifacts
from .exporters import DEFAULT_DETECTORS, export_calibration_report, positive_rich_manifest
from .render import render_artifact
from .schema import ValidationIssue, has_errors, load_artifact, validate_artifact, write_artifact


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "agreement":
        return _run_agreement(args)

    if args.command == "validate":
        return _run_validate(args)

    if args.command == "compare":
        return _run_compare(args)

    if args.command == "gate":
        return _run_gate(args)

    if args.command == "render":
        return _run_render(args)

    if args.command == "export-calibration":
        return _run_export_calibration(args)

    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pisama-verifier-gym",
        description="Audit verifier verdict exports and datasheets.",
    )
    subparsers = parser.add_subparsers(dest="command")

    agreement = subparsers.add_parser(
        "agreement",
        help="compute pairwise agreement for a verdict JSONL export",
    )
    agreement.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="optional path to a verdict JSONL export",
    )
    agreement.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )

    validate = subparsers.add_parser("validate", help="validate a Verifier Gym artifact")
    validate.add_argument("path", type=Path)

    compare = subparsers.add_parser("compare", help="compare two Verifier Gym artifacts")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    gate = subparsers.add_parser("gate", help="fail on verifier metric regressions")
    gate.add_argument("baseline", type=Path)
    gate.add_argument("candidate", type=Path)
    gate.add_argument("--max-f1-drop", type=float, default=0.05)
    gate.add_argument("--max-threshold-drift", type=float, default=0.25)
    gate.add_argument("--min-psa", type=float, default=0.05)
    gate.add_argument("--max-psa-drop", type=float, default=0.10)
    gate.add_argument("--max-abstention-spike", type=float, default=0.05)
    gate.add_argument("--allow-fingerprint-change", action="store_true")

    render = subparsers.add_parser("render", help="render a gym artifact as Markdown")
    render.add_argument("path", type=Path)
    render.add_argument("--output", "-o", type=Path)

    export = subparsers.add_parser(
        "export-calibration",
        help="export Pisama calibration reports into the gym contract",
    )
    export.add_argument("calibration_report", type=Path)
    export.add_argument("--llm-report", type=Path)
    export.add_argument("--output", "-o", type=Path)
    export.add_argument("--positive-manifest", type=Path)
    export.add_argument(
        "--detector",
        dest="detectors",
        action="append",
        default=None,
        help="detector to export; repeatable; defaults to Pisama's core verifier set",
    )

    parser.set_defaults(command="agreement")
    return parser


def _run_agreement(args: argparse.Namespace) -> int:
    verdict_rows = load_verdict_rows(args.path) if args.path else load_builtin_verdicts()
    stats = agreement_table(verdict_rows)
    balance = verdict_balance(verdict_rows)
    if args.json:
        print(
            json.dumps(
                _json_payload(len(verdict_rows), stats, balance),
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print_table(len(verdict_rows), stats, balance)
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    validation_issues = validate_artifact(load_artifact(args.path))
    _print_validation(validation_issues)
    return 1 if has_errors(validation_issues) else 0


def _run_compare(args: argparse.Namespace) -> int:
    comparison_rows = compare_artifacts(
        load_artifact(args.baseline),
        load_artifact(args.candidate),
    )
    if args.json:
        print(json.dumps([row.as_dict() for row in comparison_rows], indent=2, sort_keys=True))
    else:
        _print_compare(comparison_rows)
    return 0


def _run_gate(args: argparse.Namespace) -> int:
    gate_issues = gate_artifacts(
        load_artifact(args.baseline),
        load_artifact(args.candidate),
        max_f1_drop=args.max_f1_drop,
        max_threshold_drift=args.max_threshold_drift,
        min_psa=args.min_psa,
        max_psa_drop=args.max_psa_drop,
        max_abstention_spike=args.max_abstention_spike,
        require_same_fingerprint=not args.allow_fingerprint_change,
    )
    _print_gate(gate_issues)
    return 1 if gate_issues else 0


def _run_render(args: argparse.Namespace) -> int:
    markdown = render_artifact(load_artifact(args.path))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


def _run_export_calibration(args: argparse.Namespace) -> int:
    artifact = export_calibration_report(
        args.calibration_report,
        detectors=args.detectors or DEFAULT_DETECTORS,
        llm_report=args.llm_report,
    )
    if args.positive_manifest:
        write_artifact(args.positive_manifest, positive_rich_manifest(artifact))
    if args.output:
        write_artifact(args.output, artifact)
    else:
        print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


def _json_payload(
    row_count: int,
    stats: Sequence[AgreementStats],
    balance: Mapping[str, VerdictBalance],
) -> dict[str, object]:
    return {
        "rows": row_count,
        "agreement": [stat.as_dict() for stat in stats],
        "balance": {vendor: entry.as_dict() for vendor, entry in balance.items()},
    }


def _print_table(
    row_count: int,
    stats: Sequence[AgreementStats],
    balance: Mapping[str, VerdictBalance],
) -> None:
    print(f"rows: {row_count}  models: {', '.join(sorted(balance))}")
    print()
    print(
        f"{'vendor A':<26}"
        f"{'vendor B':<26}"
        f"{'usable n':>9}"
        f"{'raw':>7}"
        f"{'PSA':>7}"
        f"{'kappa':>8}"
    )
    for stat in stats:
        psa = (
            f"{stat.positive_specific_agreement:.2f}"
            if stat.positive_specific_agreement is not None
            else "n/a"
        )
        print(
            f"{stat.vendor_a:<26}"
            f"{stat.vendor_b:<26}"
            f"{stat.usable_n:>9}"
            f"{stat.raw_agreement:>7.2f}"
            f"{psa:>7}"
            f"{stat.cohen_kappa:>8.2f}"
        )
    print()
    for vendor in sorted(balance):
        entry = balance[vendor]
        print(f"{vendor}: {entry.yes} yes, {entry.abstain} abstain, {entry.no} no")


def _print_validation(issues: Sequence[ValidationIssue]) -> None:
    if not issues:
        print("validation OK")
        return
    for issue in issues:
        print(f"{issue.severity}: {issue.path}: {issue.message}")


def _print_compare(rows: Sequence[ComparisonRow]) -> None:
    if not rows:
        print("no matching verifiers")
        return
    print(f"{'verifier':<34}{'f1':>10}{'precision':>12}{'recall':>10}{'threshold':>12}")
    for row in rows:
        print(
            f"{row.verifier_id:<34}"
            f"{_fmt_delta(row.f1_delta):>10}"
            f"{_fmt_delta(row.precision_delta):>12}"
            f"{_fmt_delta(row.recall_delta):>10}"
            f"{_fmt_delta(row.threshold_delta):>12}"
        )


def _print_gate(issues: Sequence[GateIssue]) -> None:
    if not issues:
        print("gate OK")
        return
    for issue in issues:
        print(f"{issue.severity}: {issue.verifier_id}: {issue.metric}: {issue.message}")


def _fmt_delta(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
