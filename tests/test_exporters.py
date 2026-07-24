import json

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
