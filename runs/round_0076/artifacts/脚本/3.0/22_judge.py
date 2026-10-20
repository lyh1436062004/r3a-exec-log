"""Resumable gold-only judging, with the official LongMemEval QA criteria."""
from __future__ import annotations

import argparse
import importlib
import json
import math
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

import e1_memos_oracle_common as common
from a2_arms import get_arm

runner = importlib.import_module("21_run_generation")
OUT_DIR = runner.OUT_DIR
VERSION = "a2-judge-v1"
OFFICIAL_SOURCE = "https://github.com/xiaowu0162/LongMemEval/blob/main/src/evaluation/evaluate_qa.py"

# The following prompt strings are copied from get_anscheck_prompt() in the
# official LongMemEval implementation, inspected for this task. No benchmark
# task type or abstention identifier reaches the deployment pipeline.
#
# MIT License
# Copyright (c) 2024 Di Wu
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
_BASE_CHECK = (
    "I will give you a question, a correct answer, and a response from a model. "
    "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
    "If the response is equivalent to the correct answer or contains all the intermediate "
    "steps to get the correct answer, you should also answer yes. If the response only "
    "contains a subset of the information required by the answer, answer no."
)
_QA_SUFFIX = "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response correct? Answer yes or no only."
OFFICIAL_TEMPLATES = {
    "information": _BASE_CHECK + _QA_SUFFIX,
    "temporal-reasoning": _BASE_CHECK + (
        " In addition, do not penalize off-by-one errors for the number of days. "
        "If the question asks for the number of days/weeks/months, etc., and the model "
        "makes off-by-one errors (e.g., predicting 19 days when the answer is 18), "
        "the model's response is still correct. "
    ) + _QA_SUFFIX,
    "knowledge-update": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response contains some previous information along with an updated answer, "
        "the response should be considered as correct as long as the updated answer is the required answer."
    ) + _QA_SUFFIX,
    "single-session-preference": (
        "I will give you a question, a rubric for desired personalized response, and a "
        "response from a model. Please answer yes if the response satisfies the desired "
        "response. Otherwise, answer no. The model does not need to reflect all the points "
        "in the rubric. The response is correct as long as it recalls and utilizes the user's "
        "personal information correctly.\n\nQuestion: {}\n\nRubric: {}\n\nModel Response: {}"
        "\n\nIs the model response correct? Answer yes or no only."
    ),
    "abstention": (
        "I will give you an unanswerable question, an explanation, and a response from a model. "
        "Please answer yes if the model correctly identifies the question as unanswerable. "
        "The model could say that the information is incomplete, or some other information "
        "is given but the asked information is not.\n\nQuestion: {}\n\nExplanation: {}"
        "\n\nModel Response: {}\n\nDoes the model correctly identify the question as unanswerable? "
        "Answer yes or no only."
    ),
}
OFFICIAL_SNAPSHOT_HASH = runner.json_hash(OFFICIAL_TEMPLATES)


def longmemeval_prompt(sample: dict[str, Any], answer: str) -> str:
    question = str(sample.get("original_question") or sample["question"])
    reference = str(sample.get("gold_answer") or "")
    original_id = str(sample.get("original_question_id") or "")
    if "_abs" in original_id:
        kind = "abstention"
    else:
        kind = str(sample.get("question_type") or "")
        if kind in {"single-session-user", "single-session-assistant", "multi-session"}:
            kind = "information"
    if kind not in OFFICIAL_TEMPLATES:
        raise ValueError(f"Unknown official LongMemEval question type: {kind}")
    return OFFICIAL_TEMPLATES[kind].format(question, reference, answer)


def parse_official_yes_no(content: str) -> bool:
    # Unlike the official substring predicate, malformed or missing judgments
    # are errors to retry, not false answers that contaminate the C/H/O scores.
    text = content.strip().lower().strip('"\'').strip()
    if not re.fullmatch(r"(?:yes|no)[.!]?", text):
        raise ValueError("Official judge did not return exactly yes/no")
    return text.rstrip(".!") == "yes"


