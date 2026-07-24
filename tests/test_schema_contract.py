import json
import subprocess
import sys

import pytest

from pisama_verifier_gym.schema import (
    DatasetContract,
    InputVisibilityContract,
    LanePolicyContract,
    PublicationContract,
    ValidationIssue,
    VerifierGymArtifact,
    VerifierRecord,
    has_errors,
    load_artifact,
    validate_artifact,
    validate_artifact_path,
    write_artifact,
)
from tests.test_schema import valid_artifact


def test_typed_contracts_serialize_all_public_fields():
    dataset = DatasetContract(
        name="WildChat",
        fingerprint_id="sha256:abc123",
        content_hash="abc123",
        total_rows=97,
        provenance="WildChat",
        license="ODC-BY",
        source_composition={"wildchat": {"rows": 97}},
    )
    visibility = InputVisibilityContract(
        policy="full transcript",
        raw_input_included=True,
        fields_seen=["messages"],
    )
    lanes = LanePolicyContract(
        published_metric_lanes=["external"],
        synthetic_lanes_excluded_from_published_metrics=True,
    )
    publication = PublicationContract(
        published_metrics=True,
        public_claim="Agreement audit on 97 WildChat conversations.",
    )
    verifier = VerifierRecord(
        id="judge.derailment",
        name="derailment",
        kind="llm_judge",
        version="2026-07",
        rubric_lineage="Pisama derailment rubric",
        dataset=dataset,
        input_visibility=visibility,
        lane_policy=lanes,
        publication=publication,
        metrics={"sample_count": 97},
    )
    artifact = VerifierGymArtifact(
        generated_at="2026-07-23T00:00:00Z",
        verifiers=[verifier],
        source_reports=["judge_agreement.json"],
    )

    payload = artifact.as_dict()

    assert payload["verifiers"][0]["dataset"] == dataset.as_dict()
    assert payload["verifiers"][0]["input_visibility"] == visibility.as_dict()
    assert payload["verifiers"][0]["lane_policy"] == lanes.as_dict()
    assert payload["verifiers"][0]["publication"] == publication.as_dict()
    assert payload["verifiers"][0] == verifier.as_dict()
    assert ValidationIssue("dataset", "missing").as_dict() == {
        "path": "dataset",
        "message": "missing",
        "severity": "error",
    }


def test_artifact_io_round_trip_and_path_validation(tmp_path):
    path = tmp_path / "nested" / "artifact.json"
    payload = valid_artifact()

    write_artifact(path, payload)

    assert load_artifact(path) == payload
    assert validate_artifact_path(path) == []
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_load_artifact_rejects_non_object_json(tmp_path):
    path = tmp_path / "rows.json"
    path.write_text(json.dumps([{"verdict": True}]), encoding="utf-8")

    with pytest.raises(ValueError, match="did not contain a JSON object"):
        load_artifact(path)


def test_validator_reports_root_and_record_shape_errors():
    assert {issue.path for issue in validate_artifact({})} == {
        "artifact_type",
        "generated_at",
        "schema_version",
        "verifiers",
    }

    issues = validate_artifact(
        {
            "artifact_type": "pisama_verifier_gym",
            "schema_version": "1.0",
            "generated_at": "2026-07-23",
            "verifiers": ["not-an-object"],
        }
    )

    assert len(issues) == 1
    assert issues[0].path == "verifiers[0]"
    assert has_errors(issues)


def test_validator_reports_missing_mappings_and_invalid_metric_types():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"]["name"] = ""
    verifier["dataset"]["total_rows"] = "ten"
    verifier["metrics"]["sample_count"] = "ten"
    verifier.pop("lane_policy")
    verifier.pop("publication")

    issues = validate_artifact(artifact)
    paths = {issue.path for issue in issues}

    assert "verifiers[0].dataset.name" in paths
    assert "verifiers[0].dataset.total_rows" in paths
    assert "verifiers[0].metrics.sample_count" in paths
    assert "verifiers[0].lane_policy" in paths
    assert "verifiers[0].publication" in paths


def test_synthetic_composition_is_detected_without_explicit_count():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"].pop("synthetic_rows")
    verifier["dataset"]["source_composition"] = {
        "external": {"rows": 8},
        "synthetic_challenge": {"rows": 2},
    }
    verifier["lane_policy"]["synthetic_lanes_excluded_from_published_metrics"] = False

    issues = validate_artifact(artifact)

    assert any("include 2 synthetic rows" in issue.message for issue in issues)


