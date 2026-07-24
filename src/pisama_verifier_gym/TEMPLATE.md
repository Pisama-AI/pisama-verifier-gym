# Verifier datasheet (template)

One page per verifier. A verifier is any mechanism that evaluates rollouts against a standard and produces verdicts used for optimization or measurement: a grader, a reward function, an LLM-judge rubric, a detector. If a number derived from this verifier appears anywhere public (an F1 score, a pass rate, a reward), this sheet is what makes that number auditable.

Fill every row. "Unknown" is an acceptable value; an absent row is not.

## 1. Verifier identity

| Field | Value |
|---|---|
| Verifier name and version | |
| Rubric or spec lineage (what standard, which version, link) | |
| Model(s) used, with exact identifiers | |
| Where it runs (production, calibration lane, both) | |
| Scope claim (the precise sentence this verifier's numbers support) | |

## 2. Label lineage

| Field | Value |
|---|---|
| Corpus and provenance (real or synthetic, source, license) | |
| Lane policy (do synthetic lanes feed published metrics?) | |
| Labelling method and version history | |
| What the labeller saw (full input? truncated? which fields?) | |
| Cost per labelled item | |
| Sample floor for publishing any statistic | |

## 3. Agreement

| Field | Value |
|---|---|
| Panel composition (models, families) | |
| Pairwise raw agreement, with usable n per pair | |
| Positive specific agreement (PSA) per pair | |
| Cohen's kappa per pair | |
| Abstention rate per judge | |
| Class prevalence on the measured slice | |
| The honest reading (what these numbers do and do not support) | |

## 4. Adjudication and doctrine

| Field | Value |
|---|---|
| Selection rule for contested items | |
| Who adjudicates (human, model, both), recorded as such | |
| Adjudicator bias caveats | |
| Flip outcomes (n, direction, root causes) | |
| Doctrine rulings produced, and where they were applied | |

## 5. Calibration

| Field | Value |
|---|---|
| Dataset fingerprint of the measuring corpus | |
| Headline metrics with confidence intervals | |
| Threshold value, derivation method, applied_at timestamp | |
| Regression gate (what blocks a deploy) | |

## 6. Known limits

Open items stated as open items: blind spots, unproven classes, prevalence problems, family-bias caveats, anything a skeptical reader would find anyway.

## 7. Change log

| Date | Change |
|---|---|
| | |
