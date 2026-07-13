# Meaning of the `06` Printout

`06` refers to the console output of `06_supp_license_analysis.py`, a supplemental analysis run after A1-A5 generation and judging.

It prints:

1. The visible-supported stable-wrong count, split into samples with visible REFUTE/SELECT/CONDITION licenses and ASSERT-only samples.
2. A0-A5 flip rates with Wilson intervals for all strict cases, licensed cases, and ASSERT-only cases.
3. Paired McNemar comparisons including A4 vs A0, A3 vs A2, and A5 comparisons.
4. The number of ASSERT-only cases whose A4 verdict differs from A0, used as a replay-noise sanity check.

It also writes `supp_flip_by_license.csv`, `supp_mcnemar_by_license.csv`, and `supp_transitions_licensed.csv`.

Only A0 has been run in E1-prime so far. The current valid visible-supported stable-wrong count is 737, but licensed/assert-only membership requires A4 generation metadata. Running 06 now would not produce a valid experimental result.