def judge_prompt_hash(sample: dict[str, Any], answer: str) -> str:
    if sample.get("system_kind") == "longmemeval":
        return common.sha256_text(longmemeval_prompt(sample, answer))
    return common.sha256_text(common.build_gold_only_judge_prompt({
        "question": str(sample["question"]), "gold_answer": str(sample.get("gold_answer") or ""),
        "model_answer": answer}))


def judge_cache_key(sample: dict[str, Any], generation: dict[str, Any],
                    endpoint: dict[str, Any]) -> str:
    answer = str(generation["model_answer"])
    return runner.json_hash({
        "version": VERSION, "generation_cache_key": generation["cache_key"],
        "sample_input_hash": runner.sample_input_hash(sample), "endpoint": endpoint,
        "question": str(sample.get("original_question") or sample["question"]),
        "gold_answer": str(sample.get("gold_answer") or ""), "model_answer": answer,
        "judge_prompt_hash": judge_prompt_hash(sample, answer), "temperature": 0,
        "judge_max_tokens": common.JUDGE_MAX_TOKENS,
        "official_snapshot_hash": OFFICIAL_SNAPSHOT_HASH if sample.get("system_kind") == "longmemeval" else None,
        "taxonomy_prompt_hash": common.sha256_text(common.build_gold_only_judge_prompt({
            "question": str(sample.get("original_question") or sample["question"]),
            "gold_answer": str(sample.get("gold_answer") or ""), "model_answer": answer})),
    })


