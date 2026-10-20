"""Stage 0: deterministic complete parsing inside a frozen returned collection."""
from __future__ import annotations

import calendar
import logging
import math
import re
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from a2_schema import CapabilityMask, EvidenceRecord

TEXT_FIELDS = ("memory", "memory_value", "memory_key", "memory_type", "tags",
               "preference", "preference_type", "reasoning", "content", "text")
TIME_FIELDS = ("event_time", "event_time_iso", "occurred_at", "chat_time", "timestamp",
               "created_at", "updated_at", "create_time", "update_time")
EVENT_FIELDS = frozenset(TIME_FIELDS[:4])
SYSTEM_FIELD_SPEC = {
    name: {"text_fields": TEXT_FIELDS, "time_fields": TIME_FIELDS,
           "session_fields": ("source_session", "conversation_id", "session_id", "chat_id")}
    for name in ("memos", "mem0", "memobase", "supermemory", "longmemeval")
}
EMPTY_VALUES = frozenset(("", "none", "null", "n/a"))
MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})
LOG = logging.getLogger(__name__)


def scalar_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    return "" if text.lower() in EMPTY_VALUES else text


def canonical_text(item: Any, system_kind: str = "memos") -> str:
    if isinstance(item, str):
        text = scalar_text(item)
        return "text: " + text if text else ""
    if not isinstance(item, dict):
        return ""
    spec = SYSTEM_FIELD_SPEC[system_kind]
    parts: list[str] = []
    seen: set[tuple[str, str]] = set()
    for key in spec["text_fields"]:
        value = item.get(key)
        if key == "tags" and isinstance(value, list):
            value = ",".join(scalar_text(v) for v in value if scalar_text(v))
        text = scalar_text(value)
        if text and (key, text) not in seen:
            parts.append(f"{key}: {text}")
            seen.add((key, text))
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        for key in sorted(metadata):
            text = scalar_text(metadata[key])
            name = f"metadata.{key}"
            if text and (name, text) not in seen:
                parts.append(f"{name}: {text}")
                seen.add((name, text))
    return " | ".join(parts)


def parse_time(value: Any) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            return None
        try:
            number = value / 1000 if abs(value) > 10**11 else value
            return datetime.fromtimestamp(number, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    text = scalar_text(value)
    if not text:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            datetime.strptime(text, "%Y-%m-%d")
            return text
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        for fmt in ("%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.strptime(text, fmt).isoformat()
            except ValueError:
                continue
    return None


def text_time(text: str) -> tuple[str | None, tuple[str, str] | None]:
    exact = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if exact:
        parsed = parse_time(exact.group(1))
        if parsed:
            return parsed, (parsed, parsed)
    month = re.search(r"\b(?:in\s+|since\s+)?(" + "|".join(MONTHS) +
                      r")\s+(\d{4})\b", text, re.I)
    if month:
        year, number = int(month.group(2)), MONTHS[month.group(1).lower()]
        lo = f"{year:04d}-{number:02d}-01"
        hi = f"{year:04d}-{number:02d}-{calendar.monthrange(year, number)[1]:02d}"
        return lo, (lo, hi)
    year_match = re.search(r"\b(?:since|in|during)\s+(\d{4})\b", text, re.I)
    if year_match:
        year = int(year_match.group(1))
        if 1 <= year <= 9999:
            lo, hi = f"{year:04d}-01-01", f"{year:04d}-12-31"
            return lo, (lo, hi)
    # Relative dates without a reference date cannot be resolved without fabrication.
    return None, None


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def adapt(raw_memories: list[Any], system_kind: str) -> list[EvidenceRecord]:
    if system_kind not in SYSTEM_FIELD_SPEC:
        raise ValueError(f"Unknown system_kind: {system_kind}")
    spec = SYSTEM_FIELD_SPEC[system_kind]
    records: list[EvidenceRecord] = []
    rejected: list[dict[str, Any]] = []
    for index, item in enumerate(raw_memories):
        text = canonical_text(item, system_kind)
        if not text:
            rejected.append({"raw_index": index, "rejected": "empty_text"})
            continue
        data = item if isinstance(item, dict) else {}
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        event = ingest = None
        for key in spec["time_fields"]:
            for container in (metadata, data):
                parsed = parse_time(container.get(key))
                if parsed:
                    if key in EVENT_FIELDS and event is None:
                        event = parsed
                    if key not in EVENT_FIELDS and ingest is None:
                        ingest = parsed
        interval = None
        if event:
            source, proxy = "meta_event", False
        elif ingest:
            source, proxy = "meta_ingest", True
        else:
            event, interval = text_time(text)
            source, proxy = ("text_cue", False) if event else ("none", False)
        anchors: list[str] = []
        supplied_anchors = data.get("entity_anchors")
        if isinstance(supplied_anchors, str):
            supplied_anchors = [supplied_anchors]
        elif not isinstance(supplied_anchors, list):
            supplied_anchors = []
        for value in [data.get("memory_key"), *supplied_anchors]:
            anchor = scalar_text(value)
            if anchor and anchor not in anchors:
                anchors.append(anchor)
        session = next((scalar_text(container.get(key)) for key in spec["session_fields"]
                        for container in (metadata, data) if scalar_text(container.get(key))), None)
        score = finite_number(data.get("relativity", data.get("retrieval_score")))
        confidence = finite_number(data.get("confidence"))
        mask = CapabilityMask(True, bool(event), bool(ingest), bool(anchors),
                              bool(session), score is not None, confidence is not None)
        records.append(EvidenceRecord(
            id=f"m{index + 1}", text=text, event_time=event, ingest_time=ingest,
            time_source=source, time_is_proxy=proxy, time_uncertainty=interval,
            entity_anchors=anchors, source_session=session, raw_index=index,
            retrieval_score=score, confidence=confidence,
            memory_type=scalar_text(data.get("memory_type")) or None,
            tags=[scalar_text(v) for v in data.get("tags", []) if scalar_text(v)]
                 if isinstance(data.get("tags"), list) else [], mask=mask,
        ))
    LOG.info("Stage0 rejected=%s stats=%s", rejected, capability_summary(records))
    return records


def capability_summary(records: list[EvidenceRecord]) -> dict[str, Any]:
    n = len(records)
    return {
        "n_records": n,
        "time_source": dict(Counter(r.time_source for r in records)),
        "time_proxy_count": sum(r.time_is_proxy for r in records),
        "time_proxy_rate": sum(r.time_is_proxy for r in records) / max(1, n),
        "capability_mask": {key: any(asdict(r.mask)[key] for r in records)
                            for key in CapabilityMask.__dataclass_fields__},
        "capability_rates": {key: sum(asdict(r.mask)[key] for r in records) / max(1, n)
                             for key in CapabilityMask.__dataclass_fields__},
    }
