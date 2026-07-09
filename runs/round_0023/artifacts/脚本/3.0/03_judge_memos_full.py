from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from e1_memos_oracle_common import (
    CONDITIONS,
    MODEL,
    OUT_DIR,
    SEED,
    append_jsonl,
    call_judge,
    completed_by_cache,
    deterministic_sample,
    make_client,
    read_jsonl,
    sha256_text,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", default=",".join(CONDITIONS))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--stability-size", type=int, default=200)
    return parser.parse_args()


def load_generation_rows(condition: str) -> list[dict[str, Any]]:
    rows = [row for row in read_jsonl(OUT_DIR / "generations" / f"{condition}.jsonl") if row.get("ok")]
    rows.sort(key=lambda row: str(row.get("case_id")))
    return rows


def judge_cache_key(gen: dict[str, Any]) -> str:
    return sha256_text("|".join([str(gen["cache_key"]), MODEL, str(gen.get("model_answer", ""))]))


def verdict_record(gen: dict[str, Any], verdict: dict[str, str], api_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "cache_key": judge_cache_key(gen),
        "generation_cache_key": gen["cache_key"],
        "case_id": gen["case_id"],
        "condition": gen["condition"],
        "run_id": gen["run_id"],
        "dataset": gen["dataset"],
        "qa_key": gen["qa_key"],
        "uuid": gen["uuid"],
        "question_type": gen["question_type"],
        "baseline_label": gen["baseline_label"],
        "retrieval_stratum": gen["retrieval_stratum"],
        "semantic_any_supported": gen["semantic_any_supported"],
        "semantic_any_partial_or_supported": gen["semantic_any_partial_or_supported"],
        "question": gen["question"],
        "gold_answer": gen["gold_answer"],
        "model_answer": gen["model_answer"],
        "judge_label": verdict["label"],
        "judge_rationale": verdict["rationale"],
        "model": MODEL,
        "latency_ms": api_meta.get("latency_ms"),
        "usage": api_meta.get("usage", {}),
        "judge_prompt_hash": api_meta.get("judge_prompt_hash"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main() -> None:
    args = parse_args()
    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    bad_conditions = [item for item in conditions if item not in CONDITIONS]
    if bad_conditions:
        raise ValueError(f"Unknown conditions: {bad_conditions}")

    (OUT_DIR / "verdicts").mkdir(parents=True, exist_ok=True)
    tasks: list[dict[str, Any]] = []
    for condition in conditions:
        rows = load_generation_rows(condition)
        if args.limit:
            rows = rows[: args.limit]
        existing = completed_by_cache(OUT_DIR / "verdicts" / f"{condition}.jsonl")
        for row in rows:
            key = judge_cache_key(row)
            if key not in existing:
                tasks.append(row)

    print(f"pending judge tasks: {len(tasks)}")
    client = make_client()
    lock = Lock()

    def worker(gen: dict[str, Any]) -> dict[str, Any]:
        try:
            verdict, api_meta = call_judge(client, gen["question"], gen["gold_answer"], gen["model_answer"])
            return verdict_record(gen, verdict, api_meta)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "cache_key": judge_cache_key(gen),
                "generation_cache_key": gen.get("cache_key"),
                "case_id": gen.get("case_id"),
                "condition": gen.get("condition"),
                "error": repr(exc),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(worker, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            out_path = OUT_DIR / "verdicts" / f"{row['condition']}.jsonl"
            append_jsonl(out_path, row, lock)
            done += 1
            if done % 50 == 0 or done == len(tasks):
                print(f"judged {done}/{len(tasks)}")

    if args.stability_size > 0:
        all_verdicts: list[dict[str, Any]] = []
        for condition in conditions:
            all_verdicts.extend([row for row in read_jsonl(OUT_DIR / "verdicts" / f"{condition}.jsonl") if row.get("ok")])
        selected = deterministic_sample(all_verdicts, args.stability_size, seed=SEED)
        agreements = 0
        reruns = []
        for idx, row in enumerate(selected, 1):
            verdict, api_meta = call_judge(client, row["question"], row["gold_answer"], row["model_answer"])
            agree = verdict["label"] == row["judge_label"]
            agreements += int(agree)
            reruns.append(
                {
                    "case_id": row["case_id"],
                    "condition": row["condition"],
                    "original_label": row["judge_label"],
                    "rerun_label": verdict["label"],
                    "agree": agree,
                    "usage": api_meta.get("usage", {}),
                }
            )
            if idx % 25 == 0 or idx == len(selected):
                print(f"stability rerun {idx}/{len(selected)}")
        result = {
            "seed": SEED,
            "requested": args.stability_size,
            "n": len(selected),
            "agreements": agreements,
            "self_agreement": agreements / len(selected) if selected else None,
            "reruns": reruns,
        }
        write_json(OUT_DIR / "judge_self_agreement.json", result)
        if selected and result["self_agreement"] < 0.90:
            raise RuntimeError(f"Judge self-agreement below 0.90: {result['self_agreement']:.3f}")


if __name__ == "__main__":
    main()
