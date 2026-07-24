from pisama_verifier_gym import render_artifact
from tests.test_schema import valid_artifact


def test_render_artifact_outputs_machine_generated_datasheet():
    markdown = render_artifact(valid_artifact())

    assert "# Verifier Gym datasheet" in markdown
    assert "detector.derailment" in markdown
    assert "| Fingerprint | `abc123` |" in markdown
