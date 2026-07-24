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
    _validate_root(artifact, issues)

    verifiers = artifact.get("verifiers")
    if not isinstance(verifiers, list) or not verifiers:
        issues.append(_issue("verifiers", "must be a non-empty list"))
        return issues

    _validate_verifiers(verifiers, issues)
    return issues


def _validate_root(
    artifact: Mapping[str, Any],
    issues: list[ValidationIssue],
) -> None:
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        issues.append(_issue("artifact_type", f"must be {ARTIFACT_TYPE!r}"))
    if artifact.get("schema_version") != SCHEMA_VERSION:
        issues.append(_issue("schema_version", f"must be {SCHEMA_VERSION!r}"))
    if not _non_empty(artifact.get("generated_at")):
        issues.append(_issue("generated_at", "is required"))
    _validate_source_reports(artifact.get("source_reports"), issues)


def _validate_verifiers(
    verifiers: list[Any],
    issues: list[ValidationIssue],
) -> None:
    verifier_ids: set[str] = set()
    for index, record in enumerate(verifiers):
        path = f"verifiers[{index}]"
        if not isinstance(record, Mapping):
            issues.append(_issue(path, "must be an object"))
            continue
        _validate_verifier(record, path, issues)
        verifier_id = record.get("id")
        if isinstance(verifier_id, str) and verifier_id in verifier_ids:
            issues.append(_issue(f"{path}.id", f"duplicates verifier id {verifier_id!r}"))
        elif isinstance(verifier_id, str):
            verifier_ids.add(verifier_id)


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
    if visibility is not None:
        _validate_visibility(visibility, f"{path}.input_visibility", issues)

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
    if lane_policy is not None:
        _validate_lane_policy(lane_policy, f"{path}.lane_policy", issues)
    if publication is not None:
        _validate_publication(publication, f"{path}.publication", issues)

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
    _validate_optional_count(dataset, "total_rows", path, issues)
    _validate_optional_count(dataset, "synthetic_rows", path, issues)
    total_rows = _integer(dataset.get("total_rows"))
    synthetic_rows = _integer(dataset.get("synthetic_rows"))
    if total_rows is not None and synthetic_rows is not None and synthetic_rows > total_rows:
        issues.append(_issue(f"{path}.synthetic_rows", "cannot exceed total_rows"))


def _validate_visibility(
    visibility: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not _non_empty(visibility.get("policy")):
        issues.append(_issue(f"{path}.policy", "is required"))
    raw_input_included = visibility.get("raw_input_included")
    if raw_input_included is not None and not isinstance(raw_input_included, bool):
        issues.append(_issue(f"{path}.raw_input_included", "must be a boolean when set"))
    fields_seen = visibility.get("fields_seen")
    if fields_seen is not None and not _string_list(fields_seen):
        issues.append(_issue(f"{path}.fields_seen", "must be a list of non-empty strings when set"))


def _validate_lane_policy(
    lane_policy: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not _string_list(lane_policy.get("published_metric_lanes")):
        issues.append(_issue(f"{path}.published_metric_lanes", "must be a non-empty string list"))
    if not isinstance(
        lane_policy.get("synthetic_lanes_excluded_from_published_metrics"),
        bool,
    ):
        issues.append(
            _issue(
                f"{path}.synthetic_lanes_excluded_from_published_metrics",
                "must be a boolean",
            )
        )


def _validate_publication(
    publication: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(publication.get("published_metrics"), bool):
        issues.append(_issue(f"{path}.published_metrics", "must be a boolean"))


def _validate_metrics(
    metrics: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    count_metrics = (
        "sample_count",
        "positive_count",
        "negative_count",
        "true_positives",
        "false_positives",
        "false_negatives",
        "true_negatives",
    )
    for key in count_metrics:
        _validate_optional_count(metrics, key, path, issues)

    unit_metrics = (
        "f1",
        "precision",
        "recall",
        "f1_ci_lower",
        "f1_ci_upper",
        "always_fire_f1",
        "optimal_threshold",
    )
    for key in unit_metrics:
        value = metrics.get(key)
        if value is not None and (_number(value) is None or not 0 <= float(value) <= 1):
            issues.append(_issue(f"{path}.{key}", "must be a number between 0 and 1 when set"))


def _validate_optional_count(
    values: Mapping[str, Any],
    key: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    value = values.get(key)
    if value is not None and (_integer(value) is None or value < 0):
        issues.append(_issue(f"{path}.{key}", "must be a non-negative integer when set"))


def _validate_source_reports(value: Any, issues: list[ValidationIssue]) -> None:
    if value is not None and not _string_list(value, allow_empty=True):
        issues.append(_issue("source_reports", "must be a list of non-empty strings when set"))


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
    explicit = _integer(dataset.get("synthetic_rows"))
    if explicit is not None:
        return explicit

    total = 0
    composition = dataset.get("source_composition")
    if isinstance(composition, Mapping):
        for name, payload in composition.items():
            if "synthetic" not in str(name).lower() and "synth" not in str(name).lower():
                continue
            if isinstance(payload, Mapping) and _integer(payload.get("rows")) is not None:
                total += int(payload["rows"])
    return total


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_non_empty(item) for item in value)
    )


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _issue(
    path: str, message: str, severity: Literal["error", "warning"] = "error"
) -> ValidationIssue:
    return ValidationIssue(path=path, message=message, severity=severity)
