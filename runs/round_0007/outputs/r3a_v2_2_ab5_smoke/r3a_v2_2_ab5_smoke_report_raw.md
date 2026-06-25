# Mem0 Medium Five-Route Offline A/B Report

## Setup

- records: 200
- A2 evidence gate: 2 (1.00%)
- Oracle diagnostic gate: 0 (0.00%)
- R0: cached baseline response/label; no generation and no judging.
- A_all: prompt-only correction on all records.
- A_gated: prompt-only correction only on the exact A2 evidence gate; non-gated records reuse R0.
- B_gated: A2-selected counterevidence admission on the exact same gate; non-gated records reuse R0.
- O_oracle: gold-keyword diagnostic selector; not a method result and not an upper bound.
- question_type is used only for reporting, never for routing.

## Decision Logic

Primary test: on the A2-gated subset, compare A_gated vs B_gated. If B_gated beats A_gated, A2-selected evidence has value beyond prompt-only correction. If A_gated is close to B_gated, the gain is mostly prompt strategy. A_all measures the collateral cost of applying the prompt globally.

## Trigger Coverage

| subset | n | A2 gate | A2 gate rate | Oracle gate | Oracle gate rate |
|---|---:|---:|---:|---:|---:|
| All | 200 | 2 | 1.00% | 0 | 0.00% |
| MC+DU | 55 | 2 | 3.64% | 0 | 0.00% |
| Memory Conflict | 49 | 2 | 4.08% | 0 | 0.00% |
| Dynamic Update | 6 | 0 | 0.00% | 0 | 0.00% |
| MC R0-omission | 28 | 0 | 0.00% | 0 | 0.00% |
| MC+DU R0-omission | 31 | 0 | 0.00% | 0 | 0.00% |
| Non-MC+DU | 145 | 0 | 0.00% | 0 | 0.00% |

## All Records - Five Routes

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 200 | 76 (38.00%) | 32 (16.00%) | 92 (46.00%) |
| A_all prompt-only all | 200 | 79 (39.50%) | 29 (14.50%) | 92 (46.00%) |
| A_gated prompt-only same gate | 200 | 76 (38.00%) | 32 (16.00%) | 92 (46.00%) |
| B_gated A2 evidence | 200 | 76 (38.00%) | 32 (16.00%) | 92 (46.00%) |
| O_oracle diagnostic | 200 | 76 (38.00%) | 32 (16.00%) | 92 (46.00%) |

