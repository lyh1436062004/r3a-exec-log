# round_0016 Analysis: P1 Manual Audit Fill

## Scope

This round filled the 120-row P1 manual audit sheet prepared in round_0015 according to `5?.md` conservative audit guidance.

No API calls were made. No answers were regenerated. R3a selector, prompt, retriever, and memory store were not modified.

## Audit Results

- Candidate rows: 120
- Unique samples: 91
- Final label counts: `{'非反证': 75, '非反证但有用': 43, '模糊反证': 1, '真反证': 1}`
- Should-trigger counts: `{'否': 118, '不确定': 1, '是': 1}`
- Failure-source counts: `{'候选发现器误报': 118, '时间判断问题': 1, 'R3a漏触发': 1}`
- True counterevidence rows: 1
- Ambiguous counterevidence rows: 1
- Should-trigger rows: 1

## Key Rows

- `P1-0077`: marked as true counterevidence and should-trigger R3a because the candidate memory directly says herbal teas were no longer effective during meal-plan planning, refuting the satisfaction/energy premise.
- `P1-0036`: marked as ambiguous counterevidence because it concerns continued hospitality commitment but is temporally far earlier than the 2041 question.

## Interpretation

Most P1 candidates remain high-recall candidate-finder hits, not confirmed counterevidence. This filled audit sheet should be reviewed before any selector change.
