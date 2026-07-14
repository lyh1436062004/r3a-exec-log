from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from e1_memos_oracle_common import OUT_DIR, UNIFIED_A_CONDITIONS, load_samples, read_jsonl, write_csv, write_json


BASE_CONDITIONS = ["A6", *UNIFIED_A_CONDITIONS]
PRIMARY_PAIRS = [
    ("UA1", "A6"),
    ("UA2", "UA1"),
    ("UA3", "UA2"),
    ("UA4", "A6"),
    ("UA5", "A6"),
    ("UA5", "UA4"),
]


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


def rate_row(pool: str, condition: str, case_ids: list[str], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    values = [labels[condition].get(case_id) for case_id in case_ids]
    values = [value for value in values if value]
    correct = sum(value == "correct" for value in values)
    return {
        "pool": pool,
        "condition": condition,
        "n": len(values),
        "correct": correct,
        "recovery_rate": correct / len(values) if values else 0.0,
    }


def paired_row(pool: str, left: str, right: str, case_ids: list[str], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    paired = [case_id for case_id in case_ids if case_id in labels[left] and case_id in labels[right]]
    b = sum(labels[left][case_id] == "correct" and labels[right][case_id] != "correct" for case_id in paired)
    c = sum(labels[right][case_id] == "correct" and labels[left][case_id] != "correct" for case_id in paired)
    return {
        "pool": pool,
        "comparison": f"{left}_vs_{right}",
        "n": len(paired),
        "b": b,
        "c": c,
        "net_correct": b - c,
        "delta_rate": (b - c) / len(paired) if paired else 0.0,
        "p_value": exact_mcnemar_p(b, c),
    }


def main() -> None:
    samples = {str(row["case_id"]): row for row in load_samples()}
    all_conditions = ["A0", *BASE_CONDITIONS, "A1", "A2", "A3", "A4", "A5"]
    labels = {condition: verdict_map(condition) for condition in all_conditions}
    strict_all = [
        case_id for case_id, sample in samples.items() if sample.get("retrieval_stratum") == "strict_supported"
    ]
    stable = [
        case_id
        for case_id, sample in samples.items()
        if sample.get("retrieval_stratum") == "strict_supported" and labels["A0"].get(case_id) != "correct"
    ]
    groups = {
        "strict_stable_wrong": stable,
        "visible_supported": [case_id for case_id in stable if samples[case_id].get("visible_stratum") == "visible_supported"],
        "serialization_loss": [case_id for case_id in stable if samples[case_id].get("visible_stratum") == "serialization_loss"],
    }
    missing = {
        condition: sum(case_id not in labels[condition] for case_id in strict_all)
        for condition in BASE_CONDITIONS
    }
    if any(missing.values()):
        raise RuntimeError(f"missing verdicts: {missing}")

    rate_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    for pool, case_ids in groups.items():
        for condition in BASE_CONDITIONS:
            rate_rows.append(rate_row(pool, condition, case_ids, labels))
        for left, right in PRIMARY_PAIRS:
            paired_rows.append(paired_row(pool, left, right, case_ids, labels))

    same_pool_ids = groups["visible_supported"]
    old_new_rows: list[dict[str, Any]] = []
    for number in range(1, 6):
        row = paired_row("visible_supported", f"UA{number}", f"A{number}", same_pool_ids, labels)
        old_rate = rate_row("visible_supported", f"A{number}", same_pool_ids, labels)
        new_rate = rate_row("visible_supported", f"UA{number}", same_pool_ids, labels)
        row.update(
            {
                "old_correct": old_rate["correct"],
                "old_rate": old_rate["recovery_rate"],
                "new_correct": new_rate["correct"],
                "new_rate": new_rate["recovery_rate"],
            }
        )
        old_new_rows.append(row)

    full_strict_rates = [rate_row("strict_all", condition, strict_all, labels) for condition in ["A0", *BASE_CONDITIONS]]
    full_strict_pairs = [
        paired_row("strict_all", condition, "A0", strict_all, labels) for condition in BASE_CONDITIONS
    ]

    by_dataset_rows: list[dict[str, Any]] = []
    by_dataset: defaultdict[str, list[str]] = defaultdict(list)
    for case_id in stable:
        by_dataset[str(samples[case_id].get("dataset"))].append(case_id)
    for dataset, case_ids in sorted(by_dataset.items()):
        for condition in BASE_CONDITIONS:
            row = rate_row(dataset, condition, case_ids, labels)
            row["dataset"] = row.pop("pool")
            by_dataset_rows.append(row)

    write_csv(OUT_DIR / "unified_a1_a5_rates.csv", rate_rows, ["pool", "condition", "n", "correct", "recovery_rate"])
    write_csv(
        OUT_DIR / "unified_a1_a5_mcnemar.csv",
        paired_rows,
        ["pool", "comparison", "n", "b", "c", "net_correct", "delta_rate", "p_value"],
    )
    write_csv(
        OUT_DIR / "unified_a1_a5_old_vs_new.csv",
        old_new_rows,
        [
            "pool",
            "comparison",
            "n",
            "old_correct",
            "old_rate",
            "new_correct",
            "new_rate",
            "b",
            "c",
            "net_correct",
            "delta_rate",
            "p_value",
        ],
    )
    write_csv(
        OUT_DIR / "unified_a1_a5_by_dataset.csv",
        by_dataset_rows,
        ["dataset", "condition", "n", "correct", "recovery_rate"],
    )
    write_csv(
        OUT_DIR / "unified_a1_a5_full_strict.csv",
        full_strict_rates,
        ["pool", "condition", "n", "correct", "recovery_rate"],
    )
    write_csv(
        OUT_DIR / "unified_a1_a5_full_strict_vs_a0.csv",
        full_strict_pairs,
        ["pool", "comparison", "n", "b", "c", "net_correct", "delta_rate", "p_value"],
    )

    result = {
        "scope": {
            "strict_stable_wrong": len(stable),
            "visible_supported": len(groups["visible_supported"]),
            "serialization_loss": len(groups["serialization_loss"]),
        },
        "rates": rate_rows,
        "paired_tests": paired_rows,
        "old_vs_new_same_pool": old_new_rows,
        "by_dataset": by_dataset_rows,
        "full_strict_rates": full_strict_rates,
        "full_strict_vs_a0": full_strict_pairs,
    }
    write_json(OUT_DIR / "unified_a1_a5_results.json", result)

    main_rates = [row for row in rate_rows if row["pool"] == "strict_stable_wrong"]
    main_pairs = [row for row in paired_rows if row["pool"] == "strict_stable_wrong"]
    lines = [
        "# Unified Parsing A1-A5 Results",
        "",
        "All UA arms use the complete raw-memory payload and the same canonical serializer as A6.",
        "The denominator is the 867 strict-supported cases that remained non-correct under exact A0 replay.",
        "Judge self-agreement is reported separately; exact McNemar p-values below are unadjusted for multiple comparisons.",
        "",
        "## Conditions",
        "",
        "- A6: canonicalize and admit all raw memories in retrieval order; no labels.",
        "- UA1: A6 plus oracle gold-first ordering.",
        "- UA2: canonicalize and retain oracle gold memories only.",
        "- UA3: UA2 plus relation-specific evidence licenses.",
        "- UA4: A6 plus relation-specific licenses on oracle gold memories.",
        "- UA5: UA4 plus VOUCH on oracle gold memories otherwise labeled ASSERT.",
        "",
        "## Main Recovery Rates",
        "",
        "| condition | correct / n | recovery rate |",
        "|---|---:|---:|",
    ]
    for row in main_rates:
        lines.append(f"| {row['condition']} | {row['correct']} / {row['n']} | {row['recovery_rate']:.2%} |")
    lines.extend(["", "## Primary Paired Comparisons", "", "| comparison | b | c | delta | exact p |", "|---|---:|---:|---:|---:|"])
    for row in main_pairs:
        p_value = "NA" if row["p_value"] is None else f"{row['p_value']:.6g}"
        lines.append(f"| {row['comparison']} | {row['b']} | {row['c']} | {row['delta_rate']:+.2%} | {p_value} |")
    lines.extend(
        [
            "",
            "## Full Strict Pool Accuracy (Supplementary)",
            "",
            "This includes the 29 strict cases that A0 replay judged correct, so regressions are observable.",
            "",
            "| condition | correct / n | accuracy | vs A0 b | vs A0 c | net delta | exact p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    full_pair_map = {row["comparison"].split("_vs_")[0]: row for row in full_strict_pairs}
    for row in full_strict_rates:
        pair = full_pair_map.get(row["condition"])
        if pair is None:
            lines.append(
                f"| {row['condition']} | {row['correct']} / {row['n']} | {row['recovery_rate']:.2%} "
                "| - | - | - | - |"
            )
            continue
        p_value = "NA" if pair["p_value"] is None else f"{pair['p_value']:.6g}"
        lines.append(
            f"| {row['condition']} | {row['correct']} / {row['n']} | {row['recovery_rate']:.2%} "
            f"| {pair['b']} | {pair['c']} | {pair['delta_rate']:+.2%} | {p_value} |"
        )
    lines.extend(
        [
            "",
            "## By Visibility Stratum",
            "",
            "| pool | condition | correct / n | recovery rate |",
            "|---|---|---:|---:|",
        ]
    )
    for row in rate_rows:
        if row["pool"] == "strict_stable_wrong":
            continue
        lines.append(
            f"| {row['pool']} | {row['condition']} | {row['correct']} / {row['n']} | {row['recovery_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## By Dataset",
            "",
            "| dataset | condition | correct / n | recovery rate |",
            "|---|---|---:|---:|",
        ]
    )
    for row in by_dataset_rows:
        lines.append(
            f"| {row['dataset']} | {row['condition']} | {row['correct']} / {row['n']} | {row['recovery_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Unified vs Original A1-A5 (Same 737 Cases)",
            "",
            "| comparison | old | unified | delta | b | c | exact p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in old_new_rows:
        p_value = "NA" if row["p_value"] is None else f"{row['p_value']:.6g}"
        lines.append(
            f"| {row['comparison']} | {row['old_correct']}/{row['n']} ({row['old_rate']:.2%}) "
            f"| {row['new_correct']}/{row['n']} ({row['new_rate']:.2%}) | {row['delta_rate']:+.2%} "
            f"| {row['b']} | {row['c']} | {p_value} |"
        )
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "unified_a1_a5_results.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
