import json

from pisama_verifier_gym.cli import main
from tests.test_schema import valid_artifact


def test_cli_prints_builtin_agreement(capsys):
    assert main(["agreement"]) == 0

    output = capsys.readouterr().out

    assert "rows: 97" in output
    assert "claude-sonnet-4-6" in output
    assert "gemini-2.5-flash-lite" in output
    assert "gpt-5.5" in output


def test_cli_json_output(capsys):
    assert main(["agreement", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)

    assert payload["rows"] == 97
    assert len(payload["agreement"]) == 3
    assert payload["balance"]["gpt-5.5"]["abstain"] == 2


def test_cli_validate_render_compare_and_gate(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    rendered = tmp_path / "datasheet.md"

    payload = valid_artifact()
    baseline.write_text(json.dumps(payload), encoding="utf-8")
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["validate", str(candidate)]) == 0
    assert "validation OK" in capsys.readouterr().out

    assert main(["compare", str(baseline), str(candidate)]) == 0
    assert "detector.derailment" in capsys.readouterr().out

    assert main(["gate", str(baseline), str(candidate)]) == 0
    assert "gate OK" in capsys.readouterr().out

    assert main(["render", str(candidate), "--output", str(rendered)]) == 0
    assert "Verifier Gym datasheet" in rendered.read_text(encoding="utf-8")


def test_cli_export_calibration_writes_artifacts(tmp_path):
    report = tmp_path / "calibration.json"
    output = tmp_path / "artifact.json"
    manifest = tmp_path / "positive.json"
    report.write_text(
        json.dumps(
            {
                "calibrated_at": "2026-06-13T00:00:00+00:00",
                "external_only": True,
                "dataset_fingerprint": {
                    "fingerprint_id": "fp1",
                    "total_rows": 1,
                    "external_only": True,
                },
                "results": {"derailment": {"f1": 0.8, "sample_count": 1}},
                "sample_predictions": [
                    {"entry_id": "row1", "detection_type": "derailment", "expected": True}
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "export-calibration",
            str(report),
            "--detector",
            "derailment",
            "--output",
            str(output),
            "--positive-manifest",
            str(manifest),
        ]
    ) == 0

    assert main(["validate", str(output)]) == 0
    assert json.loads(manifest.read_text(encoding="utf-8"))["suites"][0]["positive_count"] == 1
