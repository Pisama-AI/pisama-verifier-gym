# Changelog

## Unreleased

- Reject malformed JSONL verdict rows with source line numbers.
- Reject booleans masquerading as calibration numbers or counts.
- Validate root metadata, unique verifier ids, metric ranges, counts,
  visibility, lane policy, and publication contracts.
- Make regression-gate boundary comparisons stable against floating-point
  representation noise.
- Make comparison and export helpers robust to malformed optional sections.
- Fix the bare CLI invocation so its documented default agreement report runs.
- Enforce 99 percent combined statement and branch coverage in CI.
- Enforce B-or-better function complexity, A module and average complexity, and
  zero duplicate-code findings.
- Add contract, error-path, validation, file round-trip, and entrypoint tests.
- Add CodeQL and pull request dependency review.

## 0.1.1

- Publish the canonical source repository and independent CI.
- Add data provenance, contribution, security, and maintenance policies.
- Remove private repository paths and named adjudicator metadata from the
  packaged audit artifact.
- Add clean-wheel validation across Python 3.10 through 3.13.

## 0.1.0

- Initial monorepo package for Pisama Verifier Gym.
- Added verifier datasheet template, WildChat derailment worked example, and
  sanitized backing artifacts.
- Added Python API and CLI for pairwise judge agreement.
- Added Verifier Gym artifact schemas, validation, comparison, regression
  gates, Markdown rendering, and Pisama calibration exporters.
