"""Render Verifier Gym artifacts as Markdown datasheets."""

from __future__ import annotations

from typing import Any, Mapping, cast


def render_artifact(artifact: Mapping[str, Any]) -> str:
    """Render a machine-generated Markdown datasheet."""
    lines = [
        "# Verifier Gym datasheet",
        "",
        f"Generated at: `{artifact.get('generated_at', 'unknown')}`",
        f"Schema: `{artifact.get('schema_version', 'unknown')}`",
        "",
    ]
    for verifier in artifact.get("verifiers", []):
        if isinstance(verifier, Mapping):
            lines.extend(_render_verifier(verifier))
    return "\n".join(lines).rstrip() + "\n"


def _render_verifier(verifier: Mapping[str, Any]) -> list[str]:
    metrics = _as_mapping(verifier.get("metrics"))
    dataset = _as_mapping(verifier.get("dataset"))
    publication = _as_mapping(verifier.get("publication"))
    visibility = _as_mapping(verifier.get("input_visibility"))
    lane_policy = _as_mapping(verifier.get("lane_policy"))
    challenge = _as_mapping(verifier.get("challenge_suite"))

    return [
        f"## {verifier.get('name', 'unknown')} ({verifier.get('kind', 'unknown')})",
        "",
        "### Identity",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Verifier id | `{verifier.get('id', 'unknown')}` |",
        f"| Version | `{verifier.get('version', 'unknown')}` |",
        f"| Rubric lineage | {verifier.get('rubric_lineage', 'unknown')} |",
        f"| Scope claim | {verifier.get('scope_claim', 'unknown')} |",
        "",
        "### Dataset",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Dataset | {dataset.get('name', 'unknown')} |",
        f"| Fingerprint | `{dataset.get('fingerprint_id', 'unknown')}` |",
        f"| Total rows | {dataset.get('total_rows', 'unknown')} |",
        f"| Synthetic rows | {dataset.get('synthetic_rows', 'unknown')} |",
        f"| Published metrics | {publication.get('published_metrics', False)} |",
        "",
        "### Visibility And Lane Policy",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Input visibility | {visibility.get('policy', 'unknown')} |",
        f"| Raw input included | {visibility.get('raw_input_included', False)} |",
        "| Synthetic excluded from published metrics | "
        f"{lane_policy.get('synthetic_lanes_excluded_from_published_metrics', False)} |",
        "",
        "### Metrics",
        "",
        _metrics_table(metrics),
        "",
        "### Positive-Rich Suite",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Status | {challenge.get('status', 'not_available')} |",
        f"| Positive count | {challenge.get('positive_count', 0)} |",
        "",
        "### Honest Reading",
        "",
        str(verifier.get("honest_reading", "unknown")),
        "",
        "### Known Limits",
        "",
        _limits(verifier.get("known_limits")),
        "",
    ]


def _metrics_table(metrics: Mapping[str, Any]) -> str:
    keys = [
        "sample_count",
        "f1",
        "precision",
        "recall",
        "optimal_threshold",
        "true_positives",
        "false_positives",
        "false_negatives",
        "true_negatives",
    ]
    lines = ["| Metric | Value |", "|---|---:|"]
    for key in keys:
        if key in metrics:
            lines.append(f"| {key} | {metrics[key]} |")
    return "\n".join(lines)


def _limits(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "- None recorded."
    return "\n".join(f"- {item}" for item in value)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}
