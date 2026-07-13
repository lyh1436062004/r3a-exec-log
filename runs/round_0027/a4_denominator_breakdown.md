# A4 Denominator Breakdown

All 1,987 selected samples were wrong in the saved original baseline and had non-empty gold evidence.

Of these, 896 were `strict_supported`: at least one retrieved raw memory fully supported at least one gold-evidence item.

Only 213 of the 896 received visible A4 authorization (`REFUTE`, `SELECT`, or `CONDITION`). The remaining 683 were ASSERT-only, and ASSERT had no text template.

Within the 213 actually authorized samples:

- 140 were still non-correct in the fresh A0 replay.
- 47 of those 140 became correct under A4: 33.57% recovery.
- 73 were already correct in A0 before authorization, due to replay instability.
- Of those 73, 58 stayed correct and 15 regressed under A4.
- Therefore A4 ended correct on 105 of the 213 samples, but only 47 are wrong-to-correct recoveries attributable to changed inputs.

Within all 896 strict-supported samples:

- 598 remained wrong under A0 replay.
- 55 became correct under A4.
- However, 8 of those 55 had A4 context identical to A0 because they received no visible authorization.
- Therefore `55/598` is the broad strict-pool flip count, while `47/140` is the clean descriptive recovery count among samples whose prompt actually received authorization.
