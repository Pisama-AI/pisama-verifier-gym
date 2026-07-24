# Data provenance

The package includes fixed, sanitized audit artifacts for demonstrating
verifier agreement and release gates.

## Included data

- `wildchat_v3_derailment_verdicts.jsonl` contains trace identifiers, labels,
  model-family verdicts, and confidence values. It does not contain
  conversation text.
- `judge_agreement.json` contains aggregate cross-model agreement statistics.
- `contested_adjudication.sanitized.json` contains adjudication metadata and
  truncated judge rationales. It does not contain source conversations.
- The datasheets document the rubric, sampling, limitations, and intended use.

The source trace identifiers refer to WildChat records. WildChat is published
by AI2 under its own terms. Pisama does not redistribute the source
conversations.

## Reproduction boundary

The bundled verdicts are evidence for the worked example. They are not a live
benchmark and cannot reproduce model calls without the independently licensed
source corpus and model access. The agreement calculations, schema validation,
rendering, and release gates are fully reproducible from the packaged files.

## Privacy and contributions

Do not submit private prompts, completions, credentials, customer identifiers,
or proprietary datasets. New artifacts must state their source, license,
sanitization method, and whether synthetic rows contribute to published
metrics.
