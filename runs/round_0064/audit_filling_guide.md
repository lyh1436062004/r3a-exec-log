# Experiment 7 Human Audit Filling Guide

Only columns Q-U should be edited:

- Q `human_raw_coverage`
- R `human_rendered_coverage`
- S `human_final_label`
- T `human_confidence`
- U `human_notes`

Columns A-P are provenance and machine outputs. Hide L-P before reviewing to reduce anchoring, and do not change A-P.

## Per-row decision order

1. Read question, gold answer, gold evidence, and all three direct-gold answers.
2. If any direct-gold answer is materially incorrect or incomplete, select `D_judge_error` as the final label.
3. Independently judge whether the complete answer is supported by any factual fields in `raw_retrieved_memories`:
   - `contained`: all material components are supported or directly derivable.
   - `partial`: at least one component is supported, but another required component is absent or too vague.
   - `missing`: the requested answer is not supported.
4. Independently judge the exact `ua3_rendered_context` with the same three coverage labels.
5. Map the judgments deterministically:
   - Direct-gold recovery invalid -> `D_judge_error`
   - Raw is partial/missing -> `A_evidence_missing`
   - Raw contained and rendered partial/missing -> `B_present_not_rendered`
   - Raw contained and rendered contained -> `C_rendered_not_used`

If rendered coverage appears stronger than raw coverage, use `uncertain`, select low confidence, and explain the contradiction for adjudication.

## Evidence rules

- Semantic paraphrase and ordinary reasoning are allowed; exact string overlap is not required.
- Do not supply a specific person, time, relation, quantity, or state from world knowledge when the raw/context evidence is broader.
- For temporal questions, respect the question cutoff. A later state cannot answer an earlier “as of” question without explicit support.
- `create_time` and `update_time` are system timestamps, not automatically event times.
- Fixed authorization/license sentences are not answer evidence.
- Generalization questions may use directly supported premises, but speculative creative leaps do not count as containment.

## Confidence

- `high`: explicit evidence or unambiguous paraphrase.
- `medium`: multi-hop or temporal reasoning is needed but the conclusion is still well supported.
- `low`: ambiguity, questionable gold definition, contradictory views, or uncertain recovery validity.

Recommended note format:

`Raw: <support/missing fact>; Rendered: <preserved/lost fact>; Final: <why A/B/C/D>; Time: <if relevant>`

Save the completed audit as a new file such as `human_validation_sample_filled.xlsx`; preserve the original blank workbook.
