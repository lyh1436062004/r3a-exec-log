"""Build the task-book's retrieval-defined pools; labels stay at this I/O boundary.

The archived E1 pool contains only wrong answers.  Correct answers therefore need
the SAME independent semantic support audit, never a fabricated strict label.
No retrieval is rerun, and no saved memory/context is rewritten by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

import audit_gold_evidence_semantic_retrieval as support_audit
from e1_memos_oracle_common import (
    LONG_QA, MEDIUM_QA, ROOT, SEMANTIC_DETAIL, SEED, append_jsonl,
    baseline_memory_text, make_client, read_jsonl, retry_call,
    serialize_baseline_context, sha256_text, write_json,
)

OUT_DIR = ROOT / "outputs" / "a2_mvp_v1"
OLD_DIR = ROOT / "outputs" / "e1_memos_full_oracle_v2"
SUPPORT_VERSION = "a2-pool-support-v1-full-input"
RUNS = {"memos_medium": ("medium", MEDIUM_QA), "memos_long": ("long", LONG_QA)}


def json_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def merge_run_config(section: str, payload: dict[str, Any], out_dir: Path = OUT_DIR) -> None:
    """Merge a named section without erasing preflight/other script settings."""
    path = out_dir / "run_config.json"
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    value.setdefault("seed", SEED)
    value[section] = payload
    write_json(path, value)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def serializer_view(sample: dict[str, Any]) -> dict[str, Any]:
    lines, visible = [], []
    for i, item in enumerate(sample.get("raw_memories") or [], 1):
        text = baseline_memory_text(item)
        if text:
            visible.append(f"m{i}")
            lines.append(text)
    stored = str(sample.get("context_str_full") or "")
    user = str(sample.get("user_name") or "")
    rebuilt = serialize_baseline_context(user, lines)
    note = ""
    ok = stored == rebuilt
    if not ok and stored.startswith(rebuilt + "\n"):
        note = stored[len(rebuilt) + 1:]
        ok = serialize_baseline_context(user, lines + [note]) == stored
    return {"serializer_ok": ok, "visible_memory_ids": visible,
            "pref_note": note if ok else "", "n_raw": len(sample.get("raw_memories") or []),
            "n_visible": len(visible), "context_sha256": sha256_text(stored)}


def load_source_samples() -> list[dict[str, Any]]:
    for path in (OLD_DIR / "samples_memos_full.jsonl", OLD_DIR / "visibility.jsonl",
                 MEDIUM_QA, LONG_QA, SEMANTIC_DETAIL):
        if not path.exists():
            raise FileNotFoundError(f"Required task-book source is missing: {path}")
    archived_visibility = read_jsonl(OLD_DIR / "visibility.jsonl")
    if not archived_visibility or any(not row.get("serializer_ok") for row in archived_visibility):
        raise RuntimeError("00_verify_serializer.py has not passed; generation is prohibited")
    rows: list[dict[str, Any]] = []
    for run, (dataset, path) in RUNS.items():
        with path.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                rows.append({
                    **raw, "case_id": f"{run}:{line_no}", "run_id": run,
                    "dataset": dataset, "system": "memos", "system_kind": "memos",
                    "source_file": str(path.relative_to(ROOT)), "line_no": line_no,
                    "gold_evidence": support_audit.evidence_texts(raw),
                    "baseline_answer": raw.get("baseline_response") or "",
                    "baseline_verdict": raw.get("baseline_label") or "",
                    **serializer_view(raw),
                })
    return rows


def audit_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """All fields required by the old normalizer, with full frozen memories."""
    retrieved = support_audit.raw_memory_texts(sample.get("raw_memories"))
    return {
        **sample, "qa_key": sample.get("qa_key") or "", "uuid": sample.get("uuid") or "",
        "question_type": sample.get("question_type") or "UNKNOWN",
        "evidence": sample["gold_evidence"], "retrieved": retrieved,
        "retrieved_count": len(retrieved),
        "token": support_audit.token_hit(sample["gold_evidence"], retrieved),
    }


def support_payload(sample: dict[str, Any]) -> dict[str, Any]:
    # Do not call build_case_payload(): that historical helper clips memories.
    # The original semantic definitions/prompt are reused with COMPLETE inputs.
    view = audit_sample(sample)
    return {
        "case_id": sample["case_id"], "question": sample.get("question") or "",
        "gold_answer": sample.get("gold_answer") or "",
        "gold_evidence": [{"evidence_id": f"e{i}", "text": value}
                          for i, value in enumerate(sample["gold_evidence"], 1)],
        "retrieved_memories": view["retrieved"],
    }


def support_cache_key(sample: dict[str, Any], model: str) -> str:
    prompt = support_audit.build_prompt([support_payload(sample)])
    return json_hash({"version": SUPPORT_VERSION, "model": model, "temperature": 0,
                      "prompt": prompt})


def load_support(samples: list[dict[str, Any]], model: str, out_dir: Path = OUT_DIR
                 ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    # Historical artifacts are explicitly identified as legacy, not silently
    # presented as newly input-hashed judgments.
    legacy = {str(r["case_id"]): r for r in read_jsonl(SEMANTIC_DETAIL)
              if r.get("run_id") in RUNS}
    old_samples = {str(r["case_id"]): r for r in read_jsonl(OLD_DIR / "samples_memos_full.jsonl")}
    support: dict[str, dict[str, Any]] = {}
    pending = []
    for row in samples:
        if not row["gold_evidence"] or not row["serializer_ok"]:
            continue
        cid = row["case_id"]
        key = support_cache_key(row, model)
        path = out_dir / "support_audit" / "cache" / f"{key}.json"
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cached.get("cache_key") == key and not cached.get("error"):
                support[cid] = {**cached["result"], "support_source": "input_hashed_audit",
                                "support_cache_key": key}
                continue
        previous = old_samples.get(cid)
        if cid in legacy and previous is not None:
            stable = (previous.get("raw_memories") == row.get("raw_memories")
                      and previous.get("question") == row.get("question")
                      and previous.get("gold_answer") == row.get("gold_answer")
                      and previous.get("context_str_full") == row.get("context_str_full"))
            legacy_evidence = [r.get("gold_evidence") for r in legacy[cid].get("evidence_results", [])]
            if stable and legacy_evidence == row["gold_evidence"]:
                support[cid] = {**legacy[cid], "support_source": "frozen_legacy_audit",
                                "support_cache_key": None,
                                "support_input_sha256": json_hash(support_payload(row))}
                continue
        pending.append(row)
    return support, pending


def supported_ids(result: dict[str, Any], count: int) -> tuple[list[str], list[str]]:
    valid = {f"m{i}" for i in range(1, count + 1)}
    strict, partial = [], []
    for item in result.get("evidence_results") or []:
        target = strict if item.get("status") == "supported" else (
            partial if item.get("status") == "partially_supported" else None)
        if target is None:
            continue
        for value in item.get("best_memory_ids") or []:
            if value in valid and value not in target:
                target.append(value)
    return strict, [value for value in partial if value not in strict]


def enrich_sources(samples: list[dict[str, Any]], support: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        result = support.get(sample["case_id"])
        gold, partial = supported_ids(result or {}, len(sample.get("raw_memories") or []))
        stratum = "strict_supported" if gold else ("partial_supported" if partial else (
            "no_gold_retrieved" if result is not None else "support_not_audited"))
        reason = ("empty_gold_evidence" if not sample["gold_evidence"] else
                  "serializer_failed" if not sample["serializer_ok"] else
                  "missing_support_audit" if result is None else
                  "no_gold_retrieved" if stratum == "no_gold_retrieved" else "")
        visible = set(sample["visible_memory_ids"])
        gold_visible = [mid for mid in gold if mid in visible]
        visible_stratum = ("visible_supported" if gold_visible else "serialization_loss") if gold else stratum
        rows.append({**sample, "retrieval_stratum": stratum,
                     "gold_memory_ids": gold, "partial_memory_ids": partial,
                     "gold_visible_ids": gold_visible,
                     "partial_visible_ids": [mid for mid in partial if mid in visible],
                     "visible_stratum": visible_stratum,
                     "support_evidence_results": (result or {}).get("evidence_results") or [],
                     "support_source": (result or {}).get("support_source") or "not_audited",
                     "support_cache_key": (result or {}).get("support_cache_key"),
                     "source_input_sha256": json_hash(support_payload(sample)),
                     "pool_eligible": not reason, "pool_exclusion_reason": reason})
    return rows


def prepare_support(samples: list[dict[str, Any]], support: dict[str, dict[str, Any]],
                    pending: list[dict[str, Any]], model: str, out_dir: Path = OUT_DIR) -> dict[str, Any]:
    snapshots = enrich_sources(samples, support)
    write_jsonl(out_dir / "pools" / "memos_source_snapshot.jsonl", snapshots)
    write_jsonl(out_dir / "support_audit" / "pending.jsonl",
                [{"case_id": row["case_id"], "cache_key": support_cache_key(row, model),
                  "payload": support_payload(row)} for row in pending])
    prompt_chars = sum(len(support_audit.build_prompt([support_payload(row)])) for row in pending)
    budget = {
        "source_rows": len(samples), "nonempty_evidence": sum(bool(r["gold_evidence"]) for r in samples),
        "serializer_ok": sum(r["serializer_ok"] for r in samples),
        "cached_support": len(support), "pending_cases": len(pending),
        "calls_estimate": len(pending), "max_attempts_including_retries": len(pending) * 3,
        "input_characters": prompt_chars,
        "input_tokens_rough_estimate": (prompt_chars + 3) // 4,
        "input_token_estimate_method": "characters/4 rough estimate; actual API usage is logged",
        "output_token_cap_per_call": 1800, "model": model, "temperature": 0,
        "support_audit_scope": "independent retrieval entailment; no baseline correctness shortcut",
        "serializer_failures": [r["case_id"] for r in samples if not r["serializer_ok"]],
        "exclusion_counts": dict(Counter(r["pool_exclusion_reason"] for r in snapshots if not r["pool_eligible"])),
        "source_files": {str(p.relative_to(ROOT)): file_hash(p) for _, p in RUNS.values()},
        "legacy_support_sha256": file_hash(SEMANTIC_DETAIL),
        "support_prompt_sha256": sha256_text(support_audit.build_prompt([])),
    }
    write_json(out_dir / "support_audit" / "budget.json", budget)
    merge_run_config("memos_pool_preparation", budget, out_dir)
    print(json.dumps(budget, ensure_ascii=False, indent=2), flush=True)
    return budget


def run_support_audit(pending: list[dict[str, Any]], model: str, workers: int = 12,
                      out_dir: Path = OUT_DIR) -> dict[str, Any]:
    # One explicit retry layer makes the printed three-attempt budget truthful;
    # the SDK otherwise performs additional hidden transport retries.
    client = make_client().with_options(max_retries=0)
    lock = Lock()
    failures = []
    usage = Counter()

    def run_one(sample: dict[str, Any]) -> dict[str, Any]:
        payload = support_payload(sample)
        prompt = support_audit.build_prompt([payload])
        key = support_cache_key(sample, model)
        calls: list[dict[str, Any]] = []

        def call() -> dict[str, Any]:
            completion = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, temperature=0,
                max_tokens=1800, timeout=300)
            call_usage = completion.usage.model_dump() if completion.usage is not None else {}
            calls.append(call_usage)
            parsed = support_audit.parse_json(completion.choices[0].message.content or "")
            cases = parsed.get("cases")
            if not isinstance(cases, list) or len(cases) != 1:
                raise ValueError("Support audit must return exactly the requested case")
            result = cases[0]
            if result.get("case_id") != sample["case_id"]:
                raise ValueError("Support audit case identity mismatch")
            expected = {f"e{i}" for i in range(1, len(sample["gold_evidence"]) + 1)}
            items = result.get("evidence_results")
            if (not isinstance(items, list) or len(items) != len(expected)
                    or {x.get("evidence_id") for x in items} != expected):
                raise ValueError("Support audit evidence coverage mismatch")
            if any(x.get("status") not in support_audit.STATUS_SET for x in items):
                raise ValueError("Support audit status is invalid")
            valid_memory_ids = {f"m{i}" for i in range(1, len(sample.get("raw_memories") or []) + 1)}
            if any(not isinstance(x.get("best_memory_ids"), list)
                   or not set(x["best_memory_ids"]) <= valid_memory_ids for x in items):
                raise ValueError("Support audit memory identity mismatch")
            normalized = support_audit.normalize_case_result(audit_sample(sample), result)
            return normalized

        try:
            result = retry_call("pool_support_audit", call, retries=3)
            value = {"cache_key": key, "input_hash": json_hash(payload), "model": model,
                     "version": SUPPORT_VERSION, "prompt_hash": sha256_text(prompt),
                     "prompt": prompt, "usage_by_attempt": calls, "result": result}
            write_json(out_dir / "support_audit" / "cache" / f"{key}.json", value)
        except Exception as error:
            value = {"cache_key": key, "case_id": sample["case_id"],
                     "error": f"{type(error).__name__}: {error}", "usage_by_attempt": calls}
        append_jsonl(out_dir / "support_audit" / "attempts.jsonl", {
            "case_id": sample["case_id"], "cache_key": key,
            "error": value.get("error"), "usage_by_attempt": calls,
        }, lock)
        return value

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one, sample) for sample in pending]
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result.get("error"):
                failures.append(result)
            for item in result.get("usage_by_attempt", []):
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    usage[key] += int(item.get(key) or 0)
            if completed % 25 == 0 or completed == len(pending):
                print(f"support_audit completed={completed}/{len(pending)} failed={len(failures)}", flush=True)
    stats = {"scheduled": len(pending), "completed": completed,
             "failed": len(failures), "usage": dict(usage), "failures": failures}
    write_json(out_dir / "support_audit" / "last_execution.json", stats)
    merge_run_config("memos_support_audit_last_execution", stats, out_dir)
    return stats


def build_memos_pool(model: str = "deepseek-chat", out_dir: Path = OUT_DIR) -> list[dict[str, Any]]:
    samples = load_source_samples()
    support, pending = load_support(samples, model, out_dir)
    snapshots = enrich_sources(samples, support)
    write_jsonl(out_dir / "pools" / "memos_source_snapshot.jsonl", snapshots)
    mismatches = [r["case_id"] for r in samples if not r["serializer_ok"]]
    if mismatches:
        raise RuntimeError(f"Source serializer verification failed: {len(mismatches)} cases; first={mismatches[:5]}")
    if pending:
        raise RuntimeError(f"Missing independent support audit for {len(pending)} eligible source rows; "
                           "run --prepare support-audit, then --audit-support --yes. "
                           "Correct labels cannot substitute for support.")
    pool = [row for row in snapshots if row["pool_eligible"]]
    write_jsonl(out_dir / "pools" / "memos_pool.jsonl", pool)
    write_jsonl(out_dir / "pools" / "memos_visibility.jsonl", [
        {key: row[key] for key in ("case_id", "serializer_ok", "visible_memory_ids", "gold_visible_ids",
                                  "partial_visible_ids", "visible_stratum", "pref_note", "n_raw", "n_visible")}
        for row in snapshots])
    old_ids = {r["case_id"] for r in read_jsonl(OLD_DIR / "samples_memos_full.jsonl")}
    source_wrong = {r["case_id"] for r in pool if r.get("baseline_label") != "correct"}
    equivalence = {
        "comparison": "archived baseline labels; B0 replay equality is checked after generation/judge",
        "legacy_wrong_n": len(old_ids), "new_pool_archived_wrong_n": len(source_wrong),
        "equal": old_ids == source_wrong,
        "missing_from_new_pool": sorted(old_ids - source_wrong),
        "added_to_new_pool": sorted(source_wrong - old_ids),
        "explanation": "New task-book pool excludes no_gold_retrieved, unlike old 1987 wrong-only pool; "
                       "reported mismatch is non-blocking and old flip rates are reference-only.",
    }
    write_json(out_dir / "pools" / "memos_pool_equivalence.json", equivalence)
    stats = {"dataset": "memos", "source_n": len(samples), "pool_n": len(pool),
             "retrieval_strata": dict(Counter(r["retrieval_stratum"] for r in pool)),
             "archived_baseline_labels": dict(Counter(r.get("baseline_label") for r in pool)),
             "exclusion_counts": dict(Counter(r["pool_exclusion_reason"] for r in snapshots if not r["pool_eligible"])),
             "pool_sha256": file_hash(out_dir / "pools" / "memos_pool.jsonl"),
             "equivalence": equivalence, "source_audit_complete": True}
    write_json(out_dir / "pools" / "memos_pool_summary.json", stats)
    merge_run_config("memos_pool", stats, out_dir)
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    return pool


def build_other_system_pool(system: str, out_dir: Path = OUT_DIR) -> list[dict[str, Any]]:
    """Stage E uses saved wrong-only data, never pretends to measure do-no-harm."""
    specs = [s for s in support_audit.INPUTS if s["system"] == system and s["path"].exists()]
    if not specs:
        raise FileNotFoundError(f"No archived raw-memory source for {system}")
    rows = []
    for spec in specs:
        for i, raw in enumerate(read_jsonl(spec["path"]), 1):
            if raw.get("baseline_label") == "correct":
                continue
            if not raw.get("raw_memories") or not raw.get("context_str_full"):
                continue
            rows.append({**raw, "case_id": f"{spec['run_id']}:{i}",
                         "system_kind": system, "system": system,
                         "dataset": spec["dataset"], "gold_evidence": support_audit.evidence_texts(raw),
                         "baseline_verdict": raw.get("baseline_label") or "",
                         "baseline_answer": raw.get("baseline_response") or "", "pref_note": "",
                         "evaluation_scope": "archived_wrong_only_stage_E_flip_rate_only"})
    write_jsonl(out_dir / "pools" / f"{system}_pool.jsonl", rows)
    merge_run_config(f"{system}_pool", {"pool_n": len(rows), "stage": "E",
                     "do_no_harm_available": False, "noop_err_available": False}, out_dir)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("memos", "longmemeval", "mem0", "memobase", "supermemory"), required=True)
    parser.add_argument("--prepare", choices=("support-audit",))
    parser.add_argument("--audit-support", action="store_true")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.dataset == "memos":
        samples = load_source_samples()
        support, pending = load_support(samples, args.model, args.out_dir)
        print(f"Budget: support audit calls={len(pending) if args.audit_support else 0}; "
              f"pool building calls=0; pending independent support cases={len(pending)}", flush=True)
        prepare_support(samples, support, pending, args.model, args.out_dir)
        if args.prepare:
            return
        if not args.yes:
            parser.error("Execution requires --yes after the printed budget (preparation uses zero API calls)")
        if args.audit_support:
            if len(pending) > 30000:
                raise RuntimeError("Support budget >30,000: first run/report a fixed 400-case subset")
            run_support_audit(pending, args.model, args.workers, args.out_dir)
        build_memos_pool(args.model, args.out_dir)
    elif args.dataset == "longmemeval":
        print("Budget: LLM calls=0; download cleaned S only; one retrieval per case then frozen", flush=True)
        if not args.yes:
            parser.error("Download/retrieval execution requires --yes")
        spec = importlib.util.spec_from_file_location("a2_build_longmemeval", Path(__file__).with_name("25_build_longmemeval.py"))
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load LongMemEval builder")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.build_longmemeval(out_dir=args.out_dir)
    else:
        print("Budget: LLM calls=0; archived Stage E wrong-only sources", flush=True)
        if not args.yes:
            parser.error("Pool execution requires --yes")
        build_other_system_pool(args.dataset, args.out_dir)


if __name__ == "__main__":
    main()