def test_unpublished_metrics_do_not_apply_publication_gate():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"]["synthetic_rows"] = 10
    verifier["lane_policy"]["synthetic_lanes_excluded_from_published_metrics"] = False
    verifier["publication"]["published_metrics"] = False

    assert validate_artifact(artifact) == []


def test_validator_rejects_duplicate_ids_and_invalid_root_metadata():
    artifact = valid_artifact()
    artifact["source_reports"] = ["", 3]
    artifact["verifiers"].append(dict(artifact["verifiers"][0]))

    issues = validate_artifact(artifact)
    paths = {issue.path for issue in issues}

    assert "source_reports" in paths
    assert "verifiers[1].id" in paths
    assert any("duplicates verifier id" in issue.message for issue in issues)


def test_validator_rejects_boolean_negative_and_out_of_range_metrics():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"]["total_rows"] = True
    verifier["dataset"]["synthetic_rows"] = -1
    verifier["metrics"] = {
        "sample_count": True,
        "positive_count": -1,
        "negative_count": 2.5,
        "true_positives": -2,
        "false_positives": True,
        "false_negatives": "one",
        "true_negatives": -3,
        "f1": True,
        "precision": -0.1,
        "recall": 1.1,
        "f1_ci_lower": "zero",
        "f1_ci_upper": float("inf"),
        "always_fire_f1": float("nan"),
        "optimal_threshold": 2,
    }

    paths = {issue.path for issue in validate_artifact(artifact)}

    expected_metric_paths = {f"verifiers[0].metrics.{key}" for key in verifier["metrics"]}
    assert expected_metric_paths <= paths
    assert "verifiers[0].dataset.total_rows" in paths
    assert "verifiers[0].dataset.synthetic_rows" in paths


def test_validator_rejects_inconsistent_dataset_and_policy_contracts():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"]["total_rows"] = 2
    verifier["dataset"]["synthetic_rows"] = 3
    verifier["input_visibility"] = {
        "policy": "full input",
        "raw_input_included": "yes",
        "fields_seen": ["messages", ""],
    }
    verifier["lane_policy"] = {
        "published_metric_lanes": [],
        "synthetic_lanes_excluded_from_published_metrics": "yes",
    }
    verifier["publication"] = {"published_metrics": "yes"}

    paths = {issue.path for issue in validate_artifact(artifact)}

    assert "verifiers[0].dataset.synthetic_rows" in paths
    assert "verifiers[0].input_visibility.raw_input_included" in paths
    assert "verifiers[0].input_visibility.fields_seen" in paths
    assert "verifiers[0].lane_policy.published_metric_lanes" in paths
    assert "verifiers[0].lane_policy.synthetic_lanes_excluded_from_published_metrics" in paths
    assert "verifiers[0].publication.published_metrics" in paths


def test_validator_accepts_empty_source_report_list_and_warning_only_result():
    artifact = valid_artifact()
    artifact["source_reports"] = []

    assert validate_artifact(artifact) == []
    assert not has_errors([ValidationIssue("metrics", "advisory", severity="warning")])


def test_synthetic_composition_ignores_unrelated_and_invalid_row_counts():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"].pop("synthetic_rows")
    verifier["dataset"]["source_composition"] = {
        "external": {"rows": 8},
        "synthetic_boolean": {"rows": True},
        "synthetic_missing": {},
        "synthetic_text": "two",
    }
    verifier["lane_policy"]["synthetic_lanes_excluded_from_published_metrics"] = False

    assert validate_artifact(artifact) == []


def test_validator_reports_non_mapping_verifier_sections():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["id"] = None
    verifier["dataset"] = "invalid"
    verifier["input_visibility"] = "invalid"
    verifier["lane_policy"] = "invalid"
    verifier["publication"] = "invalid"
    verifier["metrics"] = "invalid"

    paths = {issue.path for issue in validate_artifact(artifact)}

    assert "verifiers[0].id" in paths
    assert "verifiers[0].dataset" in paths
    assert "verifiers[0].input_visibility" in paths
    assert "verifiers[0].lane_policy" in paths
    assert "verifiers[0].publication" in paths
    assert "verifiers[0].metrics" in paths


def test_synthetic_composition_can_be_absent_or_non_mapping():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"].pop("synthetic_rows")
    verifier["dataset"]["source_composition"] = "invalid"
    verifier["lane_policy"]["synthetic_lanes_excluded_from_published_metrics"] = False

    assert validate_artifact(artifact) == []


def test_module_entrypoint_executes_real_cli():
    completed = subprocess.run(
        [sys.executable, "-m", "pisama_verifier_gym", "agreement", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["rows"] == 97
