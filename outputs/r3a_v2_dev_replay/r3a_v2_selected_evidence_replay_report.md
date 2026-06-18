# R3a-v2 Selected-Evidence Replay Report

This report evaluates whether v2 would keep or reject the exact v1 selected evidence that was human-audited.
Therefore human selector labels are valid for this report.

## Summary

- total rows: 180
- human true_counterevidence count: 18
- human false_counterevidence count: 131
- human ambiguous_counterevidence count: 27
- human not_counterevidence_but_useful count: 4
- v2 kept count: 18
- v2 rejected count: 162
- true retention: 9/18 (50.00%)
- false rejection: 126/131 (96.18%)
- false retention: 5/131 (3.82%)
- retained precision strict: 9/14 (64.29%)
- retained acceptable rate: 13/18 (72.22%)

## By transition_type

| transition_type | n | kept | rejected |
|---|---:|---:|---:|
| A_gated hallucination?B correct | 30 | 5 | 25 |
| R0 correct?B hallucination | 30 | 4 | 26 |
| R0 omission?B correct | 70 | 5 | 65 |
| R0 omission?B hallucination | 50 | 4 | 46 |

## By human_final_selector_judgment

| judgment | n | kept | rejected |
|---|---:|---:|---:|
| ambiguous_counterevidence | 27 | 4 | 23 |
| false_counterevidence | 131 | 5 | 126 |
| not_counterevidence_but_useful | 4 | 0 | 4 |
| true_counterevidence | 18 | 9 | 9 |

## Reject Reason Distribution

| reject_reason | count |
|---|---:|
| slot_mismatch | 71 |
| premise_anchor_mismatch | 53 |
| not_refuting | 31 |
| temporal_mismatch | 5 |
| absence_not_refutation | 2 |

## True retained examples

- sample_id=R3A-063 qa_key=7:18:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User prefers quiet, purposeful travel experiences that connect with local cultures, and dislikes crowded tourist spots, luxury travel, high‑speed tours, and trips without a clear purpose because they feel overwhelming, excessive, or unfulfi
- sample_id=R3A-123 qa_key=13:18:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User's physical health status changed from "Normal" to "Affected" (later noted as "Improving") due to the chronic condition, prompting focus on recovery and mental resilience.
- sample_id=R3A-128 qa_key=15:29:3 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User prefers documentaries for industry insights and investment inspiration, dislikes romantic comedies as they are predictable and not engaging, and avoids horror movies, favoring intellectually stimulating films over shock‑value content.
- sample_id=R3A-139 qa_key=4:33:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User enjoys spicy Thai cuisine for its bold, exciting flavors, gourmet burgers for their varied flavors and textures, and fresh sushi for its light, refreshing delight, while she avoids canned soup because it tastes processed and lacks the 
- sample_id=R3A-149 qa_key=7:23:8 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User reports a positive and sunny mental health state, no mental health issues, and attributes this outlook to balanced nutrition and regular exercise.

## True rejected examples

- sample_id=R3A-014 qa_key=13:55:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User plans to explore more romantic comedies as part of their leisure activities, valuing the comfort and laughter they provide, marking a shift from their usual preference for action thrillers.
- sample_id=R3A-060 qa_key=6:58:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User favors plant‑based meals for health and sustainability, avoids fast food due to health concerns, and steers clear of highly processed snacks, preferring fresh, natural ingredients.
- sample_id=R3A-061 qa_key=6:60:3 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User avoids sugary sodas for health reasons and energy drinks because they cause jitteriness, while enjoying green tea for its calming health benefits, freshly squeezed juices for refreshment and vitamins, and coffee for its rich flavor and
- sample_id=R3A-067 qa_key=9:29:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User dislikes romantic novels because they lack intellectual stimulation and practical insights, enjoys reading books on cloud computing for work‑relevant knowledge, reads tech industry magazines to stay updated on news and innovations, and
- sample_id=R3A-092 qa_key=19:57:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=premise_anchor_mismatch evidence=User has not yet tried mindfulness practices but is open to exploring stress‑relief exercises to manage stress from the role transition.

## False rejected examples

- sample_id=R3A-001 qa_key=10:19:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=premise_anchor_mismatch evidence=User has recently started reading science fiction novels, a shift from previously avoiding them because of complex plots and futuristic settings.
- sample_id=R3A-003 qa_key=10:27:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=temporal_mismatch evidence=User's life goals are to achieve optimal health and wellness, effectively manage post‑menopausal symptoms without medication, reach a personal wellness score of 95/100, and inspire 10,000 women through health workshops.
- sample_id=R3A-004 qa_key=10:36:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=temporal_mismatch evidence=Susan’s severe bloating has reduced significantly and her mental health feels more stable as a result of the adopted lifestyle changes.
- sample_id=R3A-005 qa_key=10:64:4 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=not_refuting evidence=User's life goals are to achieve optimal health and wellness, effectively manage post‑menopausal symptoms without medication, reach a personal wellness score of 95/100, and inspire 10,000 women through health workshops.
- sample_id=R3A-006 qa_key=10:9:6 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=not_refuting evidence=User's reading preferences: dislikes science fiction novels, self‑help books, and cookbooks with rich recipes because they feel overwhelming, oversimplify emotional issues, and conflict with dietary needs; likes health and wellness guides f

## False retained examples

- sample_id=R3A-007 qa_key=11:10:3 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User likes cultural city tours to learn about societies and history, appreciates nature hikes for peaceful reflection, but dislikes overly crowded tourist spots, restrictive package tours, and beach vacations because they feel chaotic, limi
- sample_id=R3A-040 qa_key=20:45:1 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User likes avocado toast as his go‑to breakfast, enjoying the creamy texture of ripe avocados combined with crunchy toasted bread for a fresh start to his day.
- sample_id=R3A-097 qa_key=1:55:1 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User dislikes heavy metal as it feels too chaotic, preferring soothing and harmonious music; he likes classical music for relaxation and focus, creating a peaceful atmosphere; he enjoys jazz for its improvisational style that stimulates cre
- sample_id=R3A-099 qa_key=20:46:1 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User dislikes adventure‑sports trips, finding them too risky and physically demanding, preferring gentle activities that allow him to enjoy his surroundings without stress.
- sample_id=R3A-118 qa_key=9:32:3 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User dislikes mobile puzzle games for lacking depth and strategic challenge, avoids first‑person shooters due to their fast pace, prefers strategy games that require careful planning and decision‑making, dislikes sports video games preferri