| delta vs R0 | A_all | A_gated | B_gated | Oracle |
|---|---:|---:|---:|---:|
| Delta correct | +3 (+1.50 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |
| Delta hallucination | -3 (-1.50 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |
| Delta omission | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |

## Direct A/B Test on A2-Gated Subset

This is the clean comparison. A_gated and B_gated use the same gate; the only difference is whether A2 selects and admits explicit counterevidence.

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 2 | 2 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| A_gated prompt-only | 2 | 2 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| B_gated A2 evidence | 2 | 2 (100.00%) | 0 (0.00%) | 0 (0.00%) |
| O_oracle diagnostic | 2 | 2 (100.00%) | 0 (0.00%) | 0 (0.00%) |

| delta B_gated vs A_gated | count | pp |
|---|---:|---:|
| Delta correct | +0 | +0.00 pp |
| Delta hallucination | +0 | +0.00 pp |
| Delta omission | +0 | +0.00 pp |

| delta O_oracle vs B_gated | count | pp |
|---|---:|---:|
| Delta correct | +0 | +0.00 pp |
| Delta hallucination | +0 | +0.00 pp |
| Delta omission | +0 | +0.00 pp |

## Non-Gated Subset

A_all shows the cost of global prompt-only correction. A_gated and B_gated are no-op and equal R0 here.

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 198 | 74 (37.37%) | 32 (16.16%) | 92 (46.46%) |
| A_all prompt-only all | 198 | 77 (38.89%) | 29 (14.65%) | 92 (46.46%) |
| A_gated = B_gated = R0 | 198 | 74 (37.37%) | 32 (16.16%) | 92 (46.46%) |

| delta vs R0 | A_all |
|---|---:|
| Delta correct | +3 (+1.52 pp) |
| Delta hallucination | -3 (-1.52 pp) |
| Delta omission | +0 (+0.00 pp) |

## MC+DU Focus

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 55 | 16 (29.09%) | 8 (14.55%) | 31 (56.36%) |
| A_all prompt-only all | 55 | 28 (50.91%) | 12 (21.82%) | 15 (27.27%) |
| A_gated prompt-only same gate | 55 | 16 (29.09%) | 8 (14.55%) | 31 (56.36%) |
| B_gated A2 evidence | 55 | 16 (29.09%) | 8 (14.55%) | 31 (56.36%) |
| O_oracle diagnostic | 55 | 16 (29.09%) | 8 (14.55%) | 31 (56.36%) |

| delta vs R0 | A_all | A_gated | B_gated | Oracle |
|---|---:|---:|---:|---:|
| Delta correct | +12 (+21.82 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |
| Delta hallucination | +4 (+7.27 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |
| Delta omission | -16 (-29.09 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) | +0 (+0.00 pp) |

## Memory Conflict

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| A_all prompt-only all | 49 | 28 (57.14%) | 11 (22.45%) | 10 (20.41%) |
| A_gated prompt-only same gate | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| B_gated A2 evidence | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| O_oracle diagnostic | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |

## Dynamic Update

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| A_all prompt-only all | 6 | 0 (0.00%) | 1 (16.67%) | 5 (83.33%) |
| A_gated prompt-only same gate | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| B_gated A2 evidence | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| O_oracle diagnostic | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |

## MC R0-Omission Subset

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 28 | 0 (0.00%) | 0 (0.00%) | 28 (100.00%) |
| A_all prompt-only all | 28 | 14 (50.00%) | 6 (21.43%) | 8 (28.57%) |
| A_gated prompt-only same gate | 28 | 0 (0.00%) | 0 (0.00%) | 28 (100.00%) |
| B_gated A2 evidence | 28 | 0 (0.00%) | 0 (0.00%) | 28 (100.00%) |
| O_oracle diagnostic | 28 | 0 (0.00%) | 0 (0.00%) | 28 (100.00%) |

## All Question Types

### Basic Fact Recall

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 49 | 13 (26.53%) | 9 (18.37%) | 27 (55.10%) |
| A_all prompt-only all | 49 | 6 (12.24%) | 7 (14.29%) | 36 (73.47%) |
| A_gated prompt-only same gate | 49 | 13 (26.53%) | 9 (18.37%) | 27 (55.10%) |
| B_gated A2 evidence | 49 | 13 (26.53%) | 9 (18.37%) | 27 (55.10%) |
| O_oracle diagnostic | 49 | 13 (26.53%) | 9 (18.37%) | 27 (55.10%) |

### Dynamic Update

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| A_all prompt-only all | 6 | 0 (0.00%) | 1 (16.67%) | 5 (83.33%) |
| A_gated prompt-only same gate | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| B_gated A2 evidence | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |
| O_oracle diagnostic | 6 | 2 (33.33%) | 1 (16.67%) | 3 (50.00%) |

### Generalization & Application

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 34 | 8 (23.53%) | 13 (38.24%) | 13 (38.24%) |
| A_all prompt-only all | 34 | 3 (8.82%) | 7 (20.59%) | 24 (70.59%) |
| A_gated prompt-only same gate | 34 | 8 (23.53%) | 13 (38.24%) | 13 (38.24%) |
| B_gated A2 evidence | 34 | 8 (23.53%) | 13 (38.24%) | 13 (38.24%) |
| O_oracle diagnostic | 34 | 8 (23.53%) | 13 (38.24%) | 13 (38.24%) |

### Memory Boundary

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 46 | 37 (80.43%) | 2 (4.35%) | 7 (15.22%) |
| A_all prompt-only all | 46 | 42 (91.30%) | 2 (4.35%) | 2 (4.35%) |
| A_gated prompt-only same gate | 46 | 37 (80.43%) | 2 (4.35%) | 7 (15.22%) |
| B_gated A2 evidence | 46 | 37 (80.43%) | 2 (4.35%) | 7 (15.22%) |
| O_oracle diagnostic | 46 | 37 (80.43%) | 2 (4.35%) | 7 (15.22%) |

### Memory Conflict

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| A_all prompt-only all | 49 | 28 (57.14%) | 11 (22.45%) | 10 (20.41%) |
| A_gated prompt-only same gate | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| B_gated A2 evidence | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |
| O_oracle diagnostic | 49 | 14 (28.57%) | 7 (14.29%) | 28 (57.14%) |

### Multi-hop Inference

| route | n | correct | hallucination | omission |
|---|---:|---:|---:|---:|
| R0 baseline | 16 | 2 (12.50%) | 0 (0.00%) | 14 (87.50%) |
| A_all prompt-only all | 16 | 0 (0.00%) | 1 (6.25%) | 15 (93.75%) |
| A_gated prompt-only same gate | 16 | 2 (12.50%) | 0 (0.00%) | 14 (87.50%) |
| B_gated A2 evidence | 16 | 2 (12.50%) | 0 (0.00%) | 14 (87.50%) |
| O_oracle diagnostic | 16 | 2 (12.50%) | 0 (0.00%) | 14 (87.50%) |

## Paired Flows

### All

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 14 | 20 | 1 | 4 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### A2-gated

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 0 | 0 | 0 | 0 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### Non-gated

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 14 | 20 | 1 | 4 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### MC+DU

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 2 | 14 | 1 | 1 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### Memory Conflict

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 1 | 14 | 1 | 0 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### MC R0-omission

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 0 | 14 | 0 | 0 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

### Dynamic Update

| flow | correct->omission | omission->correct | hallucination->correct | correct->hallucination |
|---|---:|---:|---:|---:|
| R0->A_all | 1 | 0 | 0 | 1 |
| R0->A_gated | 0 | 0 | 0 | 0 |
| R0->B_gated | 0 | 0 | 0 | 0 |
| A_gated->B_gated | 0 | 0 | 0 | 0 |
| B_gated->Oracle | 0 | 0 | 0 | 0 |

