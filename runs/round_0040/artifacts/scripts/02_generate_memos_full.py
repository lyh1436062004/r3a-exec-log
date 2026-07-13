from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from e1_memos_oracle_common import (
    CONDITIONS,
    GEN_MAX_TOKENS,
    MODEL,
    OUT_DIR,
    PROMPT_MEMOS,
    TEMPERATURE,
    append_jsonl,
    build_answer_prompt,
    build_context,
    call_chat,
    completed_by_cache,
    load_samples,
    make_client,
    prompt_hashes,
    sha256_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--retrieval-strata",
        default="",
        help="Comma-separated retrieval_stratum filter, e.g. strict_supported",
    )
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-a0-correct",
        action="store_true",
        help="干预臂只跑 A0 重放后仍非 correct 的样本(需先完成 A0 的生成与评判),节省预算",
    )
    parser.add_argument(
        "--e1-prime-eligible-only",
        action="store_true",
        help="Run treatment arms only on visible_supported cases that remain non-correct in A0.",
    )
    return parser.parse_args()


def load_a0_correct_case_ids() -> set[str]:
    from e1_memos_oracle_common import read_jsonl

    rows = [r for r in read_jsonl(OUT_DIR / "verdicts" / "A0.jsonl") if r.get("ok")]
    if not rows:
        raise RuntimeError("--skip-a0-correct 需要先完成 A0 的生成与评判 (verdicts/A0.jsonl)")
    return {str(r["case_id"]) for r in rows if str(r.get("judge_label")) == "correct"}


def load_e1_prime_eligible_case_ids(samples: list[dict[str, Any]]) -> set[str]:
    from e1_memos_oracle_common import read_jsonl

    rows = [r for r in read_jsonl(OUT_DIR / "verdicts" / "A0.jsonl") if r.get("ok")]
    if not rows:
        raise RuntimeError("--e1-prime-eligible-only requires verdicts/A0.jsonl")
    a0_labels = {str(r["case_id"]): str(r.get("judge_label")) for r in rows}
    eligible = {
        str(sample["case_id"])
        for sample in samples
        if sample.get("visible_stratum") == "visible_supported"
        and a0_labels.get(str(sample["case_id"])) not in {None, "correct"}
    }
    if len(eligible) != 737:
        raise RuntimeError(f"E1-prime eligibility invariant failed: expected 737, got {len(eligible)}")
    return eligible


def build_task(sample: dict[str, Any], condition: str) -> dict[str, Any]:
    context, meta = build_context(sample, condition)
    if meta.get("leakage_errors"):
        return {
            "ok": False,
            "case_id": sample["case_id"],
            "condition": condition,
            "error_type": "leakage",
            "errors": meta["leakage_errors"],
            "meta": meta,
        }
    prompt = build_answer_prompt(context, sample["question"])
    hashes = prompt_hashes()
    cache_key = sha256_text(
        "|".join(
            [
                str(sample["case_id"]),
                condition,
                meta["context_hash"],
                MODEL,
                hashes["answer_prompt_hash"],
            ]
        )
    )
    return {
        "ok": True,
        "cache_key": cache_key,
        "condition": condition,
        "case_id": sample["case_id"],
        "sample": sample,
        "context": context,
        "prompt": prompt,
        "meta": meta,
        **hashes,
    }


