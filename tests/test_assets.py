import pytest

from pisama_verifier_gym import load_builtin_json, read_datasheet, read_template


def test_template_and_datasheet_are_packaged():
    template = read_template()
    datasheet = read_datasheet("derailment-wildchat")

    assert "Verifier datasheet" in template
    assert "task derailment judge on WildChat" in datasheet


def test_json_artifacts_are_packaged():
    agreement = load_builtin_json("judge-agreement")
    adjudication = load_builtin_json("contested-adjudication")

    assert agreement["artifact"] == "cross_model_judge_agreement"
    assert adjudication["artifact"] == "contested_label_adjudication"
    assert adjudication["sanitization_note"]


def test_unknown_asset_names_fail_clearly():
    with pytest.raises(ValueError, match="unknown artifact"):
        load_builtin_json("missing")

    with pytest.raises(ValueError, match="unknown datasheet"):
        read_datasheet("missing")
