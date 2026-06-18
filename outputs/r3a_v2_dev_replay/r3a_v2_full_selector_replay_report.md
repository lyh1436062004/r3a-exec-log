# R3a-v2 Full-Selector Replay Report

This report runs v2 over full raw_memories.
Human labels refer only to the old v1 selected evidence, not necessarily to the v2 selected evidence.
Therefore this report must not report v2 precision from old labels.

## Summary

- total rows: 180
- v2 triggered count: 30
- v2 trigger rate: 16.67%
- matched_original_v1_selected count: 13
- matched_original_v1_selected rate among triggered: 43.33%

## Triggered rows by transition_type

| transition_type | triggered |
|---|---:|
| A_gated hallucination?B correct | 7 |
| R0 correct?B hallucination | 4 |
| R0 omission?B correct | 11 |
| R0 omission?B hallucination | 8 |

## Triggered rows by old v1-selected-evidence label

| old label | triggered |
|---|---:|
| ambiguous_counterevidence | 7 |
| false_counterevidence | 14 |
| true_counterevidence | 9 |

## Reject Reason Distribution

| reject_reason | count |
|---|---:|
| slot_mismatch | 62 |
| absence_not_refutation | 33 |
| premise_anchor_mismatch | 30 |
| not_refuting | 22 |
| temporal_mismatch | 3 |

## Rows triggered by v2 where the old v1-selected evidence was labeled false_counterevidence

- sample_id=R3A-007 qa_key=11:10:3 matched_original_v1_selected=True selected=User likes cultural city tours to learn about societies and history, appreciates nature hikes for peaceful reflection, but dislikes overly crowded tourist spots, restrictive package tours, and beach vacations because they feel chaotic, limi
- sample_id=R3A-010 qa_key=12:34:3 matched_original_v1_selected=False selected=User prefers classic adventure games and vintage-themed puzzle games for their nostalgic storytelling and aesthetic, dislikes mobile games with excessive ads, games lacking strong narratives, and first‑person shooters which he finds chaotic
- sample_id=R3A-029 qa_key=19:30:3 matched_original_v1_selected=False selected=User prefers classical music for a calm, focused atmosphere, enjoys herbal and soft tunes, and avoids heavy metal, loud music, and repetitive pop songs that distract or overwhelm.
- sample_id=R3A-040 qa_key=20:45:1 matched_original_v1_selected=False selected=User prefers grilled salmon because it reminds him of family gatherings with fresh fish, enjoys avocado toast as his go‑to breakfast for its creamy avocado and crunchy toast, likes roasted vegetables for their healthy, caramelized flavor, a
- sample_id=R3A-044 qa_key=2:63:3 matched_original_v1_selected=False selected=User dislikes group tours as they feel restrictive, favors solo travel for cultural immersion and spontaneous decisions, and likes cultural immersion trips to gain deep insights into local ways of life.
- sample_id=R3A-066 qa_key=8:35:1 matched_original_v1_selected=False selected=User dislikes durian because its smell is pungent and texture off‑putting, avoids overly spicy food as it masks natural flavors, dislikes raw onions due to sharp taste and lingering aftertaste, and enjoys biryani for its rich aroma and the 
- sample_id=R3A-076 qa_key=11:39:3 matched_original_v1_selected=False selected=User enjoys watching technology documentaries for insights into future innovations, psychological thrillers for complex characters and unexpected twists that challenge analytical skills, and science‑fiction films for exploring human advance
- sample_id=R3A-089 qa_key=17:60:1 matched_original_v1_selected=False selected=User prefers classical music for its soothing melodies that aid focus and clarity while working on his relative's campaign, and dislikes heavy metal and techno because their aggressive or repetitive sounds disrupt the calm environment he se
- sample_id=R3A-090 qa_key=19:10:1 matched_original_v1_selected=False selected=User enjoys playing puzzle games and science-themed strategy games because they challenge problem‑solving and combine scientific interest with strategic thinking; they avoid violent video games and titles that offer little intellectual chal
- sample_id=R3A-097 qa_key=1:55:1 matched_original_v1_selected=True selected=User dislikes heavy metal as it feels too chaotic, preferring soothing and harmonious music; he likes classical music for relaxation and focus, creating a peaceful atmosphere; he enjoys jazz for its improvisational style that stimulates cre
- sample_id=R3A-099 qa_key=20:46:1 matched_original_v1_selected=True selected=User dislikes adventure‑sports trips, finding them too risky and physically demanding, preferring gentle activities that allow him to enjoy his surroundings without stress.
- sample_id=R3A-109 qa_key=4:67:2 matched_original_v1_selected=False selected=User enjoys spicy Thai cuisine for its bold, exciting flavors, gourmet burgers for their varied flavors and textures, and fresh sushi for its light, refreshing delight, while she avoids canned soup because it tastes processed and lacks the 
- sample_id=R3A-118 qa_key=9:32:3 matched_original_v1_selected=True selected=User dislikes mobile puzzle games for lacking depth and strategic challenge, avoids first‑person shooters due to their fast pace, prefers strategy games that require careful planning and decision‑making, dislikes sports video games preferri
- sample_id=R3A-158 qa_key=14:15:2 matched_original_v1_selected=False selected=User likes roast duck, praising its crispy, fragrant skin and tender, juicy meat as a timeless culinary experience.