def generation_record(task: dict[str, Any], answer: str, api_meta: dict[str, Any]) -> dict[str, Any]:
    sample = task["sample"]
    return {
        "ok": True,
        "cache_key": task["cache_key"],
        "case_id": sample["case_id"],
        "condition": task["condition"],
        "run_id": sample["run_id"],
        "dataset": sample["dataset"],
        "qa_key": sample["qa_key"],
        "uuid": sample["uuid"],
        "question_type": sample["question_type"],
        "baseline_label": sample["baseline_label"],
        "retrieval_stratum": sample["retrieval_stratum"],
        "semantic_any_supported": sample["semantic_any_supported"],
        "semantic_any_partial_or_supported": sample["semantic_any_partial_or_supported"],
        "question": sample["question"],
        "gold_answer": sample["gold_answer"],
        "gold_evidence": sample["gold_evidence"],
        "model_answer": answer,
        "context": task["context"],
        "prompt": task["prompt"],
        "model": MODEL,
        "temperature": TEMPERATURE,
        "max_tokens": GEN_MAX_TOKENS,
        "context_hash": task["meta"]["context_hash"],
        "prompt_hash": sha256_text(task["prompt"]),
        "answer_prompt_hash": task["answer_prompt_hash"],
        "license_counts": task["meta"].get("license_counts", {}),
        "n_context_memories": task["meta"].get("n_context_memories", 0),
        "n_raw_memories": task["meta"].get("n_raw_memories"),
        "n_admitted_memories": task["meta"].get("n_admitted_memories"),
        "n_dropped_memories": task["meta"].get("n_dropped_memories"),
        "admitted_memory_ids": task["meta"].get("admitted_memory_ids", []),
        "gold_admitted_ids": task["meta"].get("gold_admitted_ids", []),
        "latency_ms": api_meta.get("latency_ms"),
        "usage": api_meta.get("usage", {}),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main() -> None:
    args = parse_args()
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    bad_conditions = [item for item in conditions if item not in CONDITIONS]
    if bad_conditions:
        raise ValueError(f"Unknown conditions: {bad_conditions}")

    samples = load_samples()
    strata = {item.strip() for item in args.retrieval_strata.split(",") if item.strip()}
    if strata:
        samples = [sample for sample in samples if str(sample.get("retrieval_stratum")) in strata]
        print(f"retrieval-strata={sorted(strata)}: {len(samples)} samples selected")
    if args.limit:
        samples = samples[: args.limit]

    a0_correct: set[str] = set()
    if args.skip_a0_correct:
        a0_correct = load_a0_correct_case_ids()
        print(f"skip-a0-correct: {len(a0_correct)} samples will be skipped for non-A0 conditions")

    e1_prime_eligible: set[str] | None = None
    if args.e1_prime_eligible_only:
        if "A0" in conditions:
            raise RuntimeError("--e1-prime-eligible-only is for A1-A5 treatment arms, not A0")
        e1_prime_eligible = load_e1_prime_eligible_case_ids(samples)
        print(f"E1-prime eligible treatment pool: {len(e1_prime_eligible)} samples")

    selected_count = len(e1_prime_eligible) if e1_prime_eligible is not None else len(samples)
    total_calls = selected_count * len(conditions)
    print("Budget sanity check")
    print(f"generation calls: {total_calls}")
    print(f"judge calls: {total_calls}, handled by 03_judge_memos_full.py")
    print("judge stability reruns: configured separately in 03_judge_memos_full.py")
    print("estimated input tokens if avg context is 4k: about 80M tokens")
    if not args.yes and not args.dry_run:
        raise RuntimeError("Pass --yes to acknowledge the budget sanity check.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "generations").mkdir(parents=True, exist_ok=True)

    tasks: list[dict[str, Any]] = []
    leakage_failures: list[dict[str, Any]] = []
    existing_by_condition = {
        condition: completed_by_cache(OUT_DIR / "generations" / f"{condition}.jsonl")
        for condition in conditions
    }
    for sample in samples:
        for condition in conditions:
            if e1_prime_eligible is not None and str(sample["case_id"]) not in e1_prime_eligible:
                continue
            if condition != "A0" and str(sample["case_id"]) in a0_correct:
                continue
            task = build_task(sample, condition)
            if not task.get("ok"):
                leakage_failures.append(task)
                continue
            if task["cache_key"] in existing_by_condition[condition]:
                continue
            tasks.append(task)

    if leakage_failures:
        with (OUT_DIR / "leakage_failures.jsonl").open("a", encoding="utf-8") as f:
            for row in leakage_failures:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        raise RuntimeError(f"Leakage check failed for {len(leakage_failures)} tasks")

    print(f"pending generation tasks: {len(tasks)}")
    if args.dry_run:
        return

    client = make_client()
    lock = Lock()

    def worker(task: dict[str, Any]) -> dict[str, Any]:
        try:
            answer, api_meta = call_chat(client, task["prompt"])
            return generation_record(task, answer, api_meta)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "cache_key": task["cache_key"],
                "case_id": task["case_id"],
                "condition": task["condition"],
                "error": repr(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            out_path = OUT_DIR / "generations" / f"{row['condition']}.jsonl"
            append_jsonl(out_path, row, lock)
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"generated {done}/{len(tasks)}")


if __name__ == "__main__":
    main()
