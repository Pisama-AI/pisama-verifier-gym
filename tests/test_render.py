from pisama_verifier_gym import render_artifact
from tests.test_schema import valid_artifact


def test_render_artifact_outputs_machine_generated_datasheet():
    markdown = render_artifact(valid_artifact())

    assert "# Verifier Gym datasheet" in markdown
    assert "detector.derailment" in markdown
    assert "| Fingerprint | `abc123` |" in markdown


def test_render_artifact_handles_optional_and_malformed_sections():
    artifact = {
        "verifiers": [
            "invalid",
            {
                "id": "minimal",
                "name": "minimal",
                "kind": "detector",
                "metrics": {
                    "precision": 0.8,
                    "recall": 0.7,
                    "optimal_threshold": 0.2,
                    "true_positives": 2,
                    "false_positives": 1,
                    "false_negatives": 1,
                    "true_negatives": 6,
                    "ignored": "value",
                },
                "dataset": "invalid",
                "publication": None,
                "input_visibility": [],
                "lane_policy": "invalid",
                "challenge_suite": 3,
                "known_limits": ["small sample", "single dataset"],
            },
        ]
    }

    markdown = render_artifact(artifact)

    assert "Generated at: `unknown`" in markdown
    assert "Schema: `unknown`" in markdown
    assert "| precision | 0.8 |" in markdown
    assert "| true_negatives | 6 |" in markdown
    assert "ignored" not in markdown
    assert "- small sample\n- single dataset" in markdown


def test_render_artifact_reports_no_recorded_limits():
    artifact = {
        "verifiers": [
            {
                "id": "minimal",
                "name": "minimal",
                "kind": "detector",
                "known_limits": "invalid",
            }
        ]
    }

    assert "- None recorded." in render_artifact(artifact)
