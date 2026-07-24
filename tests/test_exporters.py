import json
from datetime import datetime

import pytest

from pisama_verifier_gym import (
    export_calibration_report,
    positive_rich_manifest,
    validate_artifact,
)


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_export_calibration_report_builds_contract_and_positive_suite(tmp_path):
    report = tmp_path / "calibration.json"
    write_json(
        report,
        {
            "calibrated_at": "2026-06-13T00:00:00+00:00",
            "external_only": True,
            "dataset_fingerprint": {
                "fingerprint_id": "fp1",
                "content_hash": "hash1",
                "total_rows": 100,
                "external_only": True,
                "run_filters": {"script": "test_calibration"},
                "source_composition": {"external": {"rows": 100, "pos": 40, "neg": 60}},
            },
            "results": {
                "derailment": {
                    "f1": 0.5,
                    "precision": 0.75,
                    "recall": 0.4,
                    "sample_count": 10,
                    "true_positives": 2,
                    "false_positives": 1,
                    "false_negatives": 3,
                    "true_negatives": 4,
                    "optimal_threshold": 0.3,
                }
            },
            "sample_predictions": [
                {
                    "entry_id": "row1",
                    "detection_type": "derailment",
                    "expected": True,
                    "source": "wildchat_real",
                    "source_dataset": "external",
                    "difficulty": "hard",
                    "classification": "TP",
                    "tags": ["real_trace"],
                }
            ],
        },
    )

    artifact = export_calibration_report(report, detectors=["derailment"])

    assert validate_artifact(artifact) == []
    verifier = artifact["verifiers"][0]
    assert verifier["id"] == "detector.derailment"
    assert verifier["dataset"]["fingerprint_id"] == "fp1"
    assert verifier["metrics"]["f1"] == 0.5
    assert verifier["challenge_suite"]["entries"][0]["entry_id"] == "row1"


def test_export_calibration_report_includes_llm_judges(tmp_path):
    report = tmp_path / "calibration.json"
    llm = tmp_path / "llm.json"
    base = {
        "calibrated_at": "2026-06-13T00:00:00+00:00",
        "dataset_fingerprint": {"fingerprint_id": "fp1", "total_rows": 1},
        "results": {},
    }
    write_json(report, {**base, "results": {"derailment": {"f1": 0.5}}})
    write_json(llm, {**base, "results": {"analytical_semantics": {"f1": 0.9}}})

    artifact = export_calibration_report(report, detectors=["derailment"], llm_report=llm)

    ids = [record["id"] for record in artifact["verifiers"]]
    assert ids == ["detector.derailment", "llm_judge.analytical_semantics"]


def test_positive_rich_manifest_extracts_suite_metadata(tmp_path):
    report = tmp_path / "calibration.json"
    write_json(
        report,
        {
            "dataset_fingerprint": {"fingerprint_id": "fp1", "total_rows": 1},
            "results": {"completion": {"f1": 0.8}},
            "sample_predictions": [
                {"entry_id": "p1", "detection_type": "completion", "expected": True}
            ],
        },
    )

    artifact = export_calibration_report(report, detectors=["completion"])
    manifest = positive_rich_manifest(artifact)

    assert manifest["suites"][0]["verifier_id"] == "detector.completion"
    assert manifest["suites"][0]["positive_count"] == 1


def test_export_maps_metric_aliases_and_rejects_boolean_numbers(tmp_path):
    report = tmp_path / "calibration.json"
    write_json(
        report,
        {
            "timestamp": "2026-07-23T12:00:00+00:00",
            "run_type": "external_holdout",
            "dataset_fingerprint": {
                "fingerprint_id": "fp-aliases",
                "total_rows": 12,
                "source_composition": {
                    "external": {"rows": 10},
                    "synthetic_challenge": {"rows": 2},
                    "synth-invalid": {"rows": True},
                },
            },
            "results": {
                "completion": {
                    "f1": True,
                    "precision": 0.75,
                    "recall": float("inf"),
                    "f1_ci_lower": 0.4,
                    "f1_ci_upper": 0.8,
                    "always_fire_f1": 0.1,
                    "positive_count": True,
                    "negative_count": 7,
                    "n_entries": 12,
                    "rule_threshold": 0.25,
                    "tp": 3,
                    "fp": 1,
                    "fn": 2,
                    "tn": 6,
                    "eval_flags": ["small_sample"],
                }
            },
        },
    )

    artifact = export_calibration_report(report, detectors=["completion"])
    verifier = artifact["verifiers"][0]
    metrics = verifier["metrics"]

    assert artifact["generated_at"] == "2026-07-23T12:00:00+00:00"
    assert verifier["dataset"]["name"] == "external_holdout:completion"
    assert verifier["dataset"]["synthetic_rows"] == 2
    assert metrics["sample_count"] == 12
    assert metrics["optimal_threshold"] == 0.25
    assert (metrics["true_positives"], metrics["true_negatives"]) == (3, 6)
    assert "f1" not in metrics
    assert "recall" not in metrics
    assert "positive_count" not in metrics
    assert metrics["eval_flags"] == ["small_sample"]
    assert verifier["honest_reading"] == "completion has caveats in this run: small_sample."
    assert verifier["known_limits"][0] == "small_sample"


