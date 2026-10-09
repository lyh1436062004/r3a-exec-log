"""Stage 1: label-free LLM posterior estimation with validated disk caching."""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote

from a2_schema import EvidenceRecord, EstimateResult, MemoryEstimate, RELATIONS, safe_estimate
from e1_memos_oracle_common import make_client, retry_call, sha256_text

MAX_WORKERS = 12
DEFAULT_MODEL = "deepseek-chat"
MAX_TOKENS = 8192
TIMEOUT = 300
CACHE_VERSION = 1
LOG = logging.getLogger(__name__)

# Literal task-book section 4.4; braces are escaped only for str.format.
PROMPT_TEMPLATE = """你是记忆准入系统的证据估计器。你看不到标准答案,只能依据下面的问题与记忆作答。

问题:
{question}

记忆列表(每条含位置 id、时间[可能缺失]、主题锚[可能缺失]、正文):
{memory_block}

请对每条记忆判断它与问题的关系,并给出概率分布;同时判断整体情况。

每条记忆必须输出:
- relation: 六个类别的概率,键必须恰好是
  SUPPORT / REFUTE / SUPERSEDED / CURRENT / MISBIND / INSUFFICIENT,
  六个值均为 0.0-1.0 且总和为 1.0
- condition_present: 该记忆是否只是一条"仅在某条件成立时才适用"的规则
  (注意:"when she arrived"这类事件时间修饰不算条件;
   "even if / what if"属于问题句式,不属于记忆,不算条件)
- condition_text: 条件内容原文,没有则空串
- condition_satisfied: "TRUE" / "FALSE" / "UNKNOWN"
  —— 问题所述情形能否确认满足该条件;无法判断填 UNKNOWN
- entity_match: "MATCH" / "MISMATCH" / "UNCLEAR"

整体必须输出:
- premise_conflict: true/false,问题是否包含与某条记忆直接矛盾的前提
- sufficiency: 0.0-1.0,当前记忆集合是否足以回答问题
- risk: 0.0-1.0,当前集合是否需要准入干预(无需干预填低值)

只输出 JSON,不要输出任何其他文字。格式:
{{"premise_conflict":false,"sufficiency":0.0,"risk":0.0,
 "memories":[{{"id":"m1","relation":{{"SUPPORT":0.0,"REFUTE":0.0,"SUPERSEDED":0.0,
 "CURRENT":0.0,"MISBIND":0.0,"INSUFFICIENT":1.0}},"condition_present":false,
 "condition_text":"","condition_satisfied":"UNKNOWN","entity_match":"UNCLEAR"}}]}}"""
PROMPT_HASH = sha256_text(PROMPT_TEMPLATE)

_CONFIG_LOCK = Lock()
_DEFAULT_CLIENT: Any = None
_MODEL = DEFAULT_MODEL
_CACHE_LOCKS_LOCK = Lock()
_CACHE_LOCKS: dict[str, Any] = {}


def configure(client: Any = None, model: str = DEFAULT_MODEL) -> None:
    """Configure the two-input public estimator before starting worker threads."""
    global _DEFAULT_CLIENT, _MODEL
    with _CONFIG_LOCK:
        _DEFAULT_CLIENT = client
        _MODEL = model


def _configured_client() -> Any:
    global _DEFAULT_CLIENT
    with _CONFIG_LOCK:
        if _DEFAULT_CLIENT is None:
            _DEFAULT_CLIENT = make_client()
        return _DEFAULT_CLIENT


def _one_line(value: str) -> str:
    return " ".join(value.splitlines())


def memory_block(records: list[EvidenceRecord]) -> str:
    """The section 4.4 row format, containing only supplied record facts."""
    return "\n".join(
        f"[{record.id} | {record.event_time or '?'} | "
        f"{','.join(_one_line(anchor) for anchor in record.entity_anchors) or '-'}] "
        f"{_one_line(record.text)}"
        for record in records
    )


