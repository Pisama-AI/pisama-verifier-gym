"""Export Pisama calibration reports into Verifier Gym artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import ARTIFACT_TYPE, SCHEMA_VERSION

DEFAULT_DETECTORS = ("derailment", "completion", "hallucination", "decomposition")

RUBRIC_LINEAGE = {
    "derailment": "MAST failure taxonomy F6 task derailment",
    "completion": "MAST failure taxonomy completion and under-delivery verifier",
    "hallucination": "MAST failure taxonomy hallucination and grounding verifier",
    "decomposition": "MAST failure taxonomy task decomposition verifier",
    "analytical_semantics": "Pisama LLM judge rubric for analytical semantic errors",
    "specification_compliance": "Pisama LLM judge rubric for specification compliance",
}


def export_calibration_report(
    calibration_report: str | Path,
    detectors: Sequence[str] = DEFAULT_DETECTORS,
    llm_report: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a Verifier Gym artifact from Pisama calibration reports."""
    report_path = Path(calibration_report)
    report = _load_json(report_path)
    verifiers = [
        _build_verifier(
            detector=detector,
            result=result,
            report=report,
            source_report=str(report_path),
            kind="detector",
            sample_predictions=report.get("sample_predictions"),
        )
        for detector, result in _selected_results(report, detectors)
    ]

    source_reports = [str(report_path)]
    if llm_report is not None:
        llm_path = Path(llm_report)
        llm = _load_json(llm_path)
        source_reports.append(str(llm_path))
        for detector, result in _selected_results(llm, sorted((llm.get("results") or {}).keys())):
            verifiers.append(
                _build_verifier(
                    detector=detector,
                    result=result,
                    report=llm,
                    source_report=str(llm_path),
                    kind="llm_judge",
                    sample_predictions=None,
                )
            )

    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _generated_at(report),
        "source_reports": source_reports,
        "verifiers": verifiers,
    }


