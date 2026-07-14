# Generation Failure Count In The 1,987 MEMOS Error Cases

## Recommended operational definition

Treat a case as an observed generation failure when:

1. at least one raw memory fully supports a gold evidence item (`strict_supported`);
2. all raw memories are parsed by the canonical serializer;
3. oracle admission retains only gold-supporting memories and adds the relation-specific license (`UA3`);
4. the resulting answer is still judged non-correct.

Under this definition:

- Original baseline-error cases: 1,987
- Strict-supported / oracle-eligible cases: 896
- UA3 correct: 480
- UA3 non-correct: **416**
- UA3 non-correct breakdown: 332 hallucination + 84 omission
- Share of all 1,987 baseline errors: 416 / 1,987 = **20.94%**
- Share of the 896 oracle-eligible cases: 416 / 896 = **46.43%**

## Alternative mutually exclusive taxonomy

If failures are assigned to the first applicable layer and `serialization_loss` takes precedence over
`generation_failure`, the 35 UA3 failures in the serialization-loss stratum are not counted again.
Generation failure among memories already visible in `context_str_full` is then:

- Visible-supported strict cases: 763
- UA3 non-correct: **381** = 304 hallucination + 77 omission
- Serialization-loss strict cases: 133
- Serialization-loss cases still non-correct under UA3: 35 = 28 hallucination + 7 omission
- Cross-layer oracle non-rescue total: 381 + 35 = 416

## Stable-wrong sensitivity

The earlier primary experiment excluded 29 strict cases that became correct during A0 replay. In that
867-case stable-wrong pool, UA3 leaves **405** cases non-correct (323 hallucination + 82 omission).
The full-1,987 accounting should use 416, while 405 is only the stable-wrong sensitivity count.

## Interpretation boundary

`416` is a single-run observed oracle non-rescue count, not proof that these cases are intrinsically
impossible for the language model. A stronger "cannot be rescued" claim requires repeated answer
generation under the identical UA3 context and a prespecified rule such as non-correct in all three runs.
