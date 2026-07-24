# pisama-verifier-gym

[![PyPI version](https://img.shields.io/pypi/v/pisama-verifier-gym.svg)](https://pypi.org/project/pisama-verifier-gym/)
[![Python versions](https://img.shields.io/pypi/pyversions/pisama-verifier-gym.svg)](https://pypi.org/project/pisama-verifier-gym/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Pisama-AI/pisama-verifier-gym/actions/workflows/ci.yml/badge.svg)](https://github.com/Pisama-AI/pisama-verifier-gym/actions/workflows/ci.yml)

Audit harnesses for verifiers: LLM judges, reward functions, graders, and failure
detectors. The package ships a verifier datasheet template, a worked WildChat
derailment judge datasheet, sanitized backing artifacts, and a no-dependency
agreement calculator.

## Install

```bash
pip install pisama-verifier-gym
```

## Quick Start

```bash
pisama-verifier-gym agreement
pisama-verifier-gym validate artifact.json
pisama-verifier-gym gate baseline.json candidate.json
pisama-verifier-gym render artifact.json --output datasheet.md
```

```python
from pisama_verifier_gym import agreement_table, load_builtin_verdicts

rows = load_builtin_verdicts()
for stat in agreement_table(rows):
    print(stat.vendor_a, stat.vendor_b, stat.raw_agreement, stat.positive_specific_agreement)
```

## What Is Included

- `TEMPLATE.md`: the verifier datasheet template.
- `datasheets/derailment-wildchat.md`: a filled worked example for a task
  derailment LLM judge.
- `data/wildchat_v3_derailment_verdicts.jsonl`: sanitized per-trace panel
  verdicts, joinable to WildChat by `source_trace_id`.
- `data/contested_adjudication.sanitized.json`: contested-label adjudication
  record with lineage fields and conversation text removed.
- `data/judge_agreement.json`: aggregate agreement artifact from the same lane.

Conversation text is not redistributed. WildChat is distributed by AI2 under
its own license terms.

See [DATA_PROVENANCE.md](DATA_PROVENANCE.md) for the exact contents,
sanitization policy, known limitations, and reproduction boundary.

## Python API

```python
from pathlib import Path
from pisama_verifier_gym import (
    agreement_table,
    load_verdict_rows,
    pairwise_agreement,
    verdict_balance,
)

rows = load_verdict_rows(Path("verdicts.jsonl"))
table = agreement_table(rows)
balance = verdict_balance(rows)

anthropic_google = pairwise_agreement(
    rows,
    "claude-sonnet-4-6",
    "gemini-2.5-flash-lite",
)
```

Each pair reports:

- usable row count after pairwise abstention drops
- raw agreement
- positive specific agreement
- Cohen's kappa

Read raw packaged assets:

```python
from pisama_verifier_gym import read_datasheet, read_template

print(read_template())
print(read_datasheet("derailment-wildchat"))
```

## CLI

```bash
# Built-in WildChat derailment verdicts
pisama-verifier-gym agreement

# A custom JSONL export with the same per_vendor_verdicts shape
pisama-verifier-gym agreement path/to/verdicts.jsonl

# Machine-readable output
pisama-verifier-gym agreement --json

# Validate the Verifier Gym contract
pisama-verifier-gym validate artifact.json

# Compare two artifacts with the same verifier ids
pisama-verifier-gym compare baseline.json candidate.json --json

# Fail on F1 drops, PSA collapse, abstention spikes, threshold drift, or
# unexpected fingerprint changes
pisama-verifier-gym gate baseline.json candidate.json

# Render machine-generated datasheet tables as Markdown
pisama-verifier-gym render artifact.json --output datasheet.md

# Export Pisama calibration reports into the gym contract
pisama-verifier-gym export-calibration calibration_report.json \
  --llm-report llm_detector_calibration.json \
  --output verifier_gym/current.json \
  --positive-manifest verifier_gym/positive_rich_manifest.json
```

The validator fails hard when a verifier lacks rubric lineage, a dataset
fingerprint, an input visibility policy, a lane policy, or when synthetic data
can feed published metrics. It also rejects duplicate verifier ids, negative or
boolean sample counts, out-of-range unit metrics, and malformed visibility,
lane, or publication contracts. The gate is intentionally fingerprint-aware:
by default a candidate must be compared against the previous run for the same
dataset fingerprint.

Custom JSONL verdict exports are validated when loaded. Every row must contain
a `per_vendor_verdicts` object, and each vendor verdict must be `true`, `false`,
or `null`. Invalid rows fail with their source line number instead of silently
changing the agreement denominator.

## Why This Exists

High raw agreement is not enough when the positive class is rare. The included
WildChat example shows raw agreement of 0.96 to 0.98, while positive specific
agreement is 0.00 on the same slice. That distinction decides whether a
published verifier metric is useful or misleading.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests
mypy src/pisama_verifier_gym
xenon --max-absolute B --max-modules A --max-average A src/pisama_verifier_gym
pylint --disable=all --enable=duplicate-code --min-similarity-lines=8 src/pisama_verifier_gym
pytest -q --cov=pisama_verifier_gym --cov-branch --cov-fail-under=99
python -m build
```

The packaged examples are fixed audit artifacts. Generate your own artifact
from a calibration report with `pisama-verifier-gym export-calibration`, then
validate, render, and gate it before promoting a new baseline.

## License

Code, documentation, and sanitized artifacts in this package are MIT licensed.
