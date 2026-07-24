# Verifier datasheet: persona_drift under adversarial probing

A worked audit of the production `persona_drift` detector against an optimizing LLM adversary. The adversary rewrites confirmed-failing agent outputs to preserve the failure while evading the detector; a cross-family panel and a human confirm which rewrites still exhibit the failure. The tables below preserve the audit evidence. Reproducing the model calls requires the source corpus and model access, as described in the repository data-provenance policy.

## 1. Verifier identity

| Field | Value |
|---|---|
| Verifier | persona_drift, heuristic multi-factor persona-consistency scorer (`app/detection/persona.py`) |
| Rubric lineage | Persona-consistency scoring: semantic similarity + lexical overlap + tone + persona-compliance (max of role-action / style / task-relevance) + fingerprint drift |
| Production model | Anthropic only in production paths; the scorer itself is heuristic (no LLM call) |
| Adversary / panel models | Adversary: claude-sonnet-4-6 (temp 0). Panel: claude-opus-4-8 (thinking), gpt-5.4, gemini-3.5-flash (thinking) |
| Scope claim | These numbers describe robustness to a black-box prompt-search adversary on the persona_drift firing decision, NOT robustness to a gradient-trained policy and NOT production-traffic FPR. |

## 2. Label lineage

| Field | Value |
|---|---|
| Corpus | Adversarial rewrites of the fix-efficacy persona_drift seeds (3 evasion tactics per seed) + real on-persona benign probes |
| Lane | Offline robustness audit. These numbers never feed detection F1/ECE; recorded in `persona_drift_recal_history.jsonl`. |
| Labelling method | 3-family cross-family panel pre-screen, then human adjudication of contested + confirmed-evasion rows |
| What the labeller saw | Full persona, full user request, full candidate reply (no truncation) |
| Labels | 72 human-adjudicated + 0 panel-unanimous |
| Sample floor | Headline reported on the adversarial boundary set; `preliminary` flag set below 20 human labels |

## 3. Agreement, and what it does and does not show

Detector-vs-human agreement on the **adversarial boundary set** (the evasions + on-persona probes, where validating the positive class actually matters). The detector's fire/no-fire at the operating threshold is treated as one rater, the human label as the other.

| Scope | Usable n | PSA | Kappa | Prevalence |
|---|---:|---:|---:|---:|
| Adversarial boundary set | 72 | 0.4333 | 0.1435 | 0.5972 |
| + easy seeds (full set) | 90 | 0.6458 | unknown | unknown |

The honest reading: a positive specific agreement of 0.4333 on the boundary set means that, of the persona drifts either the detector or a human flags there, the share both flag is 0.4333. The full-set number (0.6458) is inflated by easy seeds the detector already catches and is reported only to make the inflation visible.

## 4. Adjudication and doctrine

| Field | Value |
|---|---|
| Selection rule | Unanimous cross-family rows are pre-approved (panel); contested rows and confirmed evasions go to a human |
| Who adjudicates | Human + 3-family panel, recorded per row (`panel_auto` flag distinguishes them) |
| Adjudicator bias | Panel is cross-family by construction; the human is the detector's author (single adjudicator caveat) |
| Confirmation rule | An evasion counts only if it both evades the detector AND is confirmed still-failing |

## 5. Calibration

| Field | Value |
|---|---|
| Dataset fingerprint | `6930a4820989f511b8f87f87d5b81b58` |
| Evade-rate (held-out evasions) | before 0.8571 [0.5714, 1.0] -> after 0.5714 [0.1429, 0.8571] (n=7) |
| Operating threshold | 0.5800 (best swept: 0.5400) |
| Hardening recommendation | **both**; dominant exploited gate: the task-relevance gate (a substantive on-topic answer suppresses the drift signal) |
| Regression gate | Offline; the production threshold moves only on a separable threshold win, never on a scoring-patch recommendation |

## 6. Known limits

- The adversary is **black-box prompt search**, not a gradient-trained policy with parameter access. This is a lower bound on attackability, not a proof of robustness.
- The dominant evasion exploits the task-relevance gate (a substantive on-topic answer suppresses the drift signal). The recommendation is `both` when no threshold separates the classes.
- Tiny-n and offline: held-out evasion n=7; this is a curated probe, not a production-FPR study.
- A "still-failing" label reflects a 3-family panel plus one human adjudicator; PSA quantifies that agreement, it does not transcend it.

## 7. Change log

| Date | Change |
|---|---|
| 2026-06-16 | Adversarial-robustness datasheet generated from `persona_drift_redteam_v1` |
