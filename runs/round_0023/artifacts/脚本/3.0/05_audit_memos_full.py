from __future__ import annotations

import argparse
import json
from typing import Any

from e1_memos_oracle_common import (
    OUT_DIR,
    deterministic_sample,
    load_samples,
    memory_text,
    raw_id_to_index,
    read_jsonl,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-n", type=int, default=60)
    parser.add_argument("--partial-n", type=int, default=30)
    parser.add_argument("--none-n", type=int, default=30)
    return parser.parse_args()


def load_condition(condition: str) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in read_jsonl(OUT_DIR / "verdicts" / f"{condition}.jsonl") if row.get("ok")}


def support_texts(sample: dict[str, Any]) -> str:
    ids = list(sample.get("gold_memory_ids") or []) + list(sample.get("partial_memory_ids") or [])
    raw = sample.get("raw_memories") or []
    rows = []
    for memory_id in ids:
        index = raw_id_to_index(memory_id)
        if index is None or index >= len(raw):
            continue
        text = memory_text(raw[index])
        if text:
            rows.append(f"{memory_id}: {text}")
    return "\n\n".join(rows)


def main() -> None:
    args = parse_args()
    samples = load_samples()
    a0 = load_condition("A0")
    a3 = load_condition("A3")
    stable = [row for row in samples if a0.get(row["case_id"], {}).get("judge_label") != "correct"]
    strict = [row for row in stable if row.get("retrieval_stratum") == "strict_supported"]
    partial = [row for row in stable if row.get("retrieval_stratum") == "partial_supported"]
    none = [row for row in stable if row.get("retrieval_stratum") == "no_gold_retrieved"]
    selected = (
        deterministic_sample(strict, args.strict_n)
        + deterministic_sample(partial, args.partial_n)
        + deterministic_sample(none, args.none_n)
    )
    rows = []
    for sample in selected:
        case_id = sample["case_id"]
        rows.append(
            {
                "case_id": case_id,
                "dataset": sample.get("dataset"),
                "question_type": sample.get("question_type"),
                "baseline_label": sample.get("baseline_label"),
                "retrieval_stratum": sample.get("retrieval_stratum"),
                "question": sample.get("question"),
                "gold_answer": sample.get("gold_answer"),
                "gold_evidence": json.dumps(sample.get("gold_evidence") or [], ensure_ascii=False),
                "support_memory_texts": support_texts(sample),
                "A0_answer": a0.get(case_id, {}).get("model_answer", ""),
                "A0_label": a0.get(case_id, {}).get("judge_label", ""),
                "A3_answer": a3.get(case_id, {}).get("model_answer", ""),
                "A3_label": a3.get(case_id, {}).get("judge_label", ""),
                "human_support_valid": "",
                "human_flip_valid": "",
                "human_notes": "",
            }
        )
    fields = [
        "case_id",
        "dataset",
        "question_type",
        "baseline_label",
        "retrieval_stratum",
        "question",
        "gold_answer",
        "gold_evidence",
        "support_memory_texts",
        "A0_answer",
        "A0_label",
        "A3_answer",
        "A3_label",
        "human_support_valid",
        "human_flip_valid",
        "human_notes",
    ]
    out = OUT_DIR / "audit" / "audit_samples.csv"
    write_csv(out, rows, fields)
    labeled_out = OUT_DIR / "audit" / "audit_with_human_labels.csv"
    write_csv(labeled_out, rows, fields)
    agreement = OUT_DIR / "audit" / "human_agreement.md"
    agreement.write_text(
        "\n".join(
            [
                "# Human Agreement",
                "",
                "Status: pending human labels.",
                "",
                "`audit_with_human_labels.csv` has been initialized with blank human columns. ",
                "After manual review, rerun the recovery/agreement step to compute judge-human agreement.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} audit rows to {out}")
    print(f"initialized human-label sheet at {labeled_out}")


if __name__ == "__main__":
    main()
