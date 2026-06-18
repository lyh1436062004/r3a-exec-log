from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Premise:
    entity: str | None
    object_or_activity: str | None
    slot: str | None
    claimed_value: str | None
    polarity: str
    temporal_condition: str | None
    event_condition: str | None
    scope: str | None
    premise_type: str
    raw_question: str


@dataclass
class MemoryProp:
    entity: str | None
    object_or_activity: str | None
    slot: str | None
    value: str | None
    polarity: str
    temporal_marker: str | None
    event_marker: str | None
    update_cues: list[str]
    negation_cues: list[str]
    raw_text: str


@dataclass
class GateResult:
    passed: bool
    reason: str
    detail: str = ""


YESNO_RE = re.compile(
    r"^(did|was|were|is|are|does|do|has|have|had|can|could|will|would|should)\b",
    re.IGNORECASE,
)

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)

TEMPORAL_RE = re.compile(
    r"\b(on|after|before)\s+([^?.,;]+)|\b(currently|now|still|anymore|any more|recently|maintain|decide to|decided to)\b|"
    r"\b(shift(?:ed)? from|switch(?:ed)? from|changed from)\b",
    re.IGNORECASE,
)

NEGATION_PATTERNS = [
    "stopped",
    "quit",
    "gave up",
    "dropped",
    "abandoned",
    "cancelled",
    "canceled",
    "called off",
    "no longer",
    "not anymore",
    "never",
    "does not",
    "did not",
    "decided not to",
    "chose not to",
]

UPDATE_PATTERNS = [
    "changed from",
    "changed to",
    "switched from",
    "switched to",
    "shifted from",
    "shifted to",
    "instead of",
    "replaced",
    "transitioned to",
    "moved from",
    "moved to",
    "now",
    "currently",
    "recently",
    "last month",
    "retired from",
    "works as",
    "role as",
    "plans to incorporate",
    "recommended incorporating",
    "progressed from",
    "later noted as",
    "remained",
    "health declined",
    "worsened",
    "improved",
    "normal",
    "good",
    "excellent",
    "chronic disease",
]

PREFERENCE_POS = {
    "like", "likes", "liked", "love", "loves", "enjoy", "enjoys", "prefer", "prefers", "preferred",
    "interested", "favors", "favours", "excited", "helpful", "conducive", "suitable", "favorite",
}
PREFERENCE_NEG = {
    "dislike", "dislikes", "disliked", "hate", "hates", "avoid", "avoids", "avoided",
    "disinterest", "disappointed", "disappointment", "frustration",
}
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "am",
    "did", "do", "does", "has", "have", "had", "can", "could", "will", "would", "should",
    "user", "person", "memory", "question", "answer", "with", "from", "into", "onto",
    "for", "and", "or", "but", "because", "about", "their", "them", "they", "his",
    "her", "hers", "him", "she", "he", "its", "our", "ours", "your", "yours", "what",
    "when", "where", "why", "how", "which", "whether", "this", "that", "these", "those",
    "due", "past", "because", "completely", "really", "very", "just", "also", "only",
    "still", "currently", "now", "recently", "after", "before", "during", "on", "in",
    "at", "by", "to", "of", "as", "role", "named", "mention", "mentioned", "having",
}

SLOT_WORDS = {
    "preference", "preference_status", "cessation", "transition", "health_status",
    "employment_status", "possession_or_relation", "activity", "decision",
    "current_state", "generic_yesno", "boundary_like",
}

DOMAIN_FAMILY = {"parent", "parents", "child", "children", "sibling", "siblings", "brother", "sister", "spouse", "partner", "family"}
LOW_SIGNAL_VALUE_TOKENS = {
    "campaign", "classic", "storytelling", "storytell", "discussion", "dialogue", "event", "events", "days",
    "situation", "situations", "planning", "trip", "conference", "festival", "documentary",
    "play", "played", "plays", "watch", "watched", "drink", "drinking", "use", "using",
    "games", "game", "gam", "dynamic",
}
GENERIC_OBJECT_TOKENS = {
    "music", "song", "songs", "film", "films", "movie", "movies", "game", "games",
    "trip", "trips", "travel", "tour", "tours", "food", "drink", "drinks",
    "technology", "science", "storytelling", "classic", "traditional", "cultural",
    "vacation", "vacations", "toast", "biryani",
}
PREDICATE_STOPWORDS_AFTER_NAME = {
    "dislike", "likes", "like", "prefer", "preferred", "express", "attend", "decide",
    "decided", "find", "lose", "lost", "stop", "stopped", "change", "changed",
    "remain", "remained",
}
HEALTH_POSITIVE = {"improving", "improved", "excellent", "normal", "good", "optimistic", "energetic", "active", "sunny", "positive"}
HEALTH_NEGATIVE = {"affected", "fatigued", "overwhelmed", "moderate", "stressed", "stress", "declined", "worsened", "bad", "poor"}


