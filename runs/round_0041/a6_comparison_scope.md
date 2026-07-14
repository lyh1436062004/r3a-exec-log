# A6 Comparison Scope

A0 replays the saved baseline `context_str_full` byte-for-byte. A6 instead starts from the same saved `raw_memories`, converts every supported raw schema into canonical text, and serializes all raw objects in their original retrieval order. It preserves the Memos note and adds no filtering, reordering, or authorization. Therefore A6 is a deliberate post-retrieval serializer/admission replacement, not a cosmetic reformat of the A0 string.

Clean causal contrasts:

- A6 versus A0 measures the total effect of unified raw-to-context conversion/admission.
- A7 versus A6 measures the incremental effect of the single unified authorization because their admitted memory ids and order are identical.

A1-A5 operate only on the 737 A0-stable-wrong cases where gold evidence was already visible, while the overall A6 result uses 867 strict cases including 130 serialization-loss cases. The 31.26% A6 rate is therefore not directly comparable with A1-A5.

On the same 737 visible-supported cases, descriptive rates are: A1 11.67%, A2 40.84%, A3 46.13%, A4 9.36%, A5 23.88%, A6 27.41%, and A7 29.72%. These comparisons describe relative outcomes but are not single-variable ablations except for A7 versus A6.
