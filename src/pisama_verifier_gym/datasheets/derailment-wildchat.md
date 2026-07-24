# Verifier datasheet: task derailment judge on WildChat

A worked example of a verifier datasheet. The verifier under audit is an LLM-judge rubric for task derailment (an agent pursuing tangential or unrelated activities instead of the assigned task). The corpus is a 100-trace slice of WildChat, labelled three times as the labelling method improved. Everything below is reproducible from the data files in this repository.

## 1. Verifier identity

| Field | Value |
|---|---|
| Verifier | F6 Task Derailment, LLM-judge rubric |
| Rubric lineage | MAST failure taxonomy (NeurIPS 2025, arXiv:2503.13657), F6 |
| Production model | Anthropic only (claude-sonnet-4-6) |
| Labelling panel | claude-sonnet-4-6, gpt-5.5, gemini-2.5-flash-lite |
| Panel scope claim | Labels and rubrics are stable across judge model families. The panel is a labelling and calibration construct; it does not run in production. |

## 2. Label lineage

| Field | Value |
|---|---|
| Corpus | WildChat (AI2), 100-trace slice, real user conversations |
| Lane | External-only. Synthetic lanes never feed published F1 and never feed agreement stats. |
| Labelling method, v1 | Three-vendor panel, truncated input (prompt[:1500] + completion[:2500]) |
| Labelling method, v2 | Full-text relabel, same panel |
| Labelling method, v3 | Panel judge swap: gpt-4o-mini replaced with gpt-5.5 (labeller version ensemble-v3-gpt5.5-2026-06-10) |
| Labelling cost | About $0.017 per trace at v3 |
| Sample floor | A vendor pair is published only at 30 or more usable rows |

## 3. Agreement, and what it does and does not show

A row counts toward a pair only when both vendors returned a definite verdict; abstentions are dropped per pair and reported. Three statistics are read together:

- **Raw agreement**: share of usable rows where both judges gave the same verdict. On an imbalanced slice this is carried by the easy negatives.
- **Positive specific agreement (PSA)**: of the positive calls either judge makes, the share both make. This is the statistic that tracks the class that actually moves thresholds.
- **Cohen's kappa**: chance-corrected agreement. Deflates mechanically as prevalence drops.

### v1 (truncated input; gpt-4o-mini on the panel)

| Vendor A | Vendor B | Usable n | Raw | PSA | Kappa |
|---|---|---:|---:|---:|---:|
| anthropic | google | 96 | 0.81 | 0.31 | 0.20 |
| anthropic | openai | 72 | 0.85 | 0.42 | 0.33 |
| google | openai | 71 | 0.83 | 0.40 | 0.30 |

The openai judge (gpt-4o-mini) abstained on 28 of 100 rows, degrading three-vendor majority votes to two-vendor on those rows.

### v2 (full-text relabel)

| Vendor A | Vendor B | Usable n | Raw | PSA | Kappa |
|---|---|---:|---:|---:|---:|
| anthropic | google | 94 | 0.93 | 0.00 | -0.03 |
| anthropic | openai | 74 | 0.95 | 0.50 | 0.48 |
| google | openai | 73 | 0.89 | 0.20 | 0.14 |

Full-text review collapsed most positives: the v1 positives were substantially truncation artifacts (see section 4).

### v3 (gpt-5.5 replaces gpt-4o-mini)

| Vendor A | Vendor B | Usable n | Raw | PSA | Kappa |
|---|---|---:|---:|---:|---:|
| anthropic | google | 91 | 0.96 | 0.00 | -0.02 |
| anthropic | openai | 91 | 0.98 | 0.00 | 0.00 |
| google | openai | 95 | 0.96 | 0.00 | -0.02 |

Verdict balance at v3: each vendor casts exactly 2 yes votes out of 97 rows, and no two vendors cast them on the same trace. OpenAI abstention fell from 28 percent to 2 percent.

**The honest reading.** Raw agreement of 0.96 to 0.98 looks like a headline. It is not. At 2 percent prevalence, raw agreement is carried by the negatives, PSA is 0.00, and kappa is indistinguishable from zero. What this slice supports is "the rubric is stable on negatives across model families." It does not yet support positive-class stability; that requires positive-rich corpora, which is recorded here as an open limit rather than papered over.

Reproduce the v3 table: `python scripts/compute_agreement.py`

## 4. Contested-label adjudication

Selection rule: any trace with at least one definite YES vote from any vendor entered adjudication. That produced 26 candidates, of which 9 were canonical positives.

| Field | Value |
|---|---|
| Candidates | 26 (9 canonical positives) |
| Adjudicated by | Model arbiters (three independent, one per index slice), at the maintainer's explicit delegation, 2026-06-10 |
| Human in loop | No. Recorded as `human_in_loop: false` in the lineage record. Arbiter proposals are suggestions; the adjudicated label remains the maintainer's call on the apply path. |
| Arbiter bias caveat | The arbiter is an Anthropic model, the same family as one of the three panel judges. Recorded inline in the artifact. |
| Method | Each arbiter applied the F6 rubric to the full trace (the panel had seen prompt[:1500] + completion[:2500]) and formed a verdict before reading the panel's reasoning. |
| Outcome | 7 of 9 positives flipped to negative. 6 of the 7 had been judged on truncated input (5 confirmed swing-on-truncation); 1 was a doctrine call. 2 positives survive. |
| Doctrine ruling | "Under-delivery is not derailment." Guidance, outlines, or refusals instead of the requested artifact, and wrong-but-on-task output, are quality or completeness failures owned by other verifiers. Applied to the F6 judge prompt the same day. |

The root cause chain is the part worth copying: a labelling-pipeline truncation produced positives that survived the panel vote (in one case unanimously, 3Y/0N/0U) because every judge was looking at the same truncated evidence. Inter-judge agreement cannot catch an upstream data defect that all judges share. Full-input review can, and the fix belongs in doctrine rather than per-case patching.

Full record: `data/contested_adjudication.sanitized.json` (conversation text removed; joinable to WildChat via `source_trace_id`).

## 5. Known limits

- PSA of 0.00 at v3 means positive-class judge stability is unproven on this slice. Open item: positive-rich corpora.
- The arbiter shares a model family with one panel judge. Mitigation is procedural (verdict before reading panel reasoning) and disclosed, not eliminated.
- Derailment remains a hard detection target downstream of labelling: the production detector's external-lane F1 is published in the failing band as of 2026-06-11. The datasheet exists precisely so that number has an audit trail.

## 6. Change log

| Date | Change |
|---|---|
| 2026-06-10 | v2 full-text relabel; v3 panel judge swap (gpt-4o-mini to gpt-5.5); contested-label adjudication; doctrine ruling applied to judge prompt |
| 2026-06-11 | Datasheet published with sanitized verdict and adjudication exports |
