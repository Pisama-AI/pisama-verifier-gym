"""Load packaged verifier gym assets."""

from __future__ import annotations

import json
from importlib.resources import as_file, files
from typing import Any

from .agreement import load_verdict_rows

PACKAGE = "pisama_verifier_gym"

DATASETS = {
    "wildchat-derailment-v3": "wildchat_v3_derailment_verdicts.jsonl",
    "wildchat_v3_derailment": "wildchat_v3_derailment_verdicts.jsonl",
}

JSON_ARTIFACTS = {
    "contested-adjudication": "contested_adjudication.sanitized.json",
    "contested_adjudication": "contested_adjudication.sanitized.json",
    "judge-agreement": "judge_agreement.json",
    "judge_agreement": "judge_agreement.json",
}


def load_builtin_verdicts(name: str = "wildchat-derailment-v3") -> list[dict[str, Any]]:
    """Load one of the packaged JSONL verdict exports."""
    try:
        filename = DATASETS[name]
    except KeyError as exc:
        valid = ", ".join(sorted(DATASETS))
        raise ValueError(f"unknown dataset {name!r}; expected one of: {valid}") from exc

    resource = files(PACKAGE).joinpath("data").joinpath(filename)
    with as_file(resource) as path:
        return load_verdict_rows(path)


def load_builtin_json(name: str) -> dict[str, Any]:
    """Load one of the packaged JSON artifacts."""
    try:
        filename = JSON_ARTIFACTS[name]
    except KeyError as exc:
        valid = ", ".join(sorted(JSON_ARTIFACTS))
        raise ValueError(f"unknown artifact {name!r}; expected one of: {valid}") from exc

    resource = files(PACKAGE).joinpath("data").joinpath(filename)
    with resource.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"artifact {name!r} did not contain a JSON object")
    return value


def read_template() -> str:
    """Read the packaged verifier datasheet template."""
    return files(PACKAGE).joinpath("TEMPLATE.md").read_text(encoding="utf-8")


def read_datasheet(name: str = "derailment-wildchat") -> str:
    """Read a packaged verifier datasheet by basename."""
    filename = name if name.endswith(".md") else f"{name}.md"
    resource = files(PACKAGE).joinpath("datasheets").joinpath(filename)
    if not resource.is_file():
        raise ValueError(f"unknown datasheet {name!r}")
    return resource.read_text(encoding="utf-8")
