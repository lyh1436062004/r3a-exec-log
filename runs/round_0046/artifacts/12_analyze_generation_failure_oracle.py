from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "e1_memos_generation_failure_oracle_v1"
EXPECTED_CASES = 381
EXPECTED_GENERATIONS = 1143
DENOMINATORS = {"candidate_pool": 381, "visible_strict": 763, "all_baseline_errors": 1987}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-incomplete", action="store_true")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def latest_ok_by(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, Any]]:
    out: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("ok"):
            out[tuple(str(row.get(field)) for field in key_fields)] = row
    return out


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def classify_case(
    sufficiency: dict[str, Any] | None,
    generations: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
) -> str:
    if sufficiency is None or len(generations) != 3 or len(judgments) != 3:
        return "unresolved"
    if not sufficiency.get("response_model"):
        return "unresolved"
    if any(not row.get("response_model") for row in generations + judgments):
        return "unresolved"
    verdict = str(sufficiency.get("verdict"))
    if verdict in {"partial", "insufficient"}:
        return "evidence_definition_failure"
    if verdict != "sufficient":
        return "unresolved"
    correct = sum(str(row.get("label")) == "correct" for row in judgments)
    if correct == 0:
        return "robust_generation_failure"
    if correct == 3:
        return "ua3_representation_or_admission_failure"
    return "generation_instability"