def positive_rich_manifest(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Extract positive-rich suite summaries from a gym artifact."""
    suites = []
    for verifier in artifact.get("verifiers", []):
        if not isinstance(verifier, Mapping):
            continue
        suite = verifier.get("challenge_suite")
        if isinstance(suite, Mapping) and suite.get("positive_count"):
            suites.append(
                {
                    "verifier_id": verifier.get("id"),
                    "verifier_name": verifier.get("name"),
                    "fingerprint_id": (verifier.get("dataset") or {}).get("fingerprint_id"),
                    **suite,
                }
            )
    return {
        "artifact_type": "pisama_verifier_gym_positive_rich_manifest",
        "schema_version": SCHEMA_VERSION,
        "generated_at": artifact.get("generated_at"),
        "suites": suites,
    }


def _selected_results(
    report: Mapping[str, Any],
    detectors: Sequence[str],
) -> list[tuple[str, Mapping[str, Any]]]:
    results = report.get("results")
    if not isinstance(results, Mapping):
        return []
    selected = []
    for detector in detectors:
        value = results.get(detector)
        if isinstance(value, Mapping):
            selected.append((detector, value))
    return selected


def _build_verifier(
    *,
    detector: str,
    result: Mapping[str, Any],
    report: Mapping[str, Any],
    source_report: str,
    kind: str,
    sample_predictions: Any,
) -> dict[str, Any]:
    fingerprint = _fingerprint(report)
    published = bool(report.get("external_only") or fingerprint.get("external_only"))
    challenge_suite = _challenge_suite(detector, sample_predictions)
    return {
        "id": f"{kind}.{detector}",
        "name": detector,
        "kind": kind,
        "version": str(report.get("calibrated_at") or report.get("timestamp") or "unknown"),
        "rubric_lineage": RUBRIC_LINEAGE.get(detector, f"Pisama verifier rubric for {detector}"),
        "where_runs": "Pisama calibration lane",
        "scope_claim": _scope_claim(detector, result, kind),
        "dataset": _dataset_contract(report, detector),
        "input_visibility": {
            "policy": "sanitized calibration summaries only",
            "raw_input_included": False,
            "fields_seen": ["entry_id", "detection_type", "expected", "prediction", "confidence"],
            "truncation": "raw trace text is not exported into Verifier Gym artifacts",
        },
        "lane_policy": {
            "published_metric_lanes": ["external"] if published else ["internal"],
            "synthetic_lanes_excluded_from_published_metrics": published,
        },
        "publication": {
            "published_metrics": published,
            "public_claim": "external-only calibration metric" if published else None,
        },
        "metrics": _metrics(result),
        "agreement": _agreement_placeholder(kind),
        "adjudication": {"status": "not_recorded_in_source_report"},
        "challenge_suite": challenge_suite,
        "source_report": source_report,
        "honest_reading": _honest_reading(detector, result),
        "known_limits": _known_limits(result, challenge_suite, kind),
    }


def _dataset_contract(report: Mapping[str, Any], detector: str) -> dict[str, Any]:
    fingerprint = _fingerprint(report)
    source_composition = fingerprint.get("source_composition")
    composition = source_composition if isinstance(source_composition, Mapping) else {}
    return {
        "name": _dataset_name(report, detector),
        "fingerprint_id": fingerprint.get("fingerprint_id"),
        "content_hash": fingerprint.get("content_hash"),
        "total_rows": fingerprint.get("total_rows"),
        "provenance": _provenance(fingerprint),
        "license": "source-specific; see calibration fingerprint files",
        "synthetic_rows": _synthetic_rows(composition),
        "source_composition": composition,
        "run_filters": fingerprint.get("run_filters"),
    }


def _metrics(result: Mapping[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {"eval_flags": result.get("eval_flags") or []}
    _copy_numbers(metrics, result, ("f1", "precision", "recall", "f1_ci_lower", "f1_ci_upper"))
    _copy_numbers(metrics, result, ("always_fire_f1",))
    _copy_integers(metrics, result, ("positive_count", "negative_count"))
    _copy_first_integer(metrics, result, "sample_count", ("sample_count", "n_entries"))
    _copy_first_number(
        metrics,
        result,
        "optimal_threshold",
        ("optimal_threshold", "threshold", "llm_threshold", "rule_threshold"),
    )
    _copy_first_integer(metrics, result, "true_positives", ("true_positives", "tp"))
    _copy_first_integer(metrics, result, "false_positives", ("false_positives", "fp"))
    _copy_first_integer(metrics, result, "false_negatives", ("false_negatives", "fn"))
    _copy_first_integer(metrics, result, "true_negatives", ("true_negatives", "tn"))
    return {key: value for key, value in metrics.items() if value is not None}


def _challenge_suite(detector: str, sample_predictions: Any) -> dict[str, Any]:
    if not isinstance(sample_predictions, list):
        return {"status": "not_available", "positive_count": 0, "entries": []}

    rows = [
        row for row in sample_predictions
        if isinstance(row, Mapping)
        and row.get("detection_type") == detector
        and row.get("expected") is True
    ]
    entries = [
        {
            "entry_id": row.get("entry_id"),
            "source": row.get("source"),
            "source_dataset": row.get("source_dataset"),
            "difficulty": row.get("difficulty"),
            "classification": row.get("classification"),
            "tags": row.get("tags") or [],
        }
        for row in rows
    ]
    return {
        "status": "ready" if len(entries) >= 30 else "needs_more_positives",
        "positive_count": len(entries),
        "minimum_positive_count": 30,
        "entries": entries,
        "privacy": "entry ids and metadata only; raw input text excluded",
    }


def _agreement_placeholder(kind: str) -> dict[str, Any]:
    if kind == "llm_judge":
        return {"status": "not_exported", "pairwise": []}
    return {"status": "not_applicable_for_single_detector_metric", "pairwise": []}


def _fingerprint(report: Mapping[str, Any]) -> Mapping[str, Any]:
    value = report.get("dataset_fingerprint")
    return value if isinstance(value, Mapping) else {}


def _dataset_name(report: Mapping[str, Any], detector: str) -> str:
    fingerprint = _fingerprint(report)
    filters = fingerprint.get("run_filters")
    if isinstance(filters, Mapping) and filters.get("script"):
        return f"{filters['script']}:{detector}"
    if report.get("run_type"):
        return f"{report['run_type']}:{detector}"
    return f"calibration:{detector}"


def _scope_claim(detector: str, result: Mapping[str, Any], kind: str) -> str:
    f1 = result.get("f1")
    if isinstance(f1, int | float):
        return f"{kind} {detector} measured F1 {f1:.4f} on the declared fingerprint"
    return f"{kind} {detector} measured on the declared fingerprint"


def _honest_reading(detector: str, result: Mapping[str, Any]) -> str:
    flags = result.get("eval_flags") or []
    f1 = result.get("f1")
    sample_count = result.get("sample_count")
    if flags:
        return f"{detector} has caveats in this run: {', '.join(map(str, flags))}."
    if isinstance(f1, int | float) and isinstance(sample_count, int):
        return f"{detector} measured F1 {f1:.4f} on n={sample_count}; read with the lane policy."
    return f"{detector} has an exported measurement; inspect metrics and lane policy before use."


def _known_limits(result: Mapping[str, Any], suite: Mapping[str, Any], kind: str) -> list[str]:
    limits: list[str] = []
    flags = result.get("eval_flags") or []
    limits.extend(str(flag) for flag in flags)
    if suite.get("status") == "needs_more_positives":
        limits.append("positive-rich suite has fewer than 30 positive examples")
    if kind == "llm_judge":
        limits.append("LLM judge agreement panel is not included in this calibration export")
    return limits


def _provenance(fingerprint: Mapping[str, Any]) -> str:
    filters = fingerprint.get("run_filters")
    if isinstance(filters, Mapping) and filters:
        return json.dumps(filters, sort_keys=True)
    return "calibration report dataset fingerprint"


def _synthetic_rows(source_composition: Mapping[str, Any]) -> int:
    return sum(
        int(payload["rows"])
        for name, payload in source_composition.items()
        if (
            _synthetic_source(name)
            and isinstance(payload, Mapping)
            and isinstance(payload.get("rows"), int)
        )
    )


def _copy_numbers(target: dict[str, Any], source: Mapping[str, Any], keys: Sequence[str]) -> None:
    for key in keys:
        target[key] = _number(source.get(key))


def _copy_integers(target: dict[str, Any], source: Mapping[str, Any], keys: Sequence[str]) -> None:
    for key in keys:
        target[key] = _integer(source.get(key))


def _copy_first_number(
    target: dict[str, Any],
    source: Mapping[str, Any],
    target_key: str,
    source_keys: Sequence[str],
) -> None:
    for key in source_keys:
        value = _number(source.get(key))
        if value is not None:
            target[target_key] = value
            return


def _copy_first_integer(
    target: dict[str, Any],
    source: Mapping[str, Any],
    target_key: str,
    source_keys: Sequence[str],
) -> None:
    for key in source_keys:
        value = _integer(source.get(key))
        if value is not None:
            target[target_key] = value
            return


def _synthetic_source(name: object) -> bool:
    normalized = str(name).lower()
    return "synthetic" in normalized or "synth" in normalized


def _generated_at(report: Mapping[str, Any]) -> str:
    value = report.get("calibrated_at") or report.get("timestamp") or report.get("run_date")
    if isinstance(value, str) and value.strip():
        return value
    return datetime.now(timezone.utc).isoformat()


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) else None


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value