def judge_one(sample: dict[str, Any], generation: dict[str, Any],
               client: Any, endpoint: dict[str, Any]) -> dict[str, Any]:
    is_lme = sample.get("system_kind") == "longmemeval"
    tracked = runner.TrackingClient(client, endpoint["model"], 9 if is_lme else 6)
    key = judge_cache_key(sample, generation, endpoint)
    row = {name: generation[name] for name in ("case_id", "pool", "arm", "artifact_arm", "generator")}
    row.update({"cache_key": key, "judge_cache_key": key, "input_hash": key,
                "generation_cache_key": generation["cache_key"], "gen_cache_key": generation["cache_key"],
                "sample_input_hash": runner.sample_input_hash(sample),
                "question": str(sample.get("original_question") or sample["question"]),
                "gold_answer": str(sample.get("gold_answer") or ""),
                "model_answer": str(generation["model_answer"]), "model": endpoint["model"],
                "base_url": endpoint["base_url"], "temperature": 0,
                "judge_prompt_hash": judge_prompt_hash(sample, str(generation["model_answer"]))})
    started = time.perf_counter()
    try:
        if is_lme:
            prompt = longmemeval_prompt(sample, row["model_answer"])

            def official_call() -> bool:
                response = tracked.chat.completions.create(
                    model=endpoint["model"], messages=[{"role": "user", "content": prompt}],
                    n=1, temperature=0, max_tokens=10, timeout=common.TIMEOUT)
                return parse_official_yes_no(response.choices[0].message.content or "")

            correct = common.retry_call("longmemeval-official-judge", official_call, retries=3)
            row.update({"official_correct": correct, "official_source": OFFICIAL_SOURCE,
                        "official_prompt_snapshot_hash": OFFICIAL_SNAPSHOT_HASH,
                        "question_type": sample.get("question_type"),
                        "is_abstention": "_abs" in str(sample.get("original_question_id") or "")})
            if correct:
                verdict = {"label": "correct", "rationale": "Official type-specific criterion: yes"}
            else:
                verdict, _ = common.call_judge(tracked, row["question"], row["gold_answer"], row["model_answer"])
                row["incorrect_taxonomy_source"] = "supplementary_gold_only_judge_after_official_no"
                if verdict["label"] == "correct":
                    raise ValueError("Official correctness and supplementary C/H/O taxonomy disagree")
        else:
            verdict, _ = common.call_judge(tracked, row["question"], row["gold_answer"], row["model_answer"])
        if verdict.get("label") not in {"correct", "hallucination", "omission"}:
            raise ValueError("Unrecognized C/H/O verdict")
        row.update({"ok": True, "judge_label": verdict["label"],
                    "judge_rationale": verdict.get("rationale", "")})
    except Exception as error:
        # No invented O label: unsuccessful calls remain pending on the next run.
        row.update({"ok": False, "error": type(error).__name__})
        if is_lme and row.get("official_correct") is False:
            row["error_type"] = "supplementary_taxonomy_failed_or_conflicted"
    row.update({"usage": tracked.usage(), "usage_by_attempt": tracked.events,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return row


def load_selection(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pool_path = args.out_dir / "pools" / f"{args.pool}_pool.jsonl"
    if not pool_path.exists():
        raise FileNotFoundError(f"Required pool is missing: {pool_path}")
    manifest_path = runner.selection_path(args.pool, args.out_dir, args.limit, args.subset)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Run generation for the same selection first: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["pool_sha256"] != runner.file_hash(pool_path):
        raise ValueError("Pool changed after the generation selection manifest")
    samples = common.read_jsonl(pool_path)
    by_id = {str(row["case_id"]): row for row in samples}
    ids = manifest["case_ids"]
    if len(set(ids)) != len(ids) or any(case_id not in by_id for case_id in ids):
        raise ValueError("Generation selection manifest is inconsistent with pool")
    if not manifest.get("budget_fallback_400"):
        expected = [str(row["case_id"]) for row in runner.select_samples(samples, args.limit, args.subset)]
        if ids != expected:
            raise ValueError("Judge and generator selections differ")
    return [by_id[case_id] for case_id in ids], manifest


def current_generations(samples: list[dict[str, Any]], arm: str, generator: str,
                        endpoint: dict[str, Any], out_dir: Path, pool: str,
                        lambda_o: float, expected_context_keys: dict[str, str] | None = None
                        ) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[str]]:
    tag = runner.artifact_arm(arm, lambda_o)
    by_id = {str(row["case_id"]): row for row in samples}
    input_hashes = {cid: runner.sample_input_hash(sample) for cid, sample in by_id.items()}
    current: dict[str, dict[str, Any]] = {}
    hashes = runner.controller_hashes()
    latest_contexts: dict[str, dict[str, Any]] = {}
    for context in common.read_jsonl(out_dir / "contexts" / pool / f"{tag}.jsonl"):
        cid = str(context.get("case_id"))
        if (cid not in by_id or context.get("controller_hashes") != hashes
                or context.get("sample_input_hash") != input_hashes[cid]
                or context.get("lambda_o") != lambda_o or context.get("leakage_errors")):
            continue
        if expected_context_keys is not None and context.get("cache_key") != expected_context_keys.get(cid):
            continue
        latest_contexts[cid] = context
    for row in common.read_jsonl(out_dir / "generations" / pool / f"{tag}__{generator}.jsonl"):
        if not row.get("ok") or str(row.get("case_id")) not in by_id:
            continue
        sample = by_id[str(row["case_id"])]
        context = latest_contexts.get(str(sample["case_id"]))
        if (not context or row.get("context_cache_key") != context.get("cache_key")
                or row.get("sample_input_hash") != input_hashes[str(sample["case_id"])]):
            continue
        if context.get("sample_input_hash") != row["sample_input_hash"] or context.get("controller_hashes") != hashes:
            continue
        prompt = common.build_answer_prompt(context["context"], sample["question"])
        expected = runner.generation_cache_key(str(sample["case_id"]), arm, prompt, endpoint, context)
        if (row.get("cache_key") != expected or row.get("prompt_hash") != common.sha256_text(prompt)
                or row.get("context_hash") != common.sha256_text(context["context"])
                or row.get("lambda_o") != lambda_o):
            continue
        current[str(row["case_id"])] = row
    return [(sample, current[str(sample["case_id"])]) for sample in samples
            if str(sample["case_id"]) in current], [str(sample["case_id"]) for sample in samples
                                                    if str(sample["case_id"]) not in current]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default="memos")
    parser.add_argument("--arm", default=",".join(runner.MAIN_ARMS))
    parser.add_argument("--generator", default=common.MODEL)
    parser.add_argument("--judge-generator", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--subset", type=int, default=0)
    parser.add_argument("--lambda-o", type=float, default=1.0)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 12 or not math.isfinite(args.lambda_o) or args.lambda_o < 0:
        parser.error("workers must be 1..12; lambda-o finite and nonnegative")
    return args


def main() -> None:
    args = parse_args()
    arms = list(dict.fromkeys(x.strip() for x in args.arm.split(",") if x.strip()))
    for arm in arms:
        if get_arm(arm).reference_only:
            raise ValueError("Archived ORACLE_REL reference is not generated or rejudged")
    registry = runner.generator_registry(args.out_dir)
    names = list(registry) if args.generator == "all" else [x.strip() for x in args.generator.split(",") if x.strip()]
    judge_name = args.judge_generator or next(iter(registry))
    if judge_name not in registry or not names or any(name not in registry for name in names):
        raise ValueError("Requested generator/judge is absent from the actual endpoint registry")
    endpoint = registry[judge_name]
    samples, manifest = load_selection(args)
    if args.pool == "longmemeval" and "B0" not in arms:
        arms = ["B0", *arms]
    tasks = []
    missing = []
    for arm in arms:
        tag = runner.artifact_arm(arm, args.lambda_o)
        for name in names:
            pairs, missing_ids = current_generations(samples, arm, name, registry[name],
                                                     args.out_dir, args.pool, args.lambda_o,
                                                     manifest.get("context_keys", {}).get(tag))
            missing.extend({"case_id": case_id, "arm": arm, "generator": name} for case_id in missing_ids)
            path = args.out_dir / "verdicts" / args.pool / f"{tag}__{name}.jsonl"
            done = common.completed_by_cache(path)
            for sample, gen in pairs:
                key = judge_cache_key(sample, gen, endpoint)
                if key not in done:
                    tasks.append((sample, gen, path))
    lme = args.pool == "longmemeval"
    budget = {"pool": args.pool, "arms": arms, "generators": names, "judge": endpoint,
              "n_selected": len(samples), "pending_verdicts": len(tasks), "missing_generations": len(missing),
              "estimated_calls_upper_bound": len(tasks) * (2 if lme else 1),
              "estimated_attempts_upper_bound": len(tasks) * (9 if lme else 6),
              "temperature": 0, "max_workers": args.workers, "manifest": manifest,
              "official_source": OFFICIAL_SOURCE if lme else None,
              "official_prompt_snapshot_hash": OFFICIAL_SNAPSHOT_HASH if lme else None,
              "incorrect_taxonomy": "supplementary gold-only C/H/O; conflicting C stays an error" if lme else "gold-only C/H/O"}
    print(json.dumps({"Budget": budget}, ensure_ascii=False, indent=2), flush=True)
    runner.merge_config(f"judge_{args.pool}_{runner.selection_name(args.limit, args.subset)}", budget, args.out_dir)
    if args.dry_run:
        return
    if not args.yes:
        raise RuntimeError("Pass --yes after reviewing the printed judge budget")
    if budget["estimated_calls_upper_bound"] > 30_000:
        raise RuntimeError("Judge budget exceeds 30,000; generate and judge the same --subset 400 first")
    if tasks:
        runner.require_account_available(endpoint)
    lock = Lock()
    client = runner.make_endpoint_client(endpoint)

    def run(task: tuple[dict[str, Any], dict[str, Any], Path]) -> dict[str, Any]:
        sample, generation, path = task
        row = judge_one(sample, generation, client, endpoint)
        common.append_jsonl(path, row, lock)
        common.append_jsonl(args.out_dir / "analysis" / f"{args.pool}_judge_attempts.jsonl",
                            {key: row[key] for key in ("case_id", "arm", "generator", "cache_key", "ok",
                                                       "usage", "usage_by_attempt", "created_at")}, lock)
        return row

    usage: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run, task) for task in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            usage.update(row["usage"])
            if row["ok"]:
                labels[row["judge_label"]] += 1
            else:
                errors += 1
            if index % 25 == 0 or index == len(tasks):
                print(f"judged completed={index}/{len(tasks)} failures={errors}", flush=True)
    summary = {"scheduled": len(tasks), "failed": errors, "labels_this_run": dict(labels),
               "usage_this_run": dict(usage), "missing_generations": missing, "budget": budget}
    common.write_json(args.out_dir / "analysis" / f"{args.pool}_judge_run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
