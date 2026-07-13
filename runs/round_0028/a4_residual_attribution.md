# Attribution of A4 Residual Errors

The value 166 is not the number of A4-final errors. Among 213 visibly authorized cases, 140 were wrong in A0 and 73 were already correct in A0. A4 recovered 47 of the 140, leaving 93 treatment-eligible cases still wrong.

Cross-condition results for those 93 cases:

- 33 are correct under A2.
- 38 are correct under A3.
- The union corrected by A2 or A3 is 43.
- Therefore 43 of the 93 are demonstrably still addressable by post-retrieval filtering or filtering-plus-authorization.
- 50 remain wrong under A2, A3, and A4.

Evidence coverage among the final 50:

- 35 have every gold-evidence item marked `supported` by the semantic judge.
- 15 have at least one supported item but not complete gold-evidence coverage.

The 15 incomplete-coverage cases cannot be cleanly attributed to the answer model. The 35 complete-coverage cases are candidates for model-side residual analysis, but still require human verification of semantic matching, answer-format constraints, judge correctness, and whether the retrieved memories jointly entail the full gold answer.

The defensible claim is: 50 cases were not corrected by the tested A2/A3/A4 interventions. It is not defensible to claim that no possible post-retrieval admission or usage intervention could correct them.