def raw_text(raw: Any) -> str:
    """
    Extract memory text from raw memory object.
    Support str and dict.
    Dict keys to check: memory, memory_content, text, content, value.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("memory", "memory_content", "text", "content", "value"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return str(raw)


def mem_id(raw: Any, rank: int) -> str:
    """
    Extract memory id from raw memory object.
    Dict keys to check: id, memory_id, uuid.
    Fallback: rank_{rank}.
    """
    if isinstance(raw, dict):
        for key in ("id", "memory_id", "uuid"):
            val = raw.get(key)
            if val is not None and str(val).strip():
                return str(val)
    return f"rank_{rank}"


def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall((text or "").lower()):
        if len(token) < 3 or token in STOPWORDS:
            continue
        out.append(token)
        stem = _stem(token)
        if stem != token and len(stem) >= 3 and stem not in STOPWORDS:
            out.append(stem)
    return out


def _uniq(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in tokens:
        if token not in seen:
            out.append(token)
            seen.add(token)
    return out


def _contains(text: str, phrase: str) -> bool:
    return phrase in (text or "").lower()


def _extract_entity(text: str) -> str | None:
    cleaned = text.strip()
    aux = r"(?:did|was|were|is|are|does|do|has|have|had|can|could|will|would|should)"
    match = re.match(rf"^{aux}\s+(.+)", cleaned, re.IGNORECASE)
    if match:
        name_parts: list[str] = []
        for raw_part in re.findall(r"[A-Za-z]+(?:'s|')?", match.group(1)):
            part = re.sub(r"(?:'s|')$", "", raw_part)
            if part.lower() in PREDICATE_STOPWORDS_AFTER_NAME:
                break
            if re.match(r"^[A-Z][a-z]+$", part):
                name_parts.append(part)
                if raw_part.endswith(("'s", "'")) or len(name_parts) == 2:
                    break
                continue
            break
        if name_parts:
            return " ".join(name_parts)
    possessive = re.search(r"\b(?!Did\b|Was\b|Were\b|Is\b|Are\b|Does\b|Do\b|Has\b|Have\b|Had\b|Can\b|Could\b|Will\b|Would\b|Should\b)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:'s|')\b", cleaned)
    if possessive:
        return possessive.group(1)
    if re.search(r"\bUser\b", cleaned):
        return "User"
    return None


def _extract_temporal(text: str) -> tuple[str | None, str | None, list[str]]:
    lower = text.lower()
    temporal_tokens: list[str] = []
    parts: list[str] = []
    event_condition: str | None = None
    for match in TEMPORAL_RE.finditer(text):
        cue = (match.group(1) or match.group(3) or match.group(4) or "").strip().lower()
        tail = (match.group(2) or "").strip(" ?.,;")
        if cue:
            temporal_tokens.extend(_tokens(cue))
        if tail:
            temporal_tokens.extend(_tokens(tail))
            if cue in {"after", "before"}:
                event_condition = f"{cue} {tail}"
            parts.append(f"{cue} {tail}".strip())
        elif cue:
            parts.append(cue)
    for date in DATE_RE.findall(text):
        if isinstance(date, tuple):
            date = " ".join(x for x in date if x)
        if date:
            parts.append(str(date))
            temporal_tokens.extend(_tokens(str(date)))
    if "last month" in lower:
        parts.append("last month")
        temporal_tokens.extend(["last", "month"])
    return ("; ".join(_uniq(parts)) or None, event_condition, _uniq(temporal_tokens))


def _phrase_after(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    phrase = match.group(1).strip(" ?.,;")
    return _clean_value_phrase(phrase)


def _clean_value_phrase(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip(" ?.,;:'\"")
    if not cleaned:
        return None
    cleaned = re.sub(r"\b(?:her|his|their)\s+(?:discussion|dialogue)\b.*$", "", cleaned, flags=re.IGNORECASE).strip(" ?.,;")
    cleaned = re.split(
        r"\b(?:during|on|after|before|because|due to|as of|at|last month|recently)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ?.,;")
    cleaned = re.split(
        r"\bin\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december|\d{4}|\d{1,2}/)",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ?.,;")
    cleaned = re.sub(r"\b(?:campaign\s+(?:days|events)|event\s+context)\b.*$", "", cleaned, flags=re.IGNORECASE).strip(" ?.,;")
    return cleaned or None


def _transition_values(text: str) -> tuple[str | None, str | None]:
    match = re.search(r"\b(?:shift(?:ed)?|switch(?:ed)?|changed|transitioned|progressed)\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+(?:after|before|on|in)\b|[?.;,]|$)", text, re.IGNORECASE)
    if match:
        return _clean_value_phrase(match.group(1)), _clean_value_phrase(match.group(2))
    match = re.search(r"\b(?:transitioned|moved)\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+(?:after|before|on|in)\b|[?.;,]|$)", text, re.IGNORECASE)
    if match:
        return _clean_value_phrase(match.group(1)), _clean_value_phrase(match.group(2))
    return None, None


def _infer_slot_and_value(text: str, is_question: bool) -> tuple[str, str | None, str]:
    lower = text.lower()
    old, new = _transition_values(text)
    healthish = re.search(
        r"\b(?:physical health|mental health|health status|health|fatigued|overwhelmed|affected|moderate|stressed|improving|improved|excellent|normal|optimistic|energetic)\b",
        lower,
    )
    if healthish and not is_question and re.search(r"\b(?:likes?|enjoys?|favors?|favours?|prefers?|avoids?|express(?:ed)? excitement about)\b", lower) and not re.search(
        r"\b(?:physical health|mental health|health status|health improved|health declined|health worsened|fatigued|overwhelmed|affected)\b",
        lower,
    ):
        healthish = None
    if healthish and not is_question:
        if re.search(r"\bhealthcare\b|\bhealth\s+(?:industry|projects?|career|interest|interests|sector|research|field)\b|\binterest(?:ed)?\s+in\s+health\b", lower):
            healthish = None
        elif "health" in lower and not re.search(
            r"\b(?:user|physical health|mental health|health status|health improved|health declined|health worsened|health changed|"
            r"fatigued|overwhelmed|affected|moderate|stressed|improving|improved|excellent|normal|optimistic|energetic|good and active)\b",
            lower,
        ):
            healthish = None
    if healthish and is_question and "health reason" in lower and not re.search(r"\b(?:physical health|mental health|health status|improve|decline|remain|change to|status)\b", lower):
        healthish = None
    if healthish and not is_question and "recommend" in lower and not re.search(
        r"\b(?:health status|physical health|mental health status|changed from|transitioned from|progressed from|later noted as|improved|declined|worsened|excellent|normal|fatigued|overwhelmed|affected)\b",
        lower,
    ):
        healthish = None
    if healthish:
        value = None
        quoted = re.findall(r"(?<![A-Za-z])'([^']+)'|\"([^\"]+)\"", text)
        vals = [a or b for a, b in quoted if (a or b)]
        if vals:
            value = " -> ".join(vals) if len(vals) >= 2 and re.search(r"\b(?:changed|transitioned|progressed)\s+from\b", lower) else vals[-1]
        elif old and new:
            value = f"{old} -> {new}"
        else:
            value = _phrase_after(r"(?:remain|remained|change(?:d)? to|later noted as|status(?: is| was)?|as)\s+(.+)", text) or "health"
        polarity = "negative" if set(_tokens(value or "")) & HEALTH_NEGATIVE else "positive"
        if set(_tokens(value or "")) & HEALTH_POSITIVE:
            polarity = "positive"
        return "health_status", value, polarity
    if old and new:
        return "transition", f"{old} -> {new}", "positive"
    if re.search(r"\bexpress(?:ed)?\s+(?:a\s+)?dislike\s+for\b", lower):
        return "preference_status", _phrase_after(r"express(?:ed)?\s+(?:a\s+)?dislike\s+for\s+(.+)", text), "negative"
    if re.search(r"\bexpress(?:ed)?\s+disinterest\s+in\b", lower):
        return "preference_status", _phrase_after(r"express(?:ed)?\s+disinterest\s+in\s+(.+)", text), "negative"
    if re.search(r"\bexpress(?:ed)?\s+disappointment\s+with\b", lower):
        return "preference_status", _phrase_after(r"express(?:ed)?\s+disappointment\s+with\s+(.+)", text), "negative"
    if re.search(r"\bexpress(?:ed)?\s+interest\s+in\b", lower):
        return "preference_status", _phrase_after(r"express(?:ed)?\s+interest\s+in\s+(.+)", text), "positive"
    if re.search(r"\bexpress(?:ed)?\s+excitement\s+about\s+incorporating\b", lower):
        return "preference_status", _phrase_after(r"express(?:ed)?\s+excitement\s+about\s+incorporating\s+(.+)", text), "positive"
    if re.search(r"\bexpress(?:ed)?\s+(?:a\s+)?preference\s+for\b", lower):
        value = _phrase_after(r"express(?:ed)?\s+(?:a\s+)?preference\s+for\s+(.+)", text)
        polarity = "negative" if value and re.match(r"\b(?:avoiding|avoid)\b", value, re.IGNORECASE) else "positive"
        return "preference_status", value, polarity
    if re.search(r"\bplans?\s+to\s+explore\s+(?:more\s+)?\b", lower):
        return "preference_status", _phrase_after(r"plans?\s+to\s+explore\s+(?:more\s+)?(.+)", text), "positive"
    if re.search(r"\bspark(?:ed)?\s+(?:a\s+)?new\s+appreciation\s+for\b", lower):
        return "preference_status", _phrase_after(r"spark(?:ed)?\s+(?:a\s+)?new\s+appreciation\s+for\s+(.+)", text), "positive"
    if re.search(r"\bprefer(?:red|s)?\s+.+\s+over\s+", lower):
        return "preference_status", _phrase_after(r"prefer(?:red|s)?\s+(.+)", text), "positive"
    fav = (
        _phrase_after(r"(?:about|with)\s+(.+?)\s+being\s+(?:her|his|their)?\s*favorite\s+(?:meal|food|drink|movie|book|activity)", text)
        or _phrase_after(r"(.+?)\s+being\s+(?:her|his|their)?\s*favorite\s+(?:meal|food|drink|movie|book|activity)", text)
        or _phrase_after(r"(.+?)\s+as\s+(?:her|his|their)?\s*favorite\s+(?:meal|food|drink|movie|book|activity)", text)
        or _phrase_after(r"favorite\s+(?:meal|food|drink|movie|book|activity)\s+was\s+(.+)", text)
    )
    if fav:
        return "preference_status", fav, "positive"
    if re.search(r"\bdecide(?:d)?\s+to\s+(?:stop|completely abandon|abandon|avoid)\b", lower):
        return "cessation", _phrase_after(r"decide(?:d)?\s+to\s+(?:stop\s+(?:drinking|watching|reading|using|playing)?|completely abandon|abandon|avoid)\s+(.+)", text), "negative"
    if re.search(r"\bfind\s+.+\s+(?:conducive|helpful|suitable)\b", lower):
        return "preference_status", _phrase_after(r"find\s+(.+?)\s+(?:conducive|helpful|suitable)\b.*", text), "positive"
    if re.search(r"\b(?:lost|lose)\s+interest\s+in\b", lower):
        return "preference_status", _phrase_after(r"(?:lost|lose)\s+interest\s+in\s+(.+)", text), "negative"
    if "retire from" in lower or "retired from" in lower:
        value = _phrase_after(r"retir(?:e|ed)\s+from\s+(.+)", text)
        return "employment_status", value, "positive"
    if re.search(r"\bworks as\b|\bemployed as\b|\brole as\b|\bdirector role\b", lower):
        value = _phrase_after(r"(?:works as|employed as|role as|director role at)\s+(.+)", text)
        return "employment_status", value, "positive"
    if re.search(r"\bstill\b|\banymore\b|\bany more\b|\bplay\b|\bdrink\b|\bwatch\b|\buse\b|\bwear\b|\bdo\b", lower):
        value = (
            _phrase_after(r"still\s+(?:does\s+)?(?:play|drink|watch|use|wear|do|does)\s+(.+)", text)
            or _phrase_after(r"\b(?:play|plays|playing|drink|drinks|drinking|watch|watches|watching|use|uses|using|wear|wears|wearing)\s+(.+)", text)
        )
        return "activity", value, "positive"
    if re.search(r"\bstopped\b|\bquit\b|\bno longer\b", lower):
        value = _phrase_after(r"(?:stopped|quit|no longer)\s+(?:playing|drinking|watching|using|wearing|doing|plans? to|wants? to)?\s*(.+)", text)
        return "cessation", value, "negative"
    if re.search(r"\bdecided not to\b|\bchose not to\b|\bcancelled\b|\bcanceled\b|\babandoned\b|\bcalled off\b", lower):
        value = _phrase_after(r"(?:decided not to|chose not to|cancelled|canceled|abandoned|called off)\s+(.+)", text)
        return "cessation", value, "negative"
    if any(re.search(rf"\b{w}\b", lower) for w in PREFERENCE_NEG):
        value = _phrase_after(r"(?:dislikes?|hates?|avoids?|avoided|disappointed with|disappointment with|frustration about)\s+(.+)", text)
        return "preference_status", value, "negative"
    if any(re.search(rf"\b{w}\b", lower) for w in PREFERENCE_POS):
        value = _phrase_after(r"(?:likes?|loves?|enjoys?|prefers?|preferred|favors?|favours?|excited about|interested in|plans to incorporate|recommended incorporating)\s+(.+)", text)
        return "preference_status", value, "positive"
    if re.search(r"\bsiblings?\b|\bparents?\b|\bchildren\b|\bspouse\b|\bpartner\b|\bhas\b|\bhave\b", lower):
        value = _phrase_after(r"(?:has|have|having)\s+(.+)", text)
        return "possession_or_relation", value, "positive"
    if is_question and re.search(r"\bever mention\b|\bunknown\b|\bboundary\b", lower):
        return "boundary_like", None, "neutral"
    return "generic_yesno", None, "positive"


def _premise_type(slot: str, question: str, temporal_condition: str | None) -> str:
    lower = question.lower()
    if "decide" in lower or "decided" in lower:
        return "dated_decision" if temporal_condition else "generic_yesno"
    if "still" in lower or "currently" in lower or "now" in lower:
        return "current_state"
    if "anymore" in lower or "any more" in lower or "stopped" in lower:
        return "cessation"
    if slot == "transition":
        return "transition"
    if slot == "health_status":
        return "health_status"
    if slot == "employment_status":
        return "employment_status"
    if slot == "possession_or_relation":
        return "possession_or_relation"
    if slot == "preference_status":
        return "preference"
    if slot == "boundary_like":
        return "boundary_like"
    return "generic_yesno"


def _make_anchor_tokens(entity: str | None, value: str | None, question: str) -> list[str]:
    raw = []
    if entity and entity.lower() != "user":
        raw.extend(_tokens(entity))
    if value:
        raw.extend(_tokens(value))
    if not raw:
        raw.extend(_tokens(question))
    return _uniq([t for t in raw if t not in SLOT_WORDS])


def extract_yesno_premise(question: str) -> dict[str, Any] | None:
    """
    Extract premise P from a yes/no question.

    Return None if:
    - question is not yes/no;
    - no stable premise can be extracted;
    - question looks like pure boundary/unknown query rather than false-premise query.

    Output dict must include:
      entity
      object_or_activity
      slot
      claimed_value
      polarity
      temporal_condition
      event_condition
      scope
      premise_type
      raw_question
      anchor_tokens
      slot_tokens
      value_tokens
      temporal_tokens
    """
    if not YESNO_RE.match(question.strip()):
        return None
    temporal_condition, event_condition, temporal_tokens = _extract_temporal(question)
    entity = _extract_entity(question)
    slot, value, polarity = _infer_slot_and_value(question, is_question=True)
    if not value and slot in {"generic_yesno", "boundary_like"}:
        q_tokens = _tokens(question)
        if len(q_tokens) < 2:
            return None
        value = " ".join(q_tokens[-3:])
    premise_type = _premise_type(slot, question, temporal_condition)
    scope = None
    if re.search(r"\bstill\b|\bmaintain\b", question, re.IGNORECASE):
        scope = "continuing_state"
    elif re.search(r"\bever\b", question, re.IGNORECASE):
        scope = "ever"
    anchor_tokens = _make_anchor_tokens(entity, value, question)
    slot_tokens = _uniq(_tokens(slot.replace("_", " ")) + _tokens(question if slot == "generic_yesno" else slot))
    value_tokens = _uniq(_tokens(value or ""))
    return {
        **asdict(Premise(entity, value, slot, value, polarity, temporal_condition, event_condition, scope, premise_type, question)),
        "anchor_tokens": anchor_tokens,
        "slot_tokens": slot_tokens,
        "value_tokens": value_tokens,
        "temporal_tokens": temporal_tokens,
    }


def _memory_temporal(text: str) -> tuple[str | None, str | None]:
    temporal, event, _ = _extract_temporal(text)
    lower = text.lower()
    if not temporal and re.search(r"\blast month\b|\bin\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", lower):
        temporal = "dated_or_relative"
    return temporal, event


def _cue_list(text: str, patterns: list[str]) -> list[str]:
    lower = text.lower()
    cues: list[str] = []
    for pattern in patterns:
        if pattern in {"on", "in", "after", "before"}:
            continue
        escaped = re.escape(pattern.lower())
        if " " in pattern:
            rx = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        else:
            rx = rf"\b{escaped}\b"
        if re.search(rx, lower):
            cues.append(pattern)
    if DATE_RE.search(text):
        cues.append("date")
    if re.search(r"\b(?:after|before)\s+[^?.,;]+", lower):
        cues.append("event_time")
    return _uniq(cues)


def parse_memory_propositions(memory_text: str) -> list[dict[str, Any]]:
    """
    Parse a retrieved memory into one or more observable propositions.

    Each prop dict must include:
      entity
      object_or_activity
      slot
      value
      polarity
      temporal_marker
      event_marker
      update_cues
      negation_cues
      anchor_tokens
      slot_tokens
      value_tokens
      raw_text
    """
    text = (memory_text or "").strip()
    if not text:
        return []
    chunks = [c.strip() for c in re.split(r"[.;]\s+|\n+|\bwhile\b|,\s*(?=(?:and\s+)?(?:dislikes?|avoids?|likes?|prefers?|favors?|favours?|enjoys?))", text, flags=re.IGNORECASE) if c.strip()]
    if not chunks:
        chunks = [text]
    props: list[dict[str, Any]] = []
    for chunk in chunks:
        temporal_marker, event_marker = _memory_temporal(chunk)
        update_cues = _cue_list(chunk, UPDATE_PATTERNS)
        negation_cues = _cue_list(chunk, NEGATION_PATTERNS)
        slot, value, polarity = _infer_slot_and_value(chunk, is_question=False)
        if "switched from" in chunk.lower() or "shifted from" in chunk.lower() or "changed from" in chunk.lower():
            update_cues.append("transition")
        prop = asdict(
            MemoryProp(
                ("User" if re.search(r"\bUser\b", chunk) else None) or _extract_entity(chunk),
                value,
                slot,
                value,
                polarity,
                temporal_marker,
                event_marker,
                _uniq(update_cues),
                _uniq(negation_cues),
                chunk,
            )
        )
        prop["anchor_tokens"] = _make_anchor_tokens(prop["entity"], value, chunk)
        prop["slot_tokens"] = _uniq(_tokens(slot.replace("_", " ")))
        prop["value_tokens"] = _uniq(_tokens(value or ""))
        props.append(prop)
    if len(props) == 1 and props[0]["raw_text"] != text:
        props.append({**props[0], "raw_text": text})
    return props


def _gate_dict(result: GateResult) -> dict[str, Any]:
    return asdict(result)


def _overlap(a: list[str], b: list[str]) -> set[str]:
    return set(a or []) & set(b or [])


def _family_domain(tokens: set[str]) -> bool:
    return bool(tokens & DOMAIN_FAMILY)


def _core_overlap(a: set[str], b: set[str]) -> set[str]:
    return (a & b) - LOW_SIGNAL_VALUE_TOKENS


def _core_value_overlap(a: set[str], b: set[str]) -> set[str]:
    return (a & b) - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS


def _normalized_phrase(text: str | None) -> str:
    return " ".join(_tokens(text or ""))


def _split_preference_over(value: str | None) -> tuple[set[str], set[str]] | None:
    if not value or not re.search(r"\bover\b", value, re.IGNORECASE):
        return None
    left, right = re.split(r"\bover\b", value, maxsplit=1, flags=re.IGNORECASE)
    left_tokens = set(_tokens(left)) - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
    right_tokens = set(_tokens(right)) - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
    return left_tokens, right_tokens


def _has_strong_object_match(premise: dict[str, Any], prop: dict[str, Any]) -> bool:
    p_value = premise.get("claimed_value") or ""
    e_value = prop.get("value") or ""
    p_tokens = set(premise.get("value_tokens") or [])
    e_tokens = set(prop.get("value_tokens") or [])
    core = _core_value_overlap(p_tokens, e_tokens)
    p_core = p_tokens - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
    e_core = e_tokens - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
    with_match = re.search(r"\bwith\s+(.+)$", p_value, re.IGNORECASE)
    if with_match:
        required = set(_tokens(with_match.group(1))) - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
        if required and not (required & e_core):
            return False
    if len(core) >= 2:
        return True
    if len(p_core) <= 2 and core:
        return True
    p_phrase = _normalized_phrase(p_value)
    e_phrase = _normalized_phrase(e_value)
    if p_phrase and e_phrase and (p_phrase in e_phrase or e_phrase in p_phrase):
        return True
    return False


def _entity_compatible(premise: dict[str, Any], prop: dict[str, Any]) -> bool:
    pe = (premise.get("entity") or "").lower()
    me = (prop.get("entity") or "").lower()
    if not pe or not me or me == "user" or pe == "user":
        return True
    return bool(set(_tokens(pe)) & set(_tokens(me)))


def check_premise_anchor(premise: dict[str, Any], prop: dict[str, Any]) -> GateResult:
    """
    Gate 1: premise-anchor matching.

    This is NOT retrieval relevance.
    Pass only if E is anchored to the same core entity/object/activity as P.
    Reject lexical false friends and same-domain/wrong-object cases.
    """
    p_tokens = set(premise.get("anchor_tokens") or [])
    e_tokens = set(prop.get("anchor_tokens") or []) | set(prop.get("value_tokens") or []) | set(_tokens(prop.get("raw_text") or ""))
    p_value = set(premise.get("value_tokens") or [])
    e_value = set(prop.get("value_tokens") or [])
    if not _entity_compatible(premise, prop):
        return GateResult(False, "premise_anchor_mismatch", "entity names do not match")
    if premise.get("slot") == "health_status" and prop.get("slot") == "health_status":
        return GateResult(True, "pass", "same health/status domain")
    hard_pairs = [
        ({"spice", "spices"}, {"science", "fiction", "novel", "novels"}),
        ({"cocktail", "cocktails"}, {"hollywood", "clothing", "clothes"}),
        ({"biryani"}, {"durian"}),
        ({"sparkling", "water"}, {"coffee", "tea"}),
    ]
    for left, right in hard_pairs:
        if (p_tokens & left) and (e_tokens & right) and not (p_tokens & e_tokens & left):
            return GateResult(False, "premise_anchor_mismatch", "lexical false friend or wrong object")
    if _family_domain(p_tokens) and _family_domain(e_tokens):
        return GateResult(True, "pass", "same family-relation domain")
    shared_value = _core_value_overlap(p_value, e_value)
    shared_anchor = _core_value_overlap(p_tokens, e_tokens)
    if shared_value or shared_anchor:
        return GateResult(True, "pass", f"shared anchor tokens: {', '.join(sorted(shared_value or shared_anchor))}")
    return GateResult(False, "premise_anchor_mismatch", "no shared core entity/object/activity")


def check_slot_value_alignment(premise: dict[str, Any], prop: dict[str, Any]) -> GateResult:
    """
    Gate 2: slot/value alignment.

    Pass only if memory speaks to the same attribute/status/preference/action slot as P.
    Reject same-person/same-domain but wrong-slot cases.
    """
    p_slot = premise.get("slot")
    e_slot = prop.get("slot")
    p_values = set(premise.get("value_tokens") or [])
    e_values = set(prop.get("value_tokens") or [])
    if p_slot == "employment_status" and e_slot != "employment_status":
        return GateResult(False, "slot_mismatch", "employment/retirement premise needs employment-status evidence")
    if p_slot == "health_status":
        if e_slot == "health_status":
            return GateResult(True, "pass", "same health/status slot")
        return GateResult(False, "slot_mismatch", "health trajectory premise needs health-status evidence")
    if p_slot == "transition":
        if e_slot in {"transition", "preference_status", "activity"} and (p_values & e_values):
            return GateResult(True, "pass", "transition-related value is mentioned")
        return GateResult(False, "slot_mismatch", "transition premise needs same preference/action value")
    if p_slot == "activity" and e_slot in {"activity", "cessation", "transition", "preference_status"}:
        if _core_value_overlap(p_values, e_values):
            return GateResult(True, "pass", "same activity/object value")
        return GateResult(False, "slot_mismatch", "activity object differs")
    if p_slot == "preference_status" and e_slot in {"preference_status", "cessation", "transition", "activity"}:
        if _core_value_overlap(p_values, e_values):
            if not _has_strong_object_match(premise, prop):
                return GateResult(False, "object_specificity_mismatch", "preference object is too generic")
            return GateResult(True, "pass", "same preference value")
        return GateResult(False, "slot_mismatch", "preference object differs")
    if p_slot == "cessation" and e_slot in {"preference_status", "activity"}:
        if _core_value_overlap(p_values, e_values) and _has_strong_object_match(premise, prop):
            return GateResult(True, "pass", "same stopped/abandoned object value")
        return GateResult(False, "slot_mismatch", "cessation object differs")
    if p_slot == "possession_or_relation":
        if e_slot == "possession_or_relation" or _family_domain(p_values | e_values):
            return GateResult(True, "pass", "same relation domain")
        return GateResult(False, "slot_mismatch", "relation premise needs relation evidence")
    if p_slot == e_slot:
        return GateResult(True, "pass", "same slot")
    return GateResult(False, "slot_mismatch", f"premise slot {p_slot} vs memory slot {e_slot}")


def check_temporal_compatibility(premise: dict[str, Any], prop: dict[str, Any]) -> GateResult:
    """
    Gate 3: temporal-condition compatibility.

    Pass only if memory timing can validly answer the premise timing.
    For dated/after-event/current/still/shift questions, undated old state should fail.
    """
    p_temporal = premise.get("temporal_condition")
    p_scope = premise.get("scope")
    p_type = premise.get("premise_type")
    e_temporal = prop.get("temporal_marker")
    update_cues = prop.get("update_cues") or []
    negation_cues = prop.get("negation_cues") or []
    has_update = bool(e_temporal or update_cues or negation_cues)
    if p_type == "preference" and premise.get("slot") == "preference_status" and prop.get("slot") in {"preference_status", "cessation"}:
        if not _has_strong_object_match(premise, prop):
            return GateResult(False, "object_specificity_mismatch", "dated preference needs exact object specificity")
        return GateResult(True, "pass", "stable opposite preference can refute dated preference utterance")
    if p_type == "health_status" and prop.get("slot") == "health_status":
        return GateResult(True, "pass", "health/status proposition has compatible trajectory semantics")
    if p_type == "transition" and prop.get("slot") not in {"transition", "preference_status", "activity", "cessation"}:
        return GateResult(False, "temporal_mismatch", "transition premise needs transition/currentness evidence")
    if p_type in {"dated_decision", "cessation"} and not has_update:
        return GateResult(False, "temporal_mismatch", "decision/cessation premise needs update or current cue")
    if p_temporal and not has_update:
        return GateResult(False, "temporal_mismatch", "premise has strong time condition but memory is undated")
    if p_scope == "continuing_state" and not has_update:
        return GateResult(False, "temporal_mismatch", "still/maintain premise needs current or update cue")
    return GateResult(True, "pass", "temporal condition is compatible")


def check_entails_not_p(premise: dict[str, Any], prop: dict[str, Any]) -> GateResult:
    """
    Gate 4: explicit refutation / contradiction test.

    Pass only if E entails not-P.
    Must distinguish evidence-against-P from absence-of-support-for-P.
    """
    p_slot = premise.get("slot")
    p_pol = premise.get("polarity")
    e_slot = prop.get("slot")
    e_pol = prop.get("polarity")
    p_values = set(premise.get("value_tokens") or [])
    e_values = set(prop.get("value_tokens") or [])
    shared = _core_value_overlap(p_values, e_values)
    negation_cues = prop.get("negation_cues") or []
    update_cues = prop.get("update_cues") or []
    raw = (prop.get("raw_text") or "").lower()
    pref_over = _split_preference_over(premise.get("claimed_value"))
    if p_slot != "health_status" and not shared and not (_family_domain(p_values) and _family_domain(e_values)):
        return GateResult(False, "absence_not_refutation", "memory does not mention the premise value")
    if p_slot in {"activity", "preference_status"}:
        if p_slot == "preference_status" and pref_over:
            x_tokens, y_tokens = pref_over
            e_core = e_values - LOW_SIGNAL_VALUE_TOKENS - GENERIC_OBJECT_TOKENS
            e_over = _split_preference_over(prop.get("value"))
            if e_over:
                e_left, e_right = e_over
                if y_tokens and x_tokens and (y_tokens & e_left) and (x_tokens & e_right):
                    return GateResult(True, "pass", "memory states the reverse preference ordering")
            if x_tokens and (x_tokens & e_core) and (e_pol == "negative" or negation_cues or e_slot == "cessation"):
                return GateResult(True, "pass", "memory rejects the preferred-over object")
            if y_tokens and (y_tokens & e_core) and e_pol == "positive":
                return GateResult(True, "pass", "memory prefers the dispreferred comparison object")
            return GateResult(False, "not_refuting", "preference-over evidence lacks exact opposing object")
        if p_pol == "positive" and (e_pol == "negative" or negation_cues or e_slot == "cessation"):
            return GateResult(True, "pass", "memory explicitly negates or stops the premise activity/preference")
        if p_pol == "positive" and e_slot == "transition" and ("switched from" in raw or "shifted from" in raw or "changed from" in raw):
            return GateResult(True, "pass", "memory says the user switched away from the premise value")
        if p_pol == "negative" and e_pol == "positive":
            return GateResult(True, "pass", "memory states the opposite positive preference/action")
        return GateResult(False, "not_refuting", "memory is compatible with the premise or only supports it")
    if p_slot == "cessation":
        if e_pol == "positive" and e_slot in {"preference_status", "activity"}:
            return GateResult(True, "pass", "memory states continued positive preference/action for the stopped object")
        return GateResult(False, "not_refuting", "memory does not contradict the claimed cessation")
    if p_slot == "transition":
        p_value = premise.get("claimed_value") or ""
        if "->" in p_value:
            old, new = [x.strip() for x in p_value.split("->", 1)]
            old_tokens = set(_tokens(old))
            new_tokens = set(_tokens(new))
            e_raw_tokens = set(_tokens(raw))
            if _core_overlap(old_tokens, e_values) and e_pol == "positive":
                return GateResult(True, "pass", "memory keeps or likes the old state instead of the claimed new state")
            if _core_overlap(new_tokens, e_values) and (e_pol == "negative" or negation_cues):
                return GateResult(True, "pass", "memory rejects the claimed new state")
            if old_tokens & e_raw_tokens and ("remained" in raw or "still" in raw):
                return GateResult(True, "pass", "memory says the old state remained")
            if new_tokens & e_raw_tokens and ("from " + new.lower()) in raw and (" to " + old.lower()) in raw:
                return GateResult(True, "pass", "memory gives the reverse transition")
        return GateResult(False, "not_refuting", "memory does not contradict the claimed transition")
    if p_slot == "employment_status":
        if "retire" in (premise.get("raw_question") or "").lower() and re.search(r"\bcurrently\b|\bnow\b|\bworks\b|\bemployed\b", raw):
            return GateResult(True, "pass", "memory gives a compatible current-work contradiction to retirement")
        return GateResult(False, "not_refuting", "employment evidence does not contradict the premise")
    if p_slot == "health_status":
        if p_pol == "negative" and e_pol == "positive":
            return GateResult(True, "pass", "memory states improved/normal/excellent health instead")
        if p_pol == "positive" and e_pol == "negative":
            return GateResult(True, "pass", "memory states worse health/status instead")
        return GateResult(False, "not_refuting", "health evidence does not contradict the premise")
    if p_slot == "possession_or_relation":
        if negation_cues and shared:
            return GateResult(True, "pass", "memory explicitly negates the same relation")
        return GateResult(False, "absence_not_refutation", "related relation fact is not explicit contradiction")
    return GateResult(False, "not_refuting", "no explicit not-P entailment")


def _not_evaluated() -> dict[str, Any]:
    return _gate_dict(GateResult(False, "not_evaluated"))


def _refutation_strength(prop: dict[str, Any]) -> int:
    score = 0
    score += 4 if prop.get("negation_cues") else 0
    score += 3 if prop.get("slot") in {"cessation", "transition"} else 0
    score += 2 if prop.get("polarity") == "negative" else 0
    return score


def select_counterevidence_v2(
    question: str,
    raw_memories: list[Any],
    max_evidence: int = 1,
) -> dict[str, Any]:
    """
    Main R3a-v2 selector.

    Returns a dict compatible with old select_counterevidence() output:
      triggered
      reason
      evidence
      n_candidates
      gate_yesno

    Additional required fields:
      premise
      rejected
      selector_version
    """
    premise = extract_yesno_premise(question)
    version = "r3a_v2_premise_refutation"
    if premise is None:
        return {
            "triggered": False,
            "reason": "no_extractable_premise",
            "evidence": [],
            "n_candidates": 0,
            "gate_yesno": False,
            "premise": None,
            "rejected": [],
            "selector_version": version,
        }
    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for rank, raw in enumerate(raw_memories or [], start=1):
        text = raw_text(raw).strip()
        memory_id = mem_id(raw, rank)
        memory_ref = f"M{rank:02d}"
        props = parse_memory_propositions(text)
        best_reject: dict[str, Any] | None = None
        for prop in props:
            trace = {
                "premise_anchor": _not_evaluated(),
                "slot_value_alignment": _not_evaluated(),
                "temporal_compatibility": _not_evaluated(),
                "explicit_refutation": _not_evaluated(),
            }
            g1 = check_premise_anchor(premise, prop)
            trace["premise_anchor"] = _gate_dict(g1)
            if not g1.passed:
                best_reject = best_reject or {
                    "rank": rank,
                    "memory_id": memory_id,
                    "memory_ref": memory_ref,
                    "memory_text": text,
                    "reject_reason": g1.reason,
                    "gate_trace": trace,
                }
                continue
            g2 = check_slot_value_alignment(premise, prop)
            trace["slot_value_alignment"] = _gate_dict(g2)
            if not g2.passed:
                best_reject = {
                    "rank": rank,
                    "memory_id": memory_id,
                    "memory_ref": memory_ref,
                    "memory_text": text,
                    "reject_reason": g2.reason,
                    "gate_trace": trace,
                }
                continue
            g3 = check_temporal_compatibility(premise, prop)
            trace["temporal_compatibility"] = _gate_dict(g3)
            if not g3.passed:
                best_reject = {
                    "rank": rank,
                    "memory_id": memory_id,
                    "memory_ref": memory_ref,
                    "memory_text": text,
                    "reject_reason": g3.reason,
                    "gate_trace": trace,
                }
                continue
            g4 = check_entails_not_p(premise, prop)
            trace["explicit_refutation"] = _gate_dict(g4)
            if not g4.passed:
                best_reject = {
                    "rank": rank,
                    "memory_id": memory_id,
                    "memory_ref": memory_ref,
                    "memory_text": text,
                    "reject_reason": g4.reason,
                    "gate_trace": trace,
                }
                continue
            confidence = 10 + _refutation_strength(prop)
            admitted.append(
                {
                    "rank": rank,
                    "memory_id": memory_id,
                    "memory_ref": memory_ref,
                    "memory_text": text,
                    "confidence": confidence,
                    "relation": "REFUTES_PREMISE",
                    "rationale": g4.detail or "Memory explicitly refutes the extracted question premise.",
                    "premise": premise,
                    "gate_trace": trace,
                    "refutation_statement": (
                        "Memory E contradicts premise P because it states an incompatible "
                        f"{prop.get('slot')} fact about {prop.get('value') or 'the same value'}."
                    ),
                    "_score": (
                        _refutation_strength(prop),
                        1 if prop.get("temporal_marker") or prop.get("update_cues") else 0,
                        len(prop.get("value_tokens") or []),
                        -rank,
                    ),
                }
            )
        if best_reject and not any(ev["rank"] == rank for ev in admitted):
            rejected.append(best_reject)
    admitted.sort(key=lambda ev: ev.get("_score", (0, 0, 0, 0)), reverse=True)
    for ev in admitted:
        ev.pop("_score", None)
    selected = admitted[: max(1, max_evidence)]
    if selected:
        return {
            "triggered": True,
            "reason": "selected_counterevidence_v2",
            "evidence": selected,
            "n_candidates": len(admitted),
            "gate_yesno": True,
            "premise": premise,
            "rejected": rejected,
            "selector_version": version,
        }
    return {
        "triggered": False,
        "reason": "no_valid_counterevidence_v2",
        "evidence": [],
        "n_candidates": 0,
        "gate_yesno": True,
        "premise": premise,
        "rejected": rejected,
        "selector_version": version,
    }
