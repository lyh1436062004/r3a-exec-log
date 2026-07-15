from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from openai import OpenAI

from e1_memos_oracle_common import (
    GEN_MAX_TOKENS,
    OUT_DIR as E1_OUT_DIR,
    PROMPT_MEMOS,
    append_jsonl,
    load_env,
    load_samples,
    read_jsonl,
    sha256_text,
    write_json,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "e1_memos_generation_failure_oracle_v1"
GEN_MODEL = "deepseek-v4-flash"
GEN_THINKING = "disabled"
JUDGE_MODEL = os.getenv("GF_JUDGE_MODEL", "LongCat-2.0")
JUDGE_BASE_URL = os.getenv(
    "GF_JUDGE_BASE_URL",
    "https://api.longcat.chat/openai/v1",
)
JUDGE_THINKING = os.getenv("GF_JUDGE_THINKING", "disabled")
TEMPERATURE = 0
GEN_REPLICATES = 3
GEN_WORKERS = 12
JUDGE_WORKERS = 8
TIMEOUT = 300
RETRIES = 3
EXPECTED_CASES = 381
EXPECTED_EVIDENCE = 793
EXPECTED_DATASETS = {"medium": 190, "long": 191}
JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("all", "generation", "judge"), default="all")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--generation-workers", type=int, default=GEN_WORKERS)
    parser.add_argument("--judge-workers", type=int, default=JUDGE_WORKERS)
    return parser.parse_args()


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def latest_ok_by(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, Any]]:
    out: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in read_jsonl(path):
        if not row.get("ok"):
            continue
        key = tuple(str(row.get(field)) for field in key_fields)
        out[key] = row
    return out


def parse_gold_evidence(raw_items: list[Any]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for index, item in enumerate(raw_items, 1):
        value = ast.literal_eval(item) if isinstance(item, str) else item
        if not isinstance(value, dict):
            raise ValueError(f"gold evidence {index} is not an object")
        content = value.get("memory_content")
        memory_type = value.get("memory_type")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"gold evidence {index} has no memory_content")
        if not isinstance(memory_type, str) or not memory_type.strip():
            raise ValueError(f"gold evidence {index} has no memory_type")
        parsed.append(
            {
                "evidence_index": str(index),
                "memory_type": memory_type,
                "memory_content": content,
                "raw": str(item),
            }
        )
    return parsed


def build_gold_context(evidence: list[dict[str, str]]) -> str:
    lines = [
        "# Authoritative benchmark gold evidence",
        "The following evidence is authoritative for answering the current question. Use it directly and do not rely on conflicting information.",
    ]
    for item in evidence:
        lines.extend(
            [
                "",
                f"Evidence {item['evidence_index']}",
                f"Memory type: {item['memory_type']}",
                f"Content: {item['memory_content']}",
            ]
        )
    return "\n".join(lines)


def build_candidates() -> list[dict[str, Any]]:
    samples = {str(row["case_id"]): row for row in load_samples()}
    ua3 = latest_ok_by(E1_OUT_DIR / "verdicts" / "UA3.jsonl", ("case_id",))
    candidates: list[dict[str, Any]] = []
    evidence_total = 0
    for case_id, sample in samples.items():
        verdict = ua3.get((case_id,))
        if sample.get("retrieval_stratum") != "strict_supported":
            continue
        if sample.get("visible_stratum") != "visible_supported":
            continue
        if verdict is None or verdict.get("judge_label") == "correct":
            continue
        evidence = parse_gold_evidence(list(sample.get("gold_evidence") or []))
        evidence_total += len(evidence)
        context = build_gold_context(evidence)
        prompt = PROMPT_MEMOS.format(context=context, question=sample["question"])
        candidates.append(
            {
                "case_id": case_id,
                "run_id": sample.get("run_id"),
                "dataset": sample.get("dataset"),
                "qa_key": sample.get("qa_key"),
                "uuid": sample.get("uuid"),
                "question_type": sample.get("question_type"),
                "question": sample.get("question"),
                "gold_answer": sample.get("gold_answer"),
                "gold_evidence": sample.get("gold_evidence"),
                "parsed_gold_evidence": evidence,
                "gold_context": context,
                "gold_context_hash": sha256_text(context),
                "generation_prompt": prompt,
                "generation_prompt_hash": sha256_text(prompt),
                "source_ua3_answer": verdict.get("model_answer"),
                "source_ua3_label": verdict.get("judge_label"),
                "source_ua3_rationale": verdict.get("judge_rationale"),
                "generation_prompt_fields": ["gold_context", "question"],
            }
        )
    candidates.sort(key=lambda row: str(row["case_id"]))
    dataset_counts: dict[str, int] = {}
    for row in candidates:
        dataset = str(row.get("dataset"))
        dataset_counts[dataset] = dataset_counts.get(dataset, 0) + 1
    if len(candidates) != EXPECTED_CASES:
        raise RuntimeError(f"candidate invariant failed: expected {EXPECTED_CASES}, got {len(candidates)}")
    if evidence_total != EXPECTED_EVIDENCE:
        raise RuntimeError(f"evidence invariant failed: expected {EXPECTED_EVIDENCE}, got {evidence_total}")
    if dataset_counts != EXPECTED_DATASETS:
        raise RuntimeError(f"dataset invariant failed: expected {EXPECTED_DATASETS}, got {dataset_counts}")
    return candidates


