from pisama_verifier_gym import compare_artifacts, gate_artifacts


def artifact(f1=0.8, threshold=0.2, fingerprint="fp1", psa=None, abstention=None):
    record = {
        "artifact_type": "pisama_verifier_gym",
        "schema_version": "1.0",
        "verifiers": [
            {
                "id": "detector.derailment",
                "dataset": {"fingerprint_id": fingerprint},
                "metrics": {
                    "f1": f1,
                    "precision": 0.9,
                    "recall": 0.7,
                    "optimal_threshold": threshold,
                },
            }
        ],
    }
    if psa is not None or abstention is not None:
        record["verifiers"][0]["agreement"] = {
            "pairwise": [
                {
                    "positive_specific_agreement": psa,
                    "abstention_rate": abstention,
                }
            ]
        }
    return record


def test_compare_artifacts_reports_metric_deltas():
    rows = compare_artifacts(artifact(f1=0.8), artifact(f1=0.7))

    assert len(rows) == 1
    assert rows[0].verifier_id == "detector.derailment"
    assert rows[0].f1_delta == -0.10000000000000009


def test_gate_fails_on_f1_drop_threshold_drift_and_fingerprint_change():
    issues = gate_artifacts(
        artifact(f1=0.8, threshold=0.1, fingerprint="fp1"),
        artifact(f1=0.7, threshold=0.5, fingerprint="fp2"),
    )

    metrics = {issue.metric for issue in issues}
    assert "f1" in metrics
    assert "optimal_threshold" in metrics
    assert "fingerprint_id" in metrics


def test_gate_passes_when_candidate_matches_baseline():
    assert gate_artifacts(artifact(), artifact()) == []


def test_gate_fails_on_psa_floor_and_drop():
    issues = gate_artifacts(artifact(psa=0.4), artifact(psa=0.02))

    assert {issue.metric for issue in issues} == {"positive_specific_agreement"}


def test_gate_fails_on_abstention_spike():
    issues = gate_artifacts(artifact(abstention=0.01), artifact(abstention=0.20))

    assert {issue.metric for issue in issues} == {"abstention_rate"}
