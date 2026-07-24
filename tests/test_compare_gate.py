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
    assert rows[0].as_dict()["precision_delta"] == 0


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


def test_compare_skips_candidate_only_verifiers_and_missing_metrics():
    baseline = artifact()
    candidate = artifact()
    candidate["verifiers"].append(
        {
            "id": "detector.new",
            "dataset": {"fingerprint_id": "fp2"},
            "metrics": {},
        }
    )
    baseline["verifiers"][0]["metrics"] = "invalid"
    candidate["verifiers"][0]["metrics"] = None

    rows = compare_artifacts(baseline, candidate)

    assert len(rows) == 1
    assert rows[0].f1_delta is None
    assert rows[0].threshold_delta is None


def test_compare_tolerates_missing_collections_and_invalid_agreement_rows():
    assert compare_artifacts({"verifiers": None}, {"verifiers": []}) == []
    assert compare_artifacts({"verifiers": [None]}, {"verifiers": [None]}) == []

    baseline = artifact(psa=0.4)
    candidate = artifact(psa=0.4)
    baseline["verifiers"][0]["agreement"] = {"pairwise": None}
    candidate["verifiers"][0]["agreement"] = {
        "pairwise": [
            "invalid",
            {"positive_specific_agreement": True, "abstention_rate": "none"},
        ]
    }
    baseline["verifiers"][0]["dataset"] = "invalid"

    row = compare_artifacts(baseline, candidate)[0]

    assert row.baseline_fingerprint_id is None
    assert row.psa_delta is None
    assert row.abstention_delta is None


def test_gate_can_allow_fingerprint_change_and_reports_issue_payloads():
    issues = gate_artifacts(
        artifact(f1=0.8, fingerprint="fp1"),
        artifact(f1=0.6, fingerprint="fp2"),
        require_same_fingerprint=False,
    )

    assert len(issues) == 1
    assert issues[0].as_dict() == {
        "verifier_id": "detector.derailment",
        "metric": "f1",
        "message": "delta -0.2000 exceeded threshold -0.0500",
        "severity": "error",
    }


def test_gate_ignores_missing_deltas_and_boundary_values():
    baseline = artifact(f1=None, threshold=None)
    candidate = artifact(f1=None, threshold=None)

    assert gate_artifacts(baseline, candidate) == []

    baseline = artifact(f1=0.8, threshold=0.25, psa=0.2, abstention=0.1)
    candidate = artifact(f1=0.75, threshold=0.5, psa=0.1, abstention=0.15)

    assert gate_artifacts(baseline, candidate) == []


def test_agreement_extremes_use_worst_pair():
    baseline = artifact(psa=0.5, abstention=0.1)
    candidate = artifact(psa=0.4, abstention=0.2)
    baseline["verifiers"][0]["agreement"]["pairwise"].append(
        {"positive_specific_agreement": 0.3, "abstention_rate": 0.3}
    )
    candidate["verifiers"][0]["agreement"]["pairwise"].append(
        {"positive_specific_agreement": 0.1, "abstention_rate": 0.4}
    )

    row = compare_artifacts(baseline, candidate)[0]

    assert row.baseline_psa_min == 0.3
    assert row.candidate_psa_min == 0.1
    assert row.psa_delta == -0.19999999999999998
    assert row.baseline_abstention_max == 0.3
    assert row.candidate_abstention_max == 0.4
