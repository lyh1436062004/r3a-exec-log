"""Post-hoc estimator diagnostics; labels never flow back into deployment."""
from __future__ import annotations

import argparse
import importlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

from a2_schema import RELATIONS
from a2_stage0_adapter import adapt
from a2_stage1_estimator import estimate_cache_key, estimate_cache_path, _load_cached

stats = importlib.import_module("23_analyze")
OUT_DIR = stats.OUT_DIR

# These are deliberately coarse task-type proxies, not complete ground truth.
# No predicted relation participates in constructing a diagnostic target.
TYPE_PROXY = {
    "dynamic update": "SUPERSEDED",
    "knowledge-update": "SUPERSEDED",
    "memory binding": "MISBIND",
    "entity misbinding": "MISBIND",
    "insufficient information": "INSUFFICIENT",
    "unanswerable": "INSUFFICIENT",
    "abstention": "INSUFFICIENT",
}


def oracle_relation(memory_id: str, sample: dict[str, Any]) -> str | None:
    if memory_id in set(sample.get("gold_memory_ids") or []):
        return "SUPPORT"
    question_type = str(sample.get("question_type") or "").strip().lower().replace("_", "-")
    return TYPE_PROXY.get(question_type)


def confusion_metrics(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    counts = Counter(pairs)
    total = len(pairs)
    per_class = []
    for relation in RELATIONS:
        true_positive = counts[(relation, relation)]
        target_n = sum(counts[(relation, predicted)] for predicted in RELATIONS)
        predicted_n = sum(counts[(target, relation)] for target in RELATIONS)
        precision = true_positive / predicted_n if predicted_n else 0.0
        recall = true_positive / target_n if target_n else 0.0
        f1 = 2 * true_positive / (target_n + predicted_n) if target_n + predicted_n else 0.0
        per_class.append({"relation": relation, "target_n": target_n, "predicted_n": predicted_n,
                          "precision": precision, "recall": recall, "f1": f1})
    represented = [row for row in per_class if row["target_n"] or row["predicted_n"]]
    return {"n": total,
            "accuracy": sum(counts[(name, name)] for name in RELATIONS) / total if total else None,
            "macro_F1_all_six_labels": sum(row["f1"] for row in per_class) / len(RELATIONS) if total else None,
            "macro_F1_represented_union": sum(row["f1"] for row in represented) / len(represented) if represented else None,
            "per_class": per_class,
            "confusion": {target: {predicted: counts[(target, predicted)] for predicted in RELATIONS}
                          for target in RELATIONS}}


def roc_auc(scores: list[float], targets: list[int]) -> float | None:
    """Mann–Whitney AUC, averaging tied ranks; bad B0 is the positive class."""
    positives = sum(targets)
    negatives = len(targets) - positives
    if positives == 0 or negatives == 0:
        return None
    ranked = sorted(zip(scores, targets))
    rank_sum = 0.0
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end][0] == ranked[start][0]:
            end += 1
        average_rank = ((start + 1) + end) / 2
        rank_sum += average_rank * sum(target for _, target in ranked[start:end])
        start = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def point_biserial(values: list[float], targets: list[int]) -> float | None:
    if len(values) < 3 or len(set(targets)) < 2:
        return None
    mean_x, mean_y = sum(values) / len(values), sum(targets) / len(targets)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(values, targets))
    denom = math.sqrt(sum((x - mean_x) ** 2 for x in values) * sum((y - mean_y) ** 2 for y in targets))
    return numerator / denom if denom else None