def build_estimator_prompt(question: str, records: list[EvidenceRecord]) -> str:
    return PROMPT_TEMPLATE.format(question=question, memory_block=memory_block(records))


def estimate_cache_key(question: str, records: list[EvidenceRecord],
                       model: str = DEFAULT_MODEL) -> str:
    """Hash prompt-visible facts plus record metadata; outer IDs are not features."""
    identity = {
        "cache_version": CACHE_VERSION,
        "question_hash": sha256_text(question),
        "record_text_hashes": [sha256_text(record.text) for record in records],
        "records": [asdict(record) for record in records],
        "model": model,
        "prompt_hash": PROMPT_HASH,
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }
    return sha256_text(json.dumps(identity, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False))


def _default_memory(identifier: str) -> MemoryEstimate:
    return MemoryEstimate(identifier, {name: float(name == "INSUFFICIENT")
                                      for name in RELATIONS})


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("non-numeric probability")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite probability")
    return number


def _unit_score(value: Any, name: str, warnings: list[str]) -> float:
    try:
        number = _number(value)
    except (ValueError, OverflowError):
        warnings.append(f"validation_warning:{name}:invalid_score")
        return 0.0
    clipped = min(1.0, max(0.0, number))
    if clipped != number:
        warnings.append(f"validation_warning:{name}:clipped")
    return clipped


def _posterior(value: Any, identifier: str, warnings: list[str]) -> dict[str, float] | None:
    try:
        if not isinstance(value, dict) or set(value) != set(RELATIONS):
            raise ValueError("relation keys do not match")
        numbers = {name: _number(value[name]) for name in RELATIONS}
        total = math.fsum(numbers.values())
        if total <= 0 or any(number < 0 for number in numbers.values()):
            raise ValueError("posterior cannot be normalized")
        if (any(number > 1 for number in numbers.values())
                or not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-6)):
            warnings.append(f"validation_warning:{identifier}:posterior_renormalized")
        normalized = {name: number / total for name, number in numbers.items()}
        if (any(not math.isfinite(number) or not 0 <= number <= 1
                for number in normalized.values())
                or not math.isclose(math.fsum(normalized.values()), 1.0,
                                    rel_tol=0, abs_tol=1e-6)):
            raise ValueError("normalized posterior is invalid")
        return normalized
    except (ValueError, OverflowError, TypeError):
        warnings.append(f"validation_warning:{identifier}:invalid_posterior")
        return None


