# R3a-v2.2 Audit Acceptance

## Source
- audit file: outputs/r3a_v2_dev_replay/r3a_v2_new_audit_candidates.csv
- candidate rows: 20

## Human audit result
- strict precision: 8/11 = 72.73%
- acceptable rate: 17/20 = 85.00%
- false_counterevidence count: 3
- true_counterevidence count: 8
- ambiguous_counterevidence count: 8
- not_counterevidence_but_useful count: 1

## Decision
R3a-v2.2 passes the audit gate for AB5 smoke if:
- strict precision >= 60%
- acceptable rate >= 70%
- false_counterevidence <= 6

Result: pass.
