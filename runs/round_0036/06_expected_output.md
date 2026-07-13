# Expected Output of `06_supp_license_analysis.py`

After A1-A5 generation and judging, the script prints:

1. Visible-supported stable-wrong total, licensed count, ASSERT-only count, and REFUTE/SELECT/CONDITION distribution.
2. A0-A5 flip rates with Wilson intervals for `strict_all`, `strict_licensed`, and `strict_assert_only`.
3. McNemar comparisons: licensed A4 vs A0, licensed A3 vs A2, ASSERT-only A4 vs A0, ASSERT-only A5 vs A0, ASSERT-only A5 vs A2, licensed A5 vs A4, and strict-all A5 vs A2.
4. The count of ASSERT-only cases where A4 and A0 verdicts differ, used as a replay-noise sanity check.

It writes `supp_flip_by_license.csv`, `supp_mcnemar_by_license.csv`, and `supp_transitions_licensed.csv`.

At the current A0-only checkpoint, the stable visible-supported total is 737. All remaining values require A1-A5 outputs and are not available yet.