def validate_estimate(payload: Any, records: list[EvidenceRecord]) -> EstimateResult:
    """Repair per-record errors, while structural JSON failures remain retryable."""
    if not isinstance(payload, dict) or not isinstance(payload.get("memories"), list):
        raise ValueError("estimator root must be an object with a memories array")
    warnings: list[str] = []
    expected = {record.id for record in records}
    returned: dict[str, Any] = {}
    duplicates: set[str] = set()
    for item in payload["memories"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            warnings.append("validation_warning:unidentified_memory:discarded")
            continue
        identifier = item["id"]
        if identifier not in expected:
            warnings.append(f"validation_warning:{identifier}:unexpected_id_discarded")
            continue
        if identifier in returned:
            duplicates.add(identifier)
        returned[identifier] = item

    memories: dict[str, MemoryEstimate] = {}
    for record in records:
        identifier = record.id
        item = returned.get(identifier)
        if item is None or identifier in duplicates:
            reason = "missing_id" if item is None else "duplicate_id"
            warnings.append(f"validation_warning:{identifier}:{reason}")
            memories[identifier] = _default_memory(identifier)
            continue
        posterior = _posterior(item.get("relation"), identifier, warnings)
        if posterior is None:
            memories[identifier] = _default_memory(identifier)
            continue
        present = item.get("condition_present", False)
        if not isinstance(present, bool):
            present = False
            warnings.append(f"validation_warning:{identifier}:invalid_condition_present")
        condition_text = item.get("condition_text", "")
        if not isinstance(condition_text, str):
            condition_text = ""
            warnings.append(f"validation_warning:{identifier}:invalid_condition_text")
        satisfied = item.get("condition_satisfied", "UNKNOWN")
        if satisfied not in ("TRUE", "FALSE", "UNKNOWN"):
            satisfied = "UNKNOWN"
            warnings.append(f"validation_warning:{identifier}:invalid_condition_satisfied")
        entity_match = item.get("entity_match", "UNCLEAR")
        if entity_match not in ("MATCH", "MISMATCH", "UNCLEAR"):
            entity_match = "UNCLEAR"
            warnings.append(f"validation_warning:{identifier}:invalid_entity_match")
        memories[identifier] = MemoryEstimate(
            identifier, posterior, present, condition_text if present else "",
            satisfied, entity_match,
        )
    conflict = payload.get("premise_conflict", False)
    if not isinstance(conflict, bool):
        conflict = False
        warnings.append("validation_warning:premise_conflict:invalid_boolean")
    return EstimateResult(
        premise_conflict=conflict,
        sufficiency=_unit_score(payload.get("sufficiency"), "sufficiency", warnings),
        risk=_unit_score(payload.get("risk"), "risk", warnings),
        memories=memories, failed=False, validation_warnings=warnings,
    )


def _parse_response(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return {name: getattr(usage, name) for name in
            ("prompt_tokens", "completion_tokens", "total_tokens")
            if getattr(usage, name, None) is not None}


def _estimate(question: str, records: list[EvidenceRecord], model: str,
              client: Any = None) -> EstimateResult:
    started = time.perf_counter()
    usage_total: dict[str, Any] = {}
    attempts = 0
    errors: list[str] = []
    if not records:
        result = safe_estimate(records, failed=False)
        result.validation_warnings.append("validation_warning:empty_collection")
        result.telemetry = {"model": model, "prompt_hash": PROMPT_HASH,
                            "attempts": 0, "usage": {}, "latency_ms": 0.0,
                            "cache_hit": False}
        return result
    try:
        if len({record.id for record in records}) != len(records):
            raise ValueError("input record identifiers are not unique")
        prompt = build_estimator_prompt(question, records)
        selected_client = client if client is not None else _configured_client()
        # Avoid multiplying the documented three attempts by SDK-level retries.
        if callable(getattr(selected_client, "with_options", None)):
            selected_client = selected_client.with_options(max_retries=0)

        def call_and_validate() -> EstimateResult:
            nonlocal attempts
            attempts += 1
            try:
                response = selected_client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, temperature=0,
                    max_tokens=MAX_TOKENS, timeout=TIMEOUT,
                )
                for name, value in _usage(response).items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        usage_total[name] = usage_total.get(name, 0) + value
                return validate_estimate(
                    _parse_response(response.choices[0].message.content or ""), records,
                )
            except Exception as exc:
                errors.append(type(exc).__name__)
                raise

        # The existing policy waits 2 then 4 seconds for three attempts, matching
        # the required exponential backoff without changing any legacy helper.
        result = retry_call("a2-estimation", call_and_validate, retries=3, sleep_base=2.0)
    except Exception as exc:
        result = safe_estimate(records)
        result.validation_warnings.append(f"validation_warning:estimate_failed:{type(exc).__name__}")
        LOG.warning("A2 estimation safely fell back (%s)", type(exc).__name__)
    result.telemetry = {
        "model": model, "prompt_hash": PROMPT_HASH, "attempts": attempts,
        "usage": usage_total, "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "cache_hit": False, "attempt_errors": errors,
    }
    return result


def estimate(question: str, records: list[EvidenceRecord]) -> EstimateResult:
    """Estimate from exactly the current question and the frozen records."""
    return _estimate(question, records, _MODEL)


def _path_component(value: str) -> str:
    encoded = quote(str(value), safe="-_")
    if not encoded or encoded in (".", ".."):
        encoded = "_" + encoded.replace(".", "%2E")
    # Windows reserves these names even with a .json extension.
    if encoded.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        encoded = "_" + encoded
    if encoded.endswith("."):
        encoded = encoded[:-1] + "%2E"
    return encoded


def estimate_cache_path(case_id: str, pool: str, out_dir: str | Path) -> Path:
    return Path(out_dir) / "estimates" / _path_component(pool) / f"{_path_component(case_id)}.json"


def _load_cached(path: Path, input_hash: str,
                 records: list[EvidenceRecord]) -> EstimateResult | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("input_hash") != input_hash:
            return None
        result = EstimateResult.from_dict({name: payload[name] for name in (
            "premise_conflict", "sufficiency", "risk", "memories", "failed",
            "validation_warnings", "telemetry",
        )})
        if set(result.memories) != {record.id for record in records}:
            return None
        if (not isinstance(result.failed, bool) or not isinstance(result.premise_conflict, bool)
                or not 0 <= _number(result.risk) <= 1
                or not 0 <= _number(result.sufficiency) <= 1
                or (result.failed and result.risk != 0.0)):
            return None
        for identifier, memory in result.memories.items():
            probabilities = memory.relation_posterior
            if (memory.id != identifier or set(probabilities) != set(RELATIONS)
                    or any(not 0 <= _number(value) <= 1 for value in probabilities.values())
                    or not math.isclose(math.fsum(probabilities.values()), 1.0,
                                        rel_tol=0, abs_tol=1e-6)
                    or not isinstance(memory.condition_present, bool)
                    or not isinstance(memory.condition_text, str)
                    or memory.condition_satisfied not in ("TRUE", "FALSE", "UNKNOWN")
                    or memory.entity_match not in ("MATCH", "MISMATCH", "UNCLEAR")):
                return None
        result.telemetry["cache_hit"] = True
        return result
    except (OSError, ValueError, OverflowError, TypeError, KeyError, AttributeError):
        return None


def _estimate_cached_locked(question: str, records: list[EvidenceRecord], case_id: str,
                            pool: str, model: str, client: Any,
                            path: Path, input_hash: str) -> EstimateResult:
    cached = _load_cached(path, input_hash, records)
    if cached is not None:
        return cached
    result = _estimate(question, records, model, client)
    result.telemetry["input_hash"] = input_hash
    payload = {
        **result.to_dict(), "input_hash": input_hash, "cache_version": CACHE_VERSION,
        "question_hash": sha256_text(question),
        "record_text_hashes": [sha256_text(record.text) for record in records],
        "model": model, "prompt_hash": PROMPT_HASH, "case_id": case_id, "pool": pool,
        "usage": result.telemetry.get("usage", {}),
        "latency_ms": result.telemetry.get("latency_ms", 0.0),
    }
    temporary_path = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2,
                                             allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temporary_path, path)
    except (OSError, ValueError, TypeError) as exc:
        result.validation_warnings.append(f"validation_warning:cache_write:{type(exc).__name__}")
        LOG.warning("A2 cache write skipped (%s)", type(exc).__name__)
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            LOG.warning("A2 cache temporary-file cleanup skipped")
    return result


def estimate_cached(question: str, records: list[EvidenceRecord], case_id: str,
                    pool: str, out_dir: str | Path, model: str = DEFAULT_MODEL,
                    client: Any = None) -> EstimateResult:
    """Outer-runner disk cache; identifiers never enter the estimator prompt."""
    try:
        input_hash = estimate_cache_key(question, records, model)
        path = estimate_cache_path(case_id, pool, out_dir)
        lock_key = os.path.normcase(str(path.resolve()))
    except Exception as exc:
        result = safe_estimate(records)
        result.validation_warnings.append(f"validation_warning:cache_identity:{type(exc).__name__}")
        return result
    with _CACHE_LOCKS_LOCK:
        lock = _CACHE_LOCKS.setdefault(lock_key, Lock())
    # Different arms may request the same estimate concurrently: only the first
    # miss issues the LLM request, and the remaining workers read its atomic file.
    with lock:
        return _estimate_cached_locked(question, records, case_id, pool, model,
                                       client, path, input_hash)
