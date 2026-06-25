# R3a-v2 Selected-Evidence Replay Report

This report evaluates whether v2 would keep or reject the exact v1 selected evidence that was human-audited.
Therefore human selector labels are valid for this report.

## Summary

- total rows: 180
- human true_counterevidence count: 18
- human false_counterevidence count: 131
- human ambiguous_counterevidence count: 27
- human not_counterevidence_but_useful count: 4
- v2 kept count: 17
- v2 rejected count: 163
- true retention: 12/18 (66.67%)
- false rejection: 130/131 (99.24%)
- false retention: 1/131 (0.76%)
- retained precision strict: 12/13 (92.31%)
- retained acceptable rate: 16/17 (94.12%)

## By transition_type

| transition_type | n | kept | rejected |
|---|---:|---:|---:|
| A_gated hallucination?B correct | 30 | 5 | 25 |
| R0 correct?B hallucination | 30 | 4 | 26 |
| R0 omission?B correct | 70 | 6 | 64 |
| R0 omission?B hallucination | 50 | 2 | 48 |

## By human_final_selector_judgment

| judgment | n | kept | rejected |
|---|---:|---:|---:|
| ambiguous_counterevidence | 27 | 4 | 23 |
| false_counterevidence | 131 | 1 | 130 |
| not_counterevidence_but_useful | 4 | 0 | 4 |
| true_counterevidence | 18 | 12 | 6 |

## Reject Reason Distribution

| reject_reason | count |
|---|---:|
| slot_mismatch | 73 |
| premise_anchor_mismatch | 56 |
| not_refuting | 23 |
| temporal_mismatch | 5 |
| object_specificity_mismatch | 3 |
| absence_not_refutation | 3 |

## True retained examples

- sample_id=R3A-014 qa_key=13:55:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User plans to explore more romantic comedies as part of their leisure activities, valuing the comfort and laughter they provide, marking a shift from their usual preference for action thrillers.
- sample_id=R3A-060 qa_key=6:58:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User favors plant‑based meals for health and sustainability, avoids fast food due to health concerns, and steers clear of highly processed snacks, preferring fresh, natural ingredients.
- sample_id=R3A-063 qa_key=7:18:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User prefers quiet, purposeful travel experiences that connect with local cultures, and dislikes crowded tourist spots, luxury travel, high‑speed tours, and trips without a clear purpose because they feel overwhelming, excessive, or unfulfi
- sample_id=R3A-067 qa_key=9:29:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User dislikes romantic novels because they lack intellectual stimulation and practical insights, enjoys reading books on cloud computing for work‑relevant knowledge, reads tech industry magazines to stay updated on news and innovations, and
- sample_id=R3A-123 qa_key=13:18:1 judgment=true_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User's physical health status changed from "Normal" to "Affected" (later noted as "Improving") due to the chronic condition, prompting focus on recovery and mental resilience.

## True rejected examples

- sample_id=R3A-061 qa_key=6:60:3 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User avoids sugary sodas for health reasons and energy drinks because they cause jitteriness, while enjoying green tea for its calming health benefits, freshly squeezed juices for refreshment and vitamins, and coffee for its rich flavor and
- sample_id=R3A-092 qa_key=19:57:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=premise_anchor_mismatch evidence=User has not yet tried mindfulness practices but is open to exploring stress‑relief exercises to manage stress from the role transition.
- sample_id=R3A-137 qa_key=3:51:8 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=not_refuting evidence=User reports that his physical condition is normal, indicating no chronic diseases or ongoing health issues.
- sample_id=R3A-142 qa_key=4:60:1 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=premise_anchor_mismatch evidence=User likes uplifting pop music because it energizes her and supports a positive outlook similar to Shirley Franco's vibrant persona, but she dislikes heavy metal for being too aggressive and slow jazz for being too mellow for her energetic 
- sample_id=R3A-168 qa_key=1:30:5 judgment=true_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User reports his physical health as normal with no chronic diseases, while his mental health is described as mildly abnormal and occasionally strained due to the demanding nature of his role and pressure to deliver high‑quality healthcare s

## False rejected examples

- sample_id=R3A-001 qa_key=10:19:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=premise_anchor_mismatch evidence=User has recently started reading science fiction novels, a shift from previously avoiding them because of complex plots and futuristic settings.
- sample_id=R3A-003 qa_key=10:27:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=temporal_mismatch evidence=User's life goals are to achieve optimal health and wellness, effectively manage post‑menopausal symptoms without medication, reach a personal wellness score of 95/100, and inspire 10,000 women through health workshops.
- sample_id=R3A-004 qa_key=10:36:3 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=temporal_mismatch evidence=Susan’s severe bloating has reduced significantly and her mental health feels more stable as a result of the adopted lifestyle changes.
- sample_id=R3A-005 qa_key=10:64:4 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=not_refuting evidence=User's life goals are to achieve optimal health and wellness, effectively manage post‑menopausal symptoms without medication, reach a personal wellness score of 95/100, and inspire 10,000 women through health workshops.
- sample_id=R3A-006 qa_key=10:9:6 judgment=false_counterevidence reason=no_valid_counterevidence_v2 reject_reason=slot_mismatch evidence=User's reading preferences: dislikes science fiction novels, self‑help books, and cookbooks with rich recipes because they feel overwhelming, oversimplify emotional issues, and conflict with dietary needs; likes health and wellness guides f

## False retained examples

- sample_id=R3A-100 qa_key=20:50:3 judgment=false_counterevidence reason=selected_counterevidence_v2 reject_reason=none evidence=User enjoys documentaries for in‑depth learning, romantic comedies for humor and heartwarming stories, and avoids horror films because they are too intense, as well as action‑packed thrillers due to their violent, high‑tension focus.

