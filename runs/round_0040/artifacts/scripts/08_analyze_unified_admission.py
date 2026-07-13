from __future__ import annotations

import math
from collections import Counter
from typing import Any

from e1_memos_oracle_common import OUT_DIR, load_samples, read_jsonl, write_csv, write_json


def exact_mcnemar_p(b: int, c: int) -> float | None:
    total = b + c
    if not total:
        return None
    try:
        from scipy.stats import binomtest  # type: ignore

        return float(binomtest(min(b, c), total, 0.5).pvalue)
    except Exception:  # noqa: BLE001
        probability = sum(math.comb(total, i) for i in range(min(b, c) + 1)) * (0.5**total)
        return min(1.0, 2 * probability)


def verdict_map(condition: str) -> dict[str, str]:
    return {
        str(row["case_id"]): str(row["judge_label"])
        for row in read_jsonl(OUT_DIR / "verdicts" / f"{condition}.jsonl")
        if row.get("ok")
    }


def main() -> None:
    samples = {str(row["case_id"]): row for row in load_samples()}
    labels = {condition: verdict_map(condition) for condition in ("A0", "A6", "A7")}
    stable = [
        case_id
        for case_id, sample in samples.items()
        if sample.get("retrieval_stratum") == "strict_supported" and labels["A0"].get(case_id) != "correct"
    ]
    missing = {
        condition: [case_id for case_id in stable if case_id not in labels[condition]]
        for condition in ("A6", "A7")
    }
    if any(missing.values()):
        raise RuntimeError(f"missing treatment verdicts: { {key: len(value) for key, value in missing.items()} }")

    groups: dict[str, list[str]] = {
        "strict_stable_wrong": stable,
        "visible_supported": [case_id for case_id in stable if samples[case_id].get("visible_stratum") == "visible_supported"],
        "serialization_loss": [case_id for case_id in stable if samples[case_id].get("visible_stratum") == "serialization_loss"],
    }
    rows: list[dict[str, Any]] = []
    mcnemar_rows: list[dict[str, Any]] = []
    for group, case_ids in groups.items():
        a6_correct = sum(labels["A6"][case_id] == "correct" for case_id in case_ids)
        a7_correct = sum(labels["A7"][case_id] == "correct" for case_id in case_ids)
        b = sum(labels["A7"][case_id] == "correct" and labels["A6"][case_id] != "correct" for case_id in case_ids)
        c = sum(labels["A6"][case_id] == "correct" and labels["A7"][case_id] != "correct" for case_id in case_ids)
        rows.append(
            {
                "pool": group,
                "n": len(case_ids),
                "a6_correct": a6_correct,
                "a6_rate": a6_correct / len(case_ids) if case_ids else 0.0,
                "a7_correct": a7_correct,
                "a7_rate": a7_correct / len(case_ids) if case_ids else 0.0,
                "a7_minus_a6": (a7_correct - a6_correct) / len(case_ids) if case_ids else 0.0,
            }
        )
        mcnemar_rows.append(
            {"pool": group, "comparison": "A7_vs_A6", "n": len(case_ids), "b": b, "c": c, "p_value": exact_mcnemar_p(b, c)}
        )

    admission = {}
    admission_path = OUT_DIR / "unified_admission_summary.json"
    if admission_path.exists():
        import json

        admission = json.loads(admission_path.read_text(encoding="utf-8"))

    write_csv(
        OUT_DIR / "unified_admission_effect_by_stratum.csv",
        rows,
        ["pool", "n", "a6_correct", "a6_rate", "a7_correct", "a7_rate", "a7_minus_a6"],
    )
    write_csv(
        OUT_DIR / "unified_admission_mcnemar.csv",
        mcnemar_rows,
        ["pool", "comparison", "n", "b", "c", "p_value"],
    )
    result = {"admission": admission, "effects": rows, "mcnemar": mcnemar_rows}
    write_json(OUT_DIR / "unified_admission_effect.json", result)

    lines = ["# Unified Admission And Authorization Effect", ""]
    lines.extend(
        [
            f"- Raw memory admission rate: {admission.get('raw_admission_rate', 0):.2%}",
            f"- Strict gold-memory admission rate: {admission.get('strict_gold_admission_rate', 0):.2%}",
            "",
            "| pool | n | A6 visibility-only | A7 + unified authorization | delta |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['pool']} | {row['n']} | {row['a6_correct']}/{row['n']} ({row['a6_rate']:.2%}) "
            f"| {row['a7_correct']}/{row['n']} ({row['a7_rate']:.2%}) | {row['a7_minus_a6']:+.2%} |"
        )
    lines.extend(["", "## Paired McNemar", "", "| pool | b | c | p |", "|---|---:|---:|---:|"])
    for row in mcnemar_rows:
        lines.append(f"| {row['pool']} | {row['b']} | {row['c']} | {row['p_value']} |")
    (OUT_DIR / "unified_admission_effect.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