def intrinsic_eval(pool: str, out_dir: Path = OUT_DIR, generator: str = "deepseek-chat",
                   model: str = "deepseek-chat", oracle_arm: str = "UA3") -> dict[str, Any]:
    pool_path = out_dir / "pools" / f"{pool}_pool.jsonl"
    samples = stats.latest_rows(pool_path)
    b0, generations, rejected = stats.load_arm_cache(out_dir, pool, "B0", generator)
    legacy_samples = stats.latest_rows(stats.OLD_DIR / "samples_memos_full.jsonl")
    historical = stats.latest_rows(stats.OLD_DIR / "verdicts" / f"{oracle_arm}.jsonl")
    historical_b0 = stats.latest_rows(stats.OLD_DIR / "verdicts" / "A0.jsonl")
    estimated, failed, absent, stale = 0, 0, [], []
    relation_pairs: list[tuple[str, str]] = []
    relation_rows = []
    skipped_types = Counter()
    risks, wrong, success_risks, success_wrong = [], [], [], []
    sufficiencies, rescued = [], []
    risk_case_rows, oracle_rows = [], []
    hashes = {str(pool_path): stats.file_hash(pool_path)} if pool_path.exists() else {}
    for cid, sample in samples.items():
        records = adapt(list(sample.get("raw_memories") or []), str(sample.get("system_kind") or sample.get("system") or "memos"))
        path = estimate_cache_path(cid, pool, out_dir)
        if not path.exists():
            absent.append(cid)
            continue
        expected_hash = estimate_cache_key(str(sample.get("question") or ""), records, model)
        result = _load_cached(path, expected_hash, records)
        hashes[str(path)] = stats.file_hash(path)
        if result is None:
            stale.append(cid)
            continue
        estimated += 1
        failed += result.failed
        current_b0 = b0.get(cid)
        deployed_hash = stats.sample_input_hash(sample)
        if (current_b0 and current_b0.get("sample_input_hash") == deployed_hash
                and generations[cid].get("sample_input_hash") == deployed_hash):
            verdict = stats.label(current_b0)
            is_wrong = int(verdict != "correct")
            risks.append(result.risk)
            wrong.append(is_wrong)
            if not result.failed:
                success_risks.append(result.risk)
                success_wrong.append(is_wrong)
            risk_case_rows.append({"case_id": cid, "risk": result.risk,
                                   "B0_label": verdict, "estimation_failed": result.failed})
        # A failed estimate is a deployed no-op, not evidence of relation quality.
        if not result.failed:
            for identifier, memory in result.memories.items():
                target = oracle_relation(identifier, sample)
                if target is None:
                    skipped_types[str(sample.get("question_type") or "unknown")] += 1
                    continue
                predicted = max(RELATIONS, key=lambda relation: memory.relation_posterior[relation])
                relation_pairs.append((target, predicted))
                relation_rows.append({"case_id": cid, "memory_id": identifier,
                                      "oracle_proxy_relation": target, "predicted_relation": predicted,
                                      "question_type": sample.get("question_type")})
        old = legacy_samples.get(cid)
        oracle_verdict = stats.label(historical.get(cid))
        baseline_now = stats.label(current_b0)
        same_input = old is not None and all(sample.get(field) == old.get(field) for field in
                                            ("question", "gold_answer", "raw_memories", "context_str_full"))
        if (pool == "memos" and not result.failed and same_input and oracle_verdict is not None
                and stats.label(historical_b0.get(cid)) in ("hallucination", "omission")
                and baseline_now in ("hallucination", "omission")
                and current_b0.get("sample_input_hash") == deployed_hash):
            repaired = int(oracle_verdict == "correct")
            sufficiencies.append(result.sufficiency)
            rescued.append(repaired)
            oracle_rows.append({"case_id": cid, "sufficiency": result.sufficiency,
                                "oracle_arm": oracle_arm, "oracle_label": oracle_verdict,
                                "oracle_repaired": repaired})
    for path in (out_dir / "generations" / pool / f"B0__{generator}.jsonl",
                 out_dir / "verdicts" / pool / f"B0__{generator}.jsonl",
                 stats.OLD_DIR / "samples_memos_full.jsonl",
                 stats.OLD_DIR / "verdicts" / f"{oracle_arm}.jsonl",
                 stats.OLD_DIR / "verdicts" / "A0.jsonl"):
        if path.exists():
            hashes[str(path)] = stats.file_hash(path)
    risk_groups = {name: [score for score, target in zip(risks, wrong) if target == value]
                   for name, value in (("B0_correct", 0), ("B0_wrong", 1))}
    group_summary = {name: {"n": len(scores), "mean": sum(scores) / len(scores) if scores else None,
                           "min": min(scores) if scores else None, "max": max(scores) if scores else None}
                     for name, scores in risk_groups.items()}
    summary = {
        "pool": pool, "generator": generator, "estimator_model": model, "pool_n": len(samples),
        "valid_estimate_n": estimated, "failed_estimate_n": failed,
        "missing_estimate_ids": absent, "stale_estimate_ids": stale,
        "oracle_relation_proxy": confusion_metrics(relation_pairs),
        "non_gold_question_type_mapping": TYPE_PROXY, "skipped_non_gold_by_type": dict(skipped_types),
        "oracle_proxy_warning": "Gold positions are SUPPORT by the requested diagnostic convention even when real relations may be REFUTE/CURRENT. Task type is a coarse proxy; not every non-gold update memory is necessarily obsolete. Unidentified non-gold relations are skipped; model predictions never construct targets. This is partial proxy agreement, not six-way independently annotated accuracy.",
        "sufficiency_oracle_repair": {
            "oracle_arm": oracle_arm, "same_input_case_id_join_n": len(rescued),
            "point_biserial_r": point_biserial(sufficiencies, rescued),
            "oracle_repaired_n": sum(rescued),
            "missing_reason": "No same-input historical oracle join or insufficient variation" if point_biserial(sufficiencies, rescued) is None else None,
            "scope": "Historical wrong AND fresh B0 wrong; exact question/gold/raw/context match; oracle arm has a real verdict. No inferred recovery from a predicted relation."},
        "risk_vs_fresh_B0": {"n": len(risks), "B0_wrong_n": sum(wrong),
                             "auc_including_failed_safe_defaults": roc_auc(risks, wrong),
                             "auc_successful_estimates_only": roc_auc(success_risks, success_wrong),
                             "score_groups": group_summary,
                             "missing_reason": "No two-class fresh B0 join" if roc_auc(risks, wrong) is None else None},
        "rejected_stale_B0_judgments": rejected,
        "input_hashes": hashes, "input_hash": stats.json_hash(hashes),
        "script_sha256": stats.file_hash(Path(__file__)), "estimated_calls": 0,
    }
    prefix = f"{pool}__{generator}"
    stats.write_json(out_dir / "analysis" / f"{prefix}_intrinsic.json", summary)
    stats.write_csv(out_dir / "analysis" / f"{prefix}_intrinsic_relation_cases.csv", relation_rows)
    stats.write_csv(out_dir / "analysis" / f"{prefix}_intrinsic_confusion.csv", [
        {"target": target, "predicted": predicted, "count": summary["oracle_relation_proxy"]["confusion"][target][predicted]}
        for target in RELATIONS for predicted in RELATIONS])
    stats.write_csv(out_dir / "analysis" / f"{prefix}_intrinsic_risk_cases.csv", risk_case_rows)
    stats.write_csv(out_dir / "analysis" / f"{prefix}_intrinsic_oracle_join.csv", oracle_rows)
    stats.merge_config(f"intrinsic_{prefix}", {"estimated_calls": 0, "input_hashes": hashes,
                                                "script_sha256": summary["script_sha256"]}, out_dir)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default="memos")
    parser.add_argument("--generator", default="deepseek-chat")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--oracle-arm", choices=("UA3", "A3"), default="UA3")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    print("Budget: intrinsic diagnostics LLM calls=0; post-hoc cached joins only", flush=True)
    summary = intrinsic_eval(args.pool, args.out_dir, args.generator, args.model, args.oracle_arm)
    stats.build_report(args.out_dir)
    print({"pool": args.pool, "valid_estimates": summary["valid_estimate_n"],
           "proxy_pairs": summary["oracle_relation_proxy"]["n"], "fresh_B0_pairs": summary["risk_vs_fresh_B0"]["n"]}, flush=True)


if __name__ == "__main__":
    main()
