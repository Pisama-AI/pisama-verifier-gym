from pisama_verifier_gym import has_errors, validate_artifact


def valid_artifact():
    return {
        "artifact_type": "pisama_verifier_gym",
        "schema_version": "1.0",
        "generated_at": "2026-06-13T00:00:00+00:00",
        "verifiers": [
            {
                "id": "detector.derailment",
                "name": "derailment",
                "kind": "detector",
                "version": "v1",
                "rubric_lineage": "MAST F6",
                "dataset": {
                    "name": "external",
                    "fingerprint_id": "abc123",
                    "total_rows": 10,
                    "synthetic_rows": 0,
                },
                "input_visibility": {"policy": "full input"},
                "lane_policy": {
                    "published_metric_lanes": ["external"],
                    "synthetic_lanes_excluded_from_published_metrics": True,
                },
                "publication": {"published_metrics": True},
                "metrics": {"sample_count": 10, "f1": 0.8},
            }
        ],
    }


def test_validate_accepts_complete_artifact():
    issues = validate_artifact(valid_artifact())

    assert issues == []


def test_validate_fails_on_missing_lineage_fingerprint_and_visibility():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["rubric_lineage"] = ""
    verifier["dataset"]["fingerprint_id"] = ""
    verifier["input_visibility"] = {}

    issues = validate_artifact(artifact)

    assert has_errors(issues)
    paths = {issue.path for issue in issues}
    assert "verifiers[0].rubric_lineage" in paths
    assert "verifiers[0].dataset.fingerprint_id" in paths
    assert "verifiers[0].input_visibility.policy" in paths


def test_validate_fails_when_synthetic_rows_feed_published_metrics():
    artifact = valid_artifact()
    verifier = artifact["verifiers"][0]
    verifier["dataset"]["synthetic_rows"] = 4
    verifier["lane_policy"]["synthetic_lanes_excluded_from_published_metrics"] = False

    issues = validate_artifact(artifact)

    assert has_errors(issues)
    assert any("synthetic" in issue.message for issue in issues)
