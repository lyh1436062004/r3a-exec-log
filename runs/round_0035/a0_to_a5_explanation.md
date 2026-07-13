# E1-prime Conditions A0-A5

All treatment conditions operate on memories that were actually visible in the saved baseline `context_str_full`. Oracle gold targets are `gold_visible_ids`, derived using gold evidence and therefore valid only as an upper-bound experiment.

| Condition | Context operation | Intended measurement |
|---|---|---|
| A0 | Replay saved `context_str_full` byte for byte | Exact baseline and stable-wrong definition |
| A1 | Move gold-visible memories to the front; preserve all other visible memories and the preference note | Position/promotion effect |
| A2 | Keep only gold-visible memories; remove other memories and the preference note | Oracle filtering effect relative to A1 |
| A3 | Use the A2 filtered context and add REFUTE, SELECT, or CONDITION labels where applicable | Relation-license increment over filtering |
| A4 | Preserve every visible memory in original order and add relation labels only to gold-visible memories | Relation-label effect without filtering or promotion |
| A5 | Use A4, but replace otherwise silent ASSERT on ordinary gold memories with a VOUCH label | Explicit gold-memory identification/backing for all gold-visible memories |

The incremental path `A0 -> A1 -> A2 -> A3` decomposes promotion, filtering, and relation licensing. The path `A0 -> A4 -> A5` studies in-place annotation without deleting or moving memories.

A3 and A4 are silent for ordinary ASSERT cases because ASSERT has no text template. A5 adds: `[证据说明] 该记忆包含回答当前问题所需的关键信息，请优先依据该记忆作答。` This is salience/vouching rather than a relation-specific speech-act license.

Only A0 has been executed in E1-prime so far. A1-A5 have not been run.
