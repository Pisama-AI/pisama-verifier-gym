"""Typed contract and validators for Verifier Gym artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "pisama_verifier_gym"


@dataclass(frozen=True)
class ValidationIssue:
    """One contract validation issue."""

    path: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class DatasetContract:
    """Dataset lineage required to make verifier metrics auditable."""

    name: str
    fingerprint_id: str
    content_hash: str | None = None
    total_rows: int | None = None
    provenance: str = "unknown"
    license: str = "unknown"
    synthetic_rows: int = 0
    source_composition: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InputVisibilityContract:
    """What the verifier saw when it produced verdicts."""

    policy: str
    raw_input_included: bool = False
    fields_seen: list[str] = field(default_factory=list)
    truncation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LanePolicyContract:
    """Rules for which lanes can feed published metrics."""

    published_metric_lanes: list[str]
    synthetic_lanes_excluded_from_published_metrics: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PublicationContract:
    """Publication status for the metric block."""

    published_metrics: bool
    public_claim: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifierRecord:
    """One audited verifier and its latest measurement."""

    id: str
    name: str
    kind: str
    version: str
    rubric_lineage: str
    dataset: DatasetContract
    input_visibility: InputVisibilityContract
    lane_policy: LanePolicyContract
    publication: PublicationContract
    metrics: dict[str, Any]
    agreement: dict[str, Any] = field(default_factory=dict)
    adjudication: dict[str, Any] = field(default_factory=dict)
    challenge_suite: dict[str, Any] = field(default_factory=dict)
    honest_reading: str = "unknown"
    known_limits: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifierGymArtifact:
    """Top-level Verifier Gym artifact."""

    generated_at: str
    verifiers: list[VerifierRecord]
    source_reports: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    artifact_type: str = ARTIFACT_TYPE

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Load a Verifier Gym JSON artifact."""
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return value


def write_artifact(path: str | Path, artifact: Mapping[str, Any]) -> None:
    """Write a Verifier Gym JSON artifact with stable formatting."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_artifact_path(path: str | Path) -> list[ValidationIssue]:
    """Validate an artifact file."""
    return validate_artifact(load_artifact(path))


def validate_artifact(artifact: Mapping[str, Any]) -> list[ValidationIssue]:
    """Validate the Verifier Gym contract.

    The hard failures intentionally match Pisama's internal release discipline:
    no lineage, no fingerprint, no input visibility policy, and no synthetic
    data in published metrics unless the lane policy excludes it.
    """
    issues: list[ValidationIssue] = []

    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        issues.append(_issue("artifact_type", f"must be {ARTIFACT_TYPE!r}"))
    if artifact.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("schema_version", f"must be {SCHEMA_VERSION!r}"))

    verifiers = artifact.get("verifiers")
    if not isinstance(verifiers, list) or not verifiers:
        issues.append(_issue("verifiers", "must be a non-empty list"))
        return issues

    for index, record in enumerate(verifiers):
        path = f"verifiers[{index}]"
        if not isinstance(record, Mapping):
            issues.append(_issue(path, "must be an object"))
            continue
        _validate_verifier(record, path, issues)

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    """Return true when any validation issue is blocking."""
    return any(issue.severity == "error" for issue in issues)


def _validate_verifier(
    record: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    _validate_identity(record, path, issues)

    dataset = _mapping(record.get("dataset"))
    if dataset is not None:
        _validate_dataset(dataset, f"{path}.dataset", issues)

    visibility = _mapping(record.get("input_visibility"))
    if visibility is not None and not _non_empty(visibility.get("policy")):
        issues.append(_issue(f"{path}.input_visibility.policy", "is required"))

    lane_policy = _mapping(record.get("lane_policy"))
    publication = _mapping(record.get("publication"))
    metrics = _mapping(record.get("metrics"))
    _validate_required_mappings(
        path,
        issues,
        {
            "dataset": dataset,
            "input_visibility": visibility,
            "lane_policy": lane_policy,
            "publication": publication,
            "metrics": metrics,
        },
    )
    if metrics is not None:
        _validate_metrics(metrics, f"{path}.metrics", issues)

    if dataset and lane_policy and publication:
        _validate_synthetic_publication(dataset, lane_policy, publication, path, issues)


def _validate_identity(
    record: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    for key in ("id", "name", "kind", "version", "rubric_lineage"):
        if not _non_empty(record.get(key)):
            issues.append(_issue(f"{path}.{key}", "is required"))


def _validate_required_mappings(
    path: str,
    issues: list[ValidationIssue],
    mappings: Mapping[str, Mapping[str, Any] | None],
) -> None:
    for key, value in mappings.items():
        if value is None:
            issues.append(_issue(f"{path}.{key}", "is required"))


def _validate_dataset(
    dataset: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not _non_empty(dataset.get("name")):
        issues.append(_issue(f"{path}.name", "is required"))
    if not _non_empty(dataset.get("fingerprint_id")):
        issues.append(_issue(f"{path}.fingerprint_id", "is required"))
    if dataset.get("total_rows") is not None and not isinstance(dataset.get("total_rows"), int):
        issues.append(_issue(f"{path}.total_rows", "must be an integer when set"))


def _validate_metrics(
    metrics: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    sample_count = metrics.get("sample_count")
    if sample_count is not None and not isinstance(sample_count, int):
        issues.append(_issue(f"{path}.sample_count", "must be an integer when set"))


def _validate_synthetic_publication(
    dataset: Mapping[str, Any],
    lane_policy: Mapping[str, Any],
    publication: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if publication.get("published_metrics") is not True:
        return

    synthetic_rows = _synthetic_rows(dataset)
    excludes_synthetic = lane_policy.get("synthetic_lanes_excluded_from_published_metrics")
    if synthetic_rows > 0 and excludes_synthetic is not True:
        issues.append(
            _issue(
                f"{path}.lane_policy.synthetic_lanes_excluded_from_published_metrics",
                f"published metrics include {synthetic_rows} synthetic rows",
            )
        )


def _synthetic_rows(dataset: Mapping[str, Any]) -> int:
    explicit = dataset.get("synthetic_rows")
    if isinstance(explicit, int):
        return explicit

    total = 0
    composition = dataset.get("source_composition")
    if isinstance(composition, Mapping):
        for name, payload in composition.items():
            if "synthetic" not in str(name).lower() and "synth" not in str(name).lower():
                continue
            if isinstance(payload, Mapping) and isinstance(payload.get("rows"), int):
                total += int(payload["rows"])
    return total


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _issue(
    path: str, message: str, severity: Literal["error", "warning"] = "error"
) -> ValidationIssue:
    return ValidationIssue(path=path, message=message, severity=severity)
