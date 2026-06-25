# round_0014 Analysis: R3a-v2.2 Full Offline Opportunity Census

## Scope

This round continued from round_0013 and ran an offline census over the full Mem0 Medium dataset. It used the existing R3a-v2.2 selector for official trigger detection and a separate high-recall heuristic pass to prepare manual-audit leads.

No API calls were made. The selector, prompt, retriever, and memory store were not modified.

## Key Results

- Total samples: 3467
- Memory Conflict samples: 769 (22.1806%)
- R3a-triggered samples, full dataset: 78 (2.2498%)
- R3a-triggered Memory Conflict samples: 78 (10.1430%)
- Memory Conflict samples not triggered by R3a: 691
- Memory Conflict samples not triggered by R3a but with suspected counterevidence candidates: 649
- Memory Conflict plus R0 omission plus untriggered plus suspected candidates: 387
- Manual audit candidate rows: 380
- Manual audit unique samples: 273

## Manual Audit Caveat

The suspected counterevidence candidates are not final labels. They are high-recall leads for manual audit only, and must not be read as true counterevidence or as proof that R3a should have triggered.

## Recommended Next Decision

audit_first_priority_candidates_before_any_selector_change

Before changing R3a-v2.2 selector logic, audit the first-priority candidate rows and separate true counterevidence from merely related, temporal, or lexical-overlap memories.