def model_matches(requested: str, actual: str | None) -> bool:
    if not actual:
        return False
    req = requested.strip().lower()
    got = actual.strip().lower()
    return got == req or got.startswith(req + "-") or got.endswith("/" + req)


def retry_call(label: str, fn: Callable[[], Any]) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            status_code = getattr(exc, "status_code", None)
            if status_code is not None and status_code != 429 and status_code < 500:
                raise
            if attempt < RETRIES:
                time.sleep(min(2**attempt, 12))
    raise RuntimeError(f"{label} failed after {RETRIES} attempts: {last_error}")


def make_clients() -> tuple[OpenAI, OpenAI]:
    load_env()
    deepseek_key = os.getenv("OPENAI_API_KEY")
    judge_key = os.getenv("GF_JUDGE_API_KEY")
    if not deepseek_key:
        raise RuntimeError("DeepSeek OPENAI_API_KEY is not configured")
    if not judge_key:
        raise RuntimeError("GF_JUDGE_API_KEY is not set")
    return (
        OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com"),
        OpenAI(api_key=judge_key, base_url=JUDGE_BASE_URL),
    )


def parse_json_response(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        match = JSON_RE.search(content)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("judge response is not a JSON object")
    return value


JUDGE_TOKEN_PARAM = "max_tokens"


def judge_request(client: OpenAI, prompt: str, max_tokens: int) -> Any:
    global JUDGE_TOKEN_PARAM

    def request(param: str) -> Any:
        kwargs: dict[str, Any] = {
            "model": JUDGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": TEMPERATURE,
            "response_format": {"type": "json_object"},
            "extra_body": {"thinking": {"type": JUDGE_THINKING}},
            "timeout": TIMEOUT,
            param: max_tokens,
        }
        return client.chat.completions.create(**kwargs)

    try:
        return request(JUDGE_TOKEN_PARAM)
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        if JUDGE_TOKEN_PARAM == "max_completion_tokens" and (
            "max_completion_tokens" in message or "unknown parameter" in message or "unsupported" in message
        ):
            JUDGE_TOKEN_PARAM = "max_tokens"
            return request(JUDGE_TOKEN_PARAM)
        raise


def smoke_test(deepseek: OpenAI, judge: OpenAI) -> dict[str, Any]:
    started = time.time()
    ds = retry_call(
        "deepseek smoke",
        lambda: deepseek.chat.completions.create(
            model=GEN_MODEL,
            messages=[{"role": "user", "content": "Reply exactly OK."}],
            temperature=TEMPERATURE,
            max_tokens=16,
            extra_body={"thinking": {"type": GEN_THINKING}},
            timeout=TIMEOUT,
        ),
    )
    ds_model = getattr(ds, "model", None)
    if not model_matches(GEN_MODEL, ds_model):
        raise RuntimeError(f"DeepSeek model mismatch: requested={GEN_MODEL}, response={ds_model}")
    if getattr(ds.choices[0].message, "reasoning_content", None):
        raise RuntimeError("DeepSeek smoke returned reasoning_content despite thinking=disabled")

    judge_prompt = 'Return exactly this JSON object: {"status":"ok"}'
    try:
        js = retry_call("judge smoke", lambda: judge_request(judge, judge_prompt, 32))
    except Exception as exc:  # noqa: BLE001
        write_json(
            OUT_DIR / "smoke_test_failure.json",
            {
                "ok": False,
                "deepseek_requested_model": GEN_MODEL,
                "deepseek_response_model": ds_model,
                "judge_requested_model": JUDGE_MODEL,
                "judge_base_url": JUDGE_BASE_URL,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            },
        )
        raise
    judge_model = getattr(js, "model", None)
    if not model_matches(JUDGE_MODEL, judge_model):
        raise RuntimeError(f"judge model mismatch: requested={JUDGE_MODEL}, response={judge_model}")
    if getattr(js.choices[0].message, "reasoning_content", None):
        raise RuntimeError("judge smoke returned reasoning_content despite thinking=disabled")
    parsed = parse_json_response(js.choices[0].message.content or "")
    if str(parsed.get("status", "")).lower() != "ok":
        raise RuntimeError(f"judge JSON smoke failed: {parsed}")
    result = {
        "ok": True,
        "deepseek_requested_model": GEN_MODEL,
        "deepseek_response_model": ds_model,
        "deepseek_thinking": GEN_THINKING,
        "judge_requested_model": JUDGE_MODEL,
        "judge_response_model": judge_model,
        "judge_base_url": JUDGE_BASE_URL,
        "judge_thinking": JUDGE_THINKING,
        "judge_token_parameter": JUDGE_TOKEN_PARAM,
        "latency_ms": round((time.time() - started) * 1000, 2),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_json(OUT_DIR / "smoke_test.json", result)
    failure_path = OUT_DIR / "smoke_test_failure.json"
    if failure_path.exists():
        failure_path.unlink()
    return result


def generation_cache_key(case: dict[str, Any], replicate: int) -> str:
    return sha256_text(
        "|".join(
            [
                str(case["case_id"]),
                str(replicate),
                GEN_MODEL,
                GEN_THINKING,
                str(TEMPERATURE),
                str(GEN_MAX_TOKENS),
                str(case["generation_prompt_hash"]),
            ]
        )
    )


def run_generation(
    client: OpenAI,
    candidates: list[dict[str, Any]],
    workers: int,
) -> None:
    path = OUT_DIR / "generations.jsonl"
    existing = latest_ok_by(path, ("case_id", "replicate"))
    tasks = [
        (case, replicate)
        for case in candidates
        for replicate in range(1, GEN_REPLICATES + 1)
        if (str(case["case_id"]), str(replicate)) not in existing
    ]
    print(f"pending generation tasks: {len(tasks)}")
    lock = Lock()

    def worker(case: dict[str, Any], replicate: int) -> dict[str, Any]:
        started = time.time()
        cache_key = generation_cache_key(case, replicate)
        try:
            response = retry_call(
                "generation",
                lambda: client.chat.completions.create(
                    model=GEN_MODEL,
                    messages=[{"role": "user", "content": case["generation_prompt"]}],
                    temperature=TEMPERATURE,
                    max_tokens=GEN_MAX_TOKENS,
                    extra_body={"thinking": {"type": GEN_THINKING}},
                    timeout=TIMEOUT,
                ),
            )
            response_model = getattr(response, "model", None)
            if not model_matches(GEN_MODEL, response_model):
                raise RuntimeError(f"generation model mismatch: {response_model}")
            message = response.choices[0].message
            if getattr(message, "reasoning_content", None):
                raise RuntimeError("generation returned reasoning_content despite thinking=disabled")
            return {
                "ok": True,
                "cache_key": cache_key,
                "case_id": case["case_id"],
                "replicate": replicate,
                "dataset": case["dataset"],
                "question_type": case["question_type"],
                "question": case["question"],
                "gold_answer": case["gold_answer"],
                "gold_evidence": case["gold_evidence"],
                "gold_context": case["gold_context"],
                "gold_context_hash": case["gold_context_hash"],
                "prompt_hash": case["generation_prompt_hash"],
                "model_answer": message.content or "",
                "requested_model": GEN_MODEL,
                "response_model": response_model,
                "thinking": GEN_THINKING,
                "temperature": TEMPERATURE,
                "max_tokens": GEN_MAX_TOKENS,
                "finish_reason": getattr(response.choices[0], "finish_reason", None),
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else {},
                "latency_ms": round((time.time() - started) * 1000, 2),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "cache_key": cache_key,
                "case_id": case["case_id"],
                "replicate": replicate,
                "error": repr(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker, case, replicate) for case, replicate in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            append_jsonl(path, future.result(), lock)
            if index % 50 == 0 or index == len(futures):
                print(f"generated {index}/{len(futures)}")


def sufficiency_prompt(case: dict[str, Any]) -> str:
    return f"""You are an independent evidence-sufficiency judge for a memory QA benchmark.

Question:
{case['question']}

Benchmark gold answer:
{case['gold_answer']}

Benchmark gold evidence:
{case['gold_context']}

Judge whether the evidence, taken together and allowing ordinary reasoning, contains enough information to derive every material component of the gold answer.

Use exactly one verdict:
- sufficient: the complete gold answer is supported or directly derivable.
- partial: some but not all material components are supported.
- insufficient: the evidence does not support the requested answer.

Return JSON only with keys:
{{"verdict":"sufficient|partial|insufficient","missing_information":"...","rationale":"..."}}
"""


def answer_judge_prompt(generation: dict[str, Any]) -> str:
    return f"""You are an independent judge for a memory QA answer.

Question:
{generation['question']}

Benchmark gold answer:
{generation['gold_answer']}

Model answer:
{generation['model_answer']}

Use exactly one label:
- correct: semantically gives the complete gold answer; wording may differ.
- omission: says unknown, gives no answer, or gives only an incomplete subset without adding a concrete false claim.
- hallucination: gives a concrete answer that contradicts the gold answer or includes unsupported/incorrect material.

Return JSON only with keys:
{{"label":"correct|hallucination|omission","rationale":"..."}}
"""


def run_sufficiency_judging(client: OpenAI, candidates: list[dict[str, Any]], workers: int) -> None:
    path = OUT_DIR / "evidence_sufficiency.jsonl"
    existing = latest_ok_by(path, ("case_id",))
    tasks = [case for case in candidates if (str(case["case_id"]),) not in existing]
    print(f"pending sufficiency tasks: {len(tasks)}")
    lock = Lock()

    def worker(case: dict[str, Any]) -> dict[str, Any]:
        prompt = sufficiency_prompt(case)
        started = time.time()
        try:
            response = retry_call("sufficiency judge", lambda: judge_request(client, prompt, 512))
            response_model = getattr(response, "model", None)
            if not model_matches(JUDGE_MODEL, response_model):
                raise RuntimeError(f"sufficiency judge model mismatch: {response_model}")
            parsed = parse_json_response(response.choices[0].message.content or "")
            verdict = str(parsed.get("verdict", "")).strip().lower()
            if verdict not in {"sufficient", "partial", "insufficient"}:
                raise ValueError(f"invalid sufficiency verdict: {verdict}")
            return {
                "ok": True,
                "cache_key": sha256_text(f"{case['case_id']}|{JUDGE_MODEL}|{sha256_text(prompt)}"),
                "case_id": case["case_id"],
                "verdict": verdict,
                "missing_information": str(parsed.get("missing_information", "")),
                "rationale": str(parsed.get("rationale", "")),
                "prompt_hash": sha256_text(prompt),
                "requested_model": JUDGE_MODEL,
                "response_model": response_model,
                "thinking": JUDGE_THINKING,
                "token_parameter": JUDGE_TOKEN_PARAM,
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else {},
                "latency_ms": round((time.time() - started) * 1000, 2),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "case_id": case["case_id"],
                "error": repr(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker, case) for case in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            append_jsonl(path, future.result(), lock)
            if index % 50 == 0 or index == len(futures):
                print(f"sufficiency judged {index}/{len(futures)}")


def run_answer_judging(client: OpenAI, workers: int) -> None:
    generations = list(latest_ok_by(OUT_DIR / "generations.jsonl", ("case_id", "replicate")).values())
    path = OUT_DIR / "answer_judgments.jsonl"
    existing = latest_ok_by(path, ("case_id", "replicate"))
    tasks = [
        row
        for row in generations
        if (str(row["case_id"]), str(row["replicate"])) not in existing
    ]
    print(f"pending answer judge tasks: {len(tasks)}")
    lock = Lock()

    def worker(generation: dict[str, Any]) -> dict[str, Any]:
        prompt = answer_judge_prompt(generation)
        started = time.time()
        try:
            response = retry_call("answer judge", lambda: judge_request(client, prompt, 256))
            response_model = getattr(response, "model", None)
            if not model_matches(JUDGE_MODEL, response_model):
                raise RuntimeError(f"answer judge model mismatch: {response_model}")
            parsed = parse_json_response(response.choices[0].message.content or "")
            label = str(parsed.get("label", "")).strip().lower()
            if label not in {"correct", "hallucination", "omission"}:
                raise ValueError(f"invalid answer label: {label}")
            return {
                "ok": True,
                "cache_key": sha256_text(
                    f"{generation['cache_key']}|{JUDGE_MODEL}|{sha256_text(prompt)}"
                ),
                "generation_cache_key": generation["cache_key"],
                "case_id": generation["case_id"],
                "replicate": generation["replicate"],
                "label": label,
                "rationale": str(parsed.get("rationale", "")),
                "prompt_hash": sha256_text(prompt),
                "requested_model": JUDGE_MODEL,
                "response_model": response_model,
                "thinking": JUDGE_THINKING,
                "token_parameter": JUDGE_TOKEN_PARAM,
                "usage": response.usage.model_dump() if getattr(response, "usage", None) else {},
                "latency_ms": round((time.time() - started) * 1000, 2),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "case_id": generation["case_id"],
                "replicate": generation["replicate"],
                "error": repr(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker, row) for row in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            append_jsonl(path, future.result(), lock)
            if index % 50 == 0 or index == len(futures):
                print(f"answer judged {index}/{len(futures)}")


def write_failures() -> dict[str, Any]:
    files = {
        "generations": OUT_DIR / "generations.jsonl",
        "evidence_sufficiency": OUT_DIR / "evidence_sufficiency.jsonl",
        "answer_judgments": OUT_DIR / "answer_judgments.jsonl",
    }
    failures: list[dict[str, Any]] = []
    counts: dict[str, dict[str, int]] = {}
    for phase, path in files.items():
        rows = read_jsonl(path)
        bad = [row for row in rows if not row.get("ok")]
        counts[phase] = {"rows": len(rows), "failed_rows": len(bad)}
        failures.extend({"phase": phase, **row} for row in bad)
    dump_jsonl(OUT_DIR / "failures.jsonl", failures)
    write_json(OUT_DIR / "run_counts.json", counts)
    return {"counts": counts, "failures": len(failures)}


def write_config(candidates: list[dict[str, Any]], smoke: dict[str, Any]) -> None:
    config = {
        "experiment_id": "e1_memos_generation_failure_oracle_v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "candidate_definition": {
            "retrieval_stratum": "strict_supported",
            "visible_stratum": "visible_supported",
            "UA3_label": "non-correct",
        },
        "candidate_count": len(candidates),
        "gold_evidence_count": sum(len(row["parsed_gold_evidence"]) for row in candidates),
        "generation": {
            "model": GEN_MODEL,
            "thinking": GEN_THINKING,
            "temperature": TEMPERATURE,
            "max_tokens": GEN_MAX_TOKENS,
            "replicates": GEN_REPLICATES,
            "prompt": "PROMPT_MEMOS with authoritative benchmark gold evidence as the only context",
        },
        "independent_judge": {
            "model": JUDGE_MODEL,
            "base_url": JUDGE_BASE_URL,
            "temperature": TEMPERATURE,
            "thinking": JUDGE_THINKING,
            "key_source": "process environment GF_JUDGE_API_KEY",
            "protocol_amendment": (
                "User authorized replacing the quota-blocked qwen3.7-max judge with LongCat-2.0 "
                "on 2026-07-15 and rerunning all 381 sufficiency plus 1,143 answer judgments; "
                "generator and all other experiment conditions remain unchanged."
            ),
        },
        "smoke_test": smoke,
        "secrets_persisted": False,
    }
    write_json(OUT_DIR / "run_config.json", config)


def main() -> None:
    args = parse_args()
    if not args.yes and not args.smoke_only:
        raise RuntimeError("Pass --yes to acknowledge 2,667 planned API calls")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_candidates()
    dump_jsonl(OUT_DIR / "candidate_pool.jsonl", candidates)
    deepseek, judge = make_clients()
    smoke = smoke_test(deepseek, judge)
    write_config(candidates, smoke)
    print(json.dumps(smoke, ensure_ascii=False))
    if args.smoke_only:
        return

    if args.phase in {"all", "generation"}:
        run_generation(deepseek, candidates, args.generation_workers)
    if args.phase in {"all", "judge"}:
        generations = latest_ok_by(OUT_DIR / "generations.jsonl", ("case_id", "replicate"))
        if len(generations) != EXPECTED_CASES * GEN_REPLICATES:
            raise RuntimeError(
                f"judge phase requires {EXPECTED_CASES * GEN_REPLICATES} successful generations, got {len(generations)}"
            )
        run_sufficiency_judging(judge, candidates, args.judge_workers)
        run_answer_judging(judge, args.judge_workers)
    summary = write_failures()
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