def test_export_builds_ready_challenge_suite_and_fallback_scope(tmp_path):
    report = tmp_path / "calibration.json"
    predictions = [
        {
            "entry_id": f"p{index}",
            "detection_type": "custom",
            "expected": True,
            "tags": None,
        }
        for index in range(30)
    ]
    predictions.extend(
        [
            {"entry_id": "negative", "detection_type": "custom", "expected": False},
            {"entry_id": "other", "detection_type": "other", "expected": True},
            "invalid",
        ]
    )
    write_json(
        report,
        {
            "run_date": "2026-07-22",
            "dataset_fingerprint": {
                "fingerprint_id": "fp-ready",
                "total_rows": 33,
                "run_filters": {"split": "external"},
            },
            "results": {"custom": {"sample_count": 33, "eval_flags": "custom_rubric"}},
            "sample_predictions": predictions,
        },
    )

    artifact = export_calibration_report(report, detectors=["missing", "custom"])
    verifier = artifact["verifiers"][0]

    assert artifact["generated_at"] == "2026-07-22"
    assert verifier["rubric_lineage"] == "Pisama verifier rubric for custom"
    assert verifier["dataset"]["name"] == "calibration:custom"
    assert verifier["dataset"]["provenance"] == '{"split": "external"}'
    assert verifier["scope_claim"] == "detector custom measured on the declared fingerprint"
    assert verifier["challenge_suite"]["status"] == "ready"
    assert verifier["challenge_suite"]["positive_count"] == 30
    assert verifier["challenge_suite"]["entries"][0]["tags"] == []


def test_export_uses_current_utc_time_when_report_has_no_timestamp(tmp_path):
    report = tmp_path / "calibration.json"
    write_json(
        report,
        {
            "dataset_fingerprint": {"fingerprint_id": "fp1", "total_rows": 1},
            "results": {"derailment": {"f1": 0.5, "sample_count": 1}},
        },
    )

    artifact = export_calibration_report(report, detectors=["derailment"])

    parsed = datetime.fromisoformat(artifact["generated_at"])
    assert parsed.tzinfo is not None
    assert artifact["verifiers"][0]["honest_reading"].startswith(
        "derailment measured F1 0.5000 on n=1"
    )


def test_export_handles_missing_results_and_malformed_llm_results(tmp_path):
    report = tmp_path / "calibration.json"
    llm = tmp_path / "llm.json"
    write_json(report, {"calibrated_at": "2026-07-23", "results": "invalid"})
    write_json(llm, {"results": ["invalid"]})

    artifact = export_calibration_report(report, llm_report=llm)

    assert artifact["verifiers"] == []
    assert artifact["source_reports"] == [str(report), str(llm)]


@pytest.mark.parametrize("payload", [[], "invalid", 1])
def test_export_rejects_non_object_report_json(tmp_path, payload):
    report = tmp_path / "calibration.json"
    write_json(report, payload)

    with pytest.raises(ValueError, match="did not contain a JSON object"):
        export_calibration_report(report)


def test_positive_manifest_skips_non_records_and_zero_positive_suites():
    artifact = {
        "generated_at": "2026-07-23",
        "verifiers": [
            "invalid",
            {"id": "no-suite"},
            {"id": "empty", "challenge_suite": {"positive_count": 0}},
            {
                "id": "valid",
                "name": "Valid",
                "dataset": "invalid",
                "challenge_suite": {"positive_count": 2, "status": "ready"},
            },
        ],
    }

    manifest = positive_rich_manifest(artifact)

    assert manifest["suites"] == [
        {
            "verifier_id": "valid",
            "verifier_name": "Valid",
            "fingerprint_id": None,
            "positive_count": 2,
            "status": "ready",
        }
    ]