def main() -> None:
    args = parse_args()
    candidates = read_jsonl(OUT_DIR / "candidate_pool.jsonl")
    candidate_map = {str(row["case_id"]): row for row in candidates}
    generations = latest_ok_by(OUT_DIR / "generations.jsonl", ("case_id", "replicate"))
    sufficiency = latest_ok_by(OUT_DIR / "evidence_sufficiency.jsonl", ("case_id",))
    judgments = latest_ok_by(OUT_DIR / "answer_judgments.jsonl", ("case_id", "replicate"))

    coverage = {
        "candidates": len(candidate_map),
        "generations": len(generations),
        "sufficiency_verdicts": len(sufficiency),
        "answer_judgments": len(judgments),
    }
    expected = {
        "candidates": EXPECTED_CASES,
        "generations": EXPECTED_GENERATIONS,
        "sufficiency_verdicts": EXPECTED_CASES,
        "answer_judgments": EXPECTED_GENERATIONS,
    }
    if coverage != expected and not args.allow_incomplete:
        raise RuntimeError(f"incomplete experiment: expected={expected}, actual={coverage}")

    case_rows: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []
    for case_id, case in sorted(candidate_map.items()):
        case_generations = [
            generations[(case_id, str(replicate))]
            for replicate in range(1, 4)
            if (case_id, str(replicate)) in generations
        ]
        case_judgments = [
            judgments[(case_id, str(replicate))]
            for replicate in range(1, 4)
            if (case_id, str(replicate)) in judgments
        ]
        suff = sufficiency.get((case_id,))
        auto_class = classify_case(suff, case_generations, case_judgments)
        row: dict[str, Any] = {
            "case_id": case_id,
            "dataset": case.get("dataset"),
            "qa_key": case.get("qa_key"),
            "question_type": case.get("question_type"),
            "question": case.get("question"),
            "gold_answer": case.get("gold_answer"),
            "gold_evidence": case.get("gold_evidence"),
            "gold_evidence_rendered": case.get("gold_context"),
            "source_ua3_answer": case.get("source_ua3_answer"),
            "source_ua3_label": case.get("source_ua3_label"),
            "sufficiency_verdict": suff.get("verdict") if suff else "",
            "sufficiency_missing_information": suff.get("missing_information") if suff else "",
            "sufficiency_rationale": suff.get("rationale") if suff else "",
            "sufficiency_response_model": suff.get("response_model") if suff else "",
            "automatic_classification": auto_class,
        }
        for replicate in range(1, 4):
            gen = generations.get((case_id, str(replicate)))
            judge = judgments.get((case_id, str(replicate)))
            row[f"run_{replicate}_answer"] = gen.get("model_answer") if gen else ""
            row[f"run_{replicate}_generation_model"] = gen.get("response_model") if gen else ""
            row[f"run_{replicate}_judge_label"] = judge.get("label") if judge else ""
            row[f"run_{replicate}_judge_rationale"] = judge.get("rationale") if judge else ""
            row[f"run_{replicate}_judge_model"] = judge.get("response_model") if judge else ""
            if gen:
                call_rows.append(
                    {
                        "case_id": case_id,
                        "dataset": case.get("dataset"),
                        "question_type": case.get("question_type"),
                        "replicate": replicate,
                        "question": case.get("question"),
                        "gold_answer": case.get("gold_answer"),
                        "model_answer": gen.get("model_answer"),
                        "generation_requested_model": gen.get("requested_model"),
                        "generation_response_model": gen.get("response_model"),
                        "context_hash": gen.get("gold_context_hash"),
                        "prompt_hash": gen.get("prompt_hash"),
                        "generation_latency_ms": gen.get("latency_ms"),
                        "generation_usage": json.dumps(gen.get("usage") or {}, ensure_ascii=False),
                        "judge_label": judge.get("label") if judge else "",
                        "judge_rationale": judge.get("rationale") if judge else "",
                        "judge_requested_model": judge.get("requested_model") if judge else "",
                        "judge_response_model": judge.get("response_model") if judge else "",
                        "judge_latency_ms": judge.get("latency_ms") if judge else "",
                        "judge_usage": json.dumps(judge.get("usage") or {}, ensure_ascii=False) if judge else "",
                    }
                )
        case_rows.append(row)

    classification_counts = Counter(str(row["automatic_classification"]) for row in case_rows)
    robust = classification_counts["robust_generation_failure"]
    rate_rows: list[dict[str, Any]] = []
    for denominator_name, denominator in DENOMINATORS.items():
        low, high = wilson(robust, denominator)
        rate_rows.append(
            {
                "denominator": denominator_name,
                "robust_generation_failures": robust,
                "n": denominator,
                "rate": robust / denominator,
                "wilson_low": low,
                "wilson_high": high,
            }
        )

    grouped_rows: list[dict[str, Any]] = []
    for field in ("dataset", "question_type"):
        groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in case_rows:
            groups[str(row.get(field))].append(row)
        for value, rows in sorted(groups.items()):
            counts = Counter(str(row["automatic_classification"]) for row in rows)
            grouped_rows.append(
                {
                    "field": field,
                    "value": value,
                    "n": len(rows),
                    "robust_generation_failure": counts["robust_generation_failure"],
                    "generation_instability": counts["generation_instability"],
                    "ua3_representation_or_admission_failure": counts[
                        "ua3_representation_or_admission_failure"
                    ],
                    "evidence_definition_failure": counts["evidence_definition_failure"],
                    "unresolved": counts["unresolved"],
                }
            )

    case_fields = [
        "case_id",
        "dataset",
        "qa_key",
        "question_type",
        "question",
        "gold_answer",
        "gold_evidence",
        "gold_evidence_rendered",
        "source_ua3_answer",
        "source_ua3_label",
        "sufficiency_verdict",
        "sufficiency_missing_information",
        "sufficiency_rationale",
        "sufficiency_response_model",
        "automatic_classification",
    ]
    for replicate in range(1, 4):
        case_fields.extend(
            [
                f"run_{replicate}_answer",
                f"run_{replicate}_generation_model",
                f"run_{replicate}_judge_label",
                f"run_{replicate}_judge_rationale",
                f"run_{replicate}_judge_model",
            ]
        )
    call_fields = list(call_rows[0].keys()) if call_rows else []

    write_jsonl(OUT_DIR / "case_summary.jsonl", case_rows)
    write_jsonl(OUT_DIR / "call_details.jsonl", call_rows)
    write_csv(OUT_DIR / "case_summary.csv", case_rows, case_fields)
    write_csv(OUT_DIR / "call_details.csv", call_rows, call_fields)
    write_csv(OUT_DIR / "robust_failure_rates.csv", rate_rows, list(rate_rows[0].keys()))
    write_csv(OUT_DIR / "results_by_group.csv", grouped_rows, list(grouped_rows[0].keys()))

    result = {
        "coverage": coverage,
        "classification_counts": dict(classification_counts),
        "rates": rate_rows,
        "by_group": grouped_rows,
    }
    write_json(OUT_DIR / "results.json", result)

    lines = [
        "# Direct Gold-Evidence Generation-Failure Experiment",
        "",
        "## Coverage",
        "",
        f"- Candidates: {coverage['candidates']}/{EXPECTED_CASES}",
        f"- Generations: {coverage['generations']}/{EXPECTED_GENERATIONS}",
        f"- Sufficiency verdicts: {coverage['sufficiency_verdicts']}/{EXPECTED_CASES}",
        f"- Answer judgments: {coverage['answer_judgments']}/{EXPECTED_GENERATIONS}",
        "",
        "## Automatic Classification",
        "",
        "| class | count | rate among 381 |",
        "|---|---:|---:|",
    ]
    for name in (
        "robust_generation_failure",
        "generation_instability",
        "ua3_representation_or_admission_failure",
        "evidence_definition_failure",
        "unresolved",
    ):
        count = classification_counts[name]
        lines.append(f"| {name} | {count} | {count / EXPECTED_CASES:.2%} |")
    lines.extend(["", "## Robust Failure Rates", "", "| denominator | count / n | rate | 95% Wilson CI |", "|---|---:|---:|---:|"])
    for row in rate_rows:
        lines.append(
            f"| {row['denominator']} | {row['robust_generation_failures']}/{row['n']} "
            f"| {row['rate']:.2%} | [{row['wilson_low']:.2%}, {row['wilson_high']:.2%}] |"
        )
    (OUT_DIR / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
