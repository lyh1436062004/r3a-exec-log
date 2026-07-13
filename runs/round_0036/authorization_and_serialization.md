# Authorization and Post-Retrieval Serialization

The omission is not a learned admission decision. Memos returns both fact-memory and preference-memory objects. Preference objects store their usable content in `preference` and `reasoning`, while the baseline serializer recognizes only `memory`, `memory_value`, `memory_key`, `content`, and `text`. It therefore turns preference-only objects into empty strings and omits them from `context_str_full`.

Adding an authorization flag or annotation as another raw metadata field does not fix this: the same serializer will ignore both the preference content and the authorization field.

The controller must operate before final serialization:

`retriever -> raw_memories -> schema normalizer -> admission/authorization -> canonical serializer -> context -> LLM`

For an admitted preference object, normalization should first produce canonical text such as `Preference: ...\nReasoning: ...`; the authorization prefix and canonical text must then be emitted together into the final context. This does not modify the memory store or retriever.

To isolate effects experimentally, use three conditions on omitted gold memories: original context, visibility-only serialization, and the same serialization plus authorization. Visibility-only versus original measures admission recovery; authorized versus visibility-only measures the additional authorization effect.
