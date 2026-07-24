import json
import runpy
import sys

import pytest

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

    assert (
        main(
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
        )
        == 0
    )

    assert main(["validate", str(output)]) == 0
    assert json.loads(manifest.read_text(encoding="utf-8"))["suites"][0]["positive_count"] == 1


def test_cli_uses_agreement_as_default_command(capsys):
    assert main([]) == 0
    assert "rows: 97" in capsys.readouterr().out


def test_cli_reads_custom_agreement_file(tmp_path, capsys):
    verdicts = tmp_path / "verdicts.jsonl"
    verdicts.write_text(
        '{"per_vendor_verdicts":{"a":{"verdict":true},"b":{"verdict":true}}}\n',
        encoding="utf-8",
    )

    assert main(["agreement", str(verdicts), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 1


def test_cli_reports_validation_gate_and_empty_comparison_failures(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"

    baseline_payload = valid_artifact()
    candidate_payload = valid_artifact()
    candidate_payload["verifiers"][0]["id"] = "detector.new"
    candidate_payload["verifiers"][0]["dataset"]["fingerprint_id"] = "changed"
    baseline.write_text(json.dumps(baseline_payload), encoding="utf-8")
    candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")

    assert main(["compare", str(baseline), str(candidate)]) == 0
    assert "no matching verifiers" in capsys.readouterr().out

    candidate_payload["verifiers"][0]["id"] = "detector.derailment"
    candidate_payload["verifiers"][0]["metrics"]["f1"] = 0.1
    candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")

    assert main(["gate", str(baseline), str(candidate)]) == 1
    gate_output = capsys.readouterr().out
    assert "fingerprint_id" in gate_output
    assert "f1" in gate_output

    candidate_payload["artifact_type"] = "invalid"
    candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")
    assert main(["validate", str(candidate)]) == 1
    assert "error: artifact_type" in capsys.readouterr().out


def test_cli_compare_json_render_stdout_and_fingerprint_override(tmp_path, capsys):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline_payload = valid_artifact()
    candidate_payload = valid_artifact()
    candidate_payload["verifiers"][0]["dataset"]["fingerprint_id"] = "changed"
    baseline.write_text(json.dumps(baseline_payload), encoding="utf-8")
    candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")

    assert main(["compare", str(baseline), str(candidate), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["verifier_id"] == "detector.derailment"

    assert (
        main(
            [
                "gate",
                str(baseline),
                str(candidate),
                "--allow-fingerprint-change",
            ]
        )
        == 0
    )
    assert "gate OK" in capsys.readouterr().out

    assert main(["render", str(candidate)]) == 0
    assert "# Verifier Gym datasheet" in capsys.readouterr().out


def test_cli_export_calibration_to_stdout_with_llm_report(tmp_path, capsys):
    report = tmp_path / "calibration.json"
    llm_report = tmp_path / "llm.json"
    common = {
        "calibrated_at": "2026-07-23",
        "dataset_fingerprint": {"fingerprint_id": "fp1", "total_rows": 1},
    }
    report.write_text(
        json.dumps({**common, "results": {"derailment": {"f1": 0.8}}}),
        encoding="utf-8",
    )
    llm_report.write_text(
        json.dumps({**common, "results": {"analytical_semantics": {"f1": 0.7}}}),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "export-calibration",
                str(report),
                "--llm-report",
                str(llm_report),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert [entry["kind"] for entry in payload["verifiers"]] == ["detector", "llm_judge"]


@pytest.mark.parametrize(
    "module_name",
    ["pisama_verifier_gym.__main__", "pisama_verifier_gym.cli"],
)
@pytest.mark.filterwarnings(
    "ignore:'pisama_verifier_gym.cli' found in sys.modules after import:RuntimeWarning"
)
def test_python_module_entrypoints_execute(module_name, capsys):
    original_argv = sys.argv
    sys.argv = [module_name, "agreement", "--json"]
    try:
        with pytest.raises(SystemExit, match="0"):
            runpy.run_module(module_name, run_name="__main__")
    finally:
        sys.argv = original_argv

    assert json.loads(capsys.readouterr().out)["rows"] == 97
