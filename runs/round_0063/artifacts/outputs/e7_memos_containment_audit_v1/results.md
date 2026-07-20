# Experiment 7 - Containment Audit

## Coverage

- Frozen candidates: 158/158
- Successful automatic audits: 158/158
- Retriever and memory store: frozen; no retrieval or write was performed
- Inference-feature exclusion: no gold memory IDs, partial/distractor labels, or HaluMem distractor labels were supplied to the auditor

## Primary A/B/C/D census

| Label | Count | Share | Wilson 95% CI |
|---|---:|---:|---:|
| A_evidence_missing | 12 | 7.59% | [4.40%, 12.81%] |
| B_present_not_rendered | 73 | 46.20% | [38.61%, 53.97%] |
| C_rendered_not_used | 72 | 45.57% | [38.00%, 53.35%] |
| D_judge_error | 1 | 0.63% | [0.11%, 3.50%] |

## Interpretation

- Upstream content loss (A): 12/158
- Unified-adapter rendering headroom (B): 73/158
- Already rendered but not used (C): 72/158
- Direct-gold recovery/judge error (D): 1/158
- Frozen-retrieval post-retrieval repairable space (B+C): 145/158 (91.77%)

## Coverage diagnostics

- Raw coverage: {'contained': 145, 'missing': 7, 'partial': 6}
- Rendered coverage: {'contained': 72, 'missing': 26, 'partial': 60}
- Temporal information: {'preserved': 99, 'not_needed': 54, 'lost_in_rendering': 1, 'missing_from_raw': 4}

## Resource usage

- GPU hours: 0
- Automatic audit calls: 158
- Recorded token usage: {'completion_tokens': 37286, 'prompt_tokens': 536988, 'total_tokens': 574274, 'prompt_cache_hit_tokens': 6400, 'prompt_cache_miss_tokens': 530588}
- Monetary cost is not asserted because provider pricing was not frozen in the experiment config; token counts are preserved for billing reconstruction.

## Human validation

A deterministic validation workbook with 43 rows was prepared: 13 raw partial/missing and 30 raw contained cases, plus 0 mandatory anomalies not already sampled. The partial/missing stratum is a census when it contains fewer than 30 cases.
