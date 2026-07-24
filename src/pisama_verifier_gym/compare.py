"""Comparison and regression gates for Verifier Gym artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ComparisonRow:
    """Metric delta for one verifier."""

    verifier_id: str
    fingerprint_id: str | None
    baseline_fingerprint_id: str | None
    f1_delta: float | None = None
    precision_delta: float | None = None
    recall_delta: float | None = None
    threshold_delta: float | None = None
    psa_delta: float | None = None
    abstention_delta: float | None = None
    baseline_psa_min: float | None = None
    candidate_psa_min: float | None = None
    baseline_abstention_max: float | None = None
    candidate_abstention_max: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GateIssue:
    """One blocking or advisory gate result."""

    verifier_id: str
    metric: str
    message: str
    severity: str = "error"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def compare_artifacts(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> list[ComparisonRow]:
    """Compare matching verifier records in two artifacts."""
    baseline_map = _verifier_map(baseline)
    rows = []
    for verifier_id, current in _verifier_map(candidate).items():
        previous = baseline_map.get(verifier_id)
        if previous is None:
            continue
        rows.append(_compare_record(verifier_id, previous, current))
    return rows


def gate_artifacts(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    max_f1_drop: float = 0.05,
    max_threshold_drift: float = 0.25,
    min_psa: float = 0.05,
    max_psa_drop: float = 0.10,
    max_abstention_spike: float = 0.05,
    require_same_fingerprint: bool = True,
) -> list[GateIssue]:
    """Return regression gate issues. Empty means pass."""
    issues: list[GateIssue] = []
    for row in compare_artifacts(baseline, candidate):
        _gate_fingerprint(row, require_same_fingerprint, issues)
        _gate_delta(row, "f1", row.f1_delta, -max_f1_drop, issues)
        _gate_abs_delta(row, "optimal_threshold", row.threshold_delta, max_threshold_drift, issues)
        _gate_psa(row, min_psa, max_psa_drop, issues)
        _gate_delta(row, "abstention_rate", row.abstention_delta, max_abstention_spike, issues)
    return issues


def _compare_record(
    verifier_id: str,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> ComparisonRow:
    baseline_psa = _agreement_extreme(baseline, "positive_specific_agreement", min)
    candidate_psa = _agreement_extreme(candidate, "positive_specific_agreement", min)
    baseline_abstention = _agreement_extreme(baseline, "abstention_rate", max)
    candidate_abstention = _agreement_extreme(candidate, "abstention_rate", max)

    return ComparisonRow(
        verifier_id=verifier_id,
        fingerprint_id=_fingerprint(candidate),
        baseline_fingerprint_id=_fingerprint(baseline),
        f1_delta=_metric_delta(baseline, candidate, "f1"),
        precision_delta=_metric_delta(baseline, candidate, "precision"),
        recall_delta=_metric_delta(baseline, candidate, "recall"),
        threshold_delta=_metric_delta(baseline, candidate, "optimal_threshold"),
        psa_delta=_delta(baseline_psa, candidate_psa),
        abstention_delta=_delta(baseline_abstention, candidate_abstention),
        baseline_psa_min=baseline_psa,
        candidate_psa_min=candidate_psa,
        baseline_abstention_max=baseline_abstention,
        candidate_abstention_max=candidate_abstention,
    )


def _gate_fingerprint(
    row: ComparisonRow,
    require_same: bool,
    issues: list[GateIssue],
) -> None:
    if require_same and row.fingerprint_id != row.baseline_fingerprint_id:
        issues.append(
            GateIssue(
                verifier_id=row.verifier_id,
                metric="fingerprint_id",
                message=(
                    f"candidate fingerprint {row.fingerprint_id} differs from "
                    f"baseline {row.baseline_fingerprint_id}"
                ),
            )
        )


def _gate_delta(
    row: ComparisonRow,
    metric: str,
    delta: float | None,
    threshold: float,
    issues: list[GateIssue],
) -> None:
    if delta is None:
        return
    if threshold < 0 and delta < threshold:
        issues.append(_delta_issue(row, metric, delta, threshold))
    if threshold > 0 and delta > threshold:
        issues.append(_delta_issue(row, metric, delta, threshold))


def _gate_abs_delta(
    row: ComparisonRow,
    metric: str,
    delta: float | None,
    threshold: float,
    issues: list[GateIssue],
) -> None:
    if delta is not None and abs(delta) > threshold:
        issues.append(_delta_issue(row, metric, delta, threshold))


def _gate_psa(
    row: ComparisonRow,
    min_psa: float,
    max_drop: float,
    issues: list[GateIssue],
) -> None:
    if row.candidate_psa_min is not None and row.candidate_psa_min < min_psa:
        issues.append(
            GateIssue(
                verifier_id=row.verifier_id,
                metric="positive_specific_agreement",
                message=f"minimum PSA {row.candidate_psa_min:.4f} fell below floor {min_psa:.4f}",
            )
        )
    if row.psa_delta is not None and row.psa_delta < -max_drop:
        issues.append(_delta_issue(row, "positive_specific_agreement", row.psa_delta, -max_drop))


def _delta_issue(row: ComparisonRow, metric: str, delta: float, threshold: float) -> GateIssue:
    return GateIssue(
        verifier_id=row.verifier_id,
        metric=metric,
        message=f"delta {delta:+.4f} exceeded threshold {threshold:+.4f}",
    )


def _metric_delta(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metric: str,
) -> float | None:
    before = _number((baseline.get("metrics") or {}).get(metric))
    after = _number((candidate.get("metrics") or {}).get(metric))
    if before is None or after is None:
        return None
    return after - before


def _delta(before: float | None, after: float | None) -> float | None:
    if before is None or after is None:
        return None
    return after - before


def _agreement_extreme(
    record: Mapping[str, Any],
    metric: str,
    selector: Any,
) -> float | None:
    agreement = record.get("agreement")
    if not isinstance(agreement, Mapping):
        return None
    values = []
    for row in agreement.get("pairwise", []):
        if isinstance(row, Mapping):
            value = _number(row.get(metric))
            if value is not None:
                values.append(value)
    return selector(values) if values else None


def _fingerprint(record: Mapping[str, Any]) -> str | None:
    dataset = record.get("dataset")
    if not isinstance(dataset, Mapping):
        return None
    value = dataset.get("fingerprint_id")
    return str(value) if value is not None else None


def _verifier_map(artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    for record in artifact.get("verifiers", []):
        if isinstance(record, Mapping) and record.get("id"):
            records[str(record["id"])] = record
    return records


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None
