from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from typing import Any

from e1_memos_oracle_common import CONDITIONS, OUT_DIR, load_samples, read_jsonl, write_csv, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    return parser.parse_args()


def load_verdicts() -> dict[str, dict[str, dict[str, Any]]]:
    verdicts: dict[str, dict[str, dict[str, Any]]] = {}
    for condition in CONDITIONS:
        rows = [row for row in read_jsonl(OUT_DIR / "verdicts" / f"{condition}.jsonl") if row.get("ok")]
        verdicts[condition] = {str(row["case_id"]): row for row in rows}
    return verdicts


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar_p(b: int, c: int) -> float | None:
    total = b + c
    if total == 0:
        return None
    try:
        from scipy.stats import binomtest  # type: ignore

        return float(binomtest(min(b, c), total, 0.5).pvalue)
    except Exception:  # noqa: BLE001
        prob = sum(math.comb(total, i) for i in range(0, min(b, c) + 1)) * (0.5**total)
        return min(1.0, 2 * prob)


def label(verdicts: dict[str, dict[str, dict[str, Any]]], condition: str, case_id: str) -> str | None:
    row = verdicts.get(condition, {}).get(case_id)
    return str(row.get("judge_label")) if row else None


def rate_rows(pool_name: str, case_ids: list[str], verdicts: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for condition in ["A1", "A2", "A3", "A4", "A5"]:
        labels = [label(verdicts, condition, case_id) for case_id in case_ids]
        labels = [item for item in labels if item]
        correct = sum(1 for item in labels if item == "correct")
        lo, hi = wilson(correct, len(labels))
        rows.append(
            {
                "pool": pool_name,
                "condition": condition,
                "n": len(labels),
                "correct": correct,
                "flip_rate": correct / len(labels) if labels else 0.0,
                "wilson_low": lo,
                "wilson_high": hi,
            }
        )
    return rows


def transitions(
    pool_name: str,
    case_ids: list[str],
    verdicts: dict[str, dict[str, dict[str, Any]]],
    condition: str,
) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for case_id in case_ids:
        a0 = label(verdicts, "A0", case_id)
        x = label(verdicts, condition, case_id)
        if a0 and x:
            counts[(a0, x)] += 1
    total_by_from = Counter()
    for (src, _dst), count in counts.items():
        total_by_from[src] += count
    rows = []
    for src in ["hallucination", "omission", "correct"]:
        for dst in ["correct", "hallucination", "omission"]:
            count = counts[(src, dst)]
            denom = total_by_from[src]
            rows.append(
                {
                    "pool": pool_name,
                    "condition": condition,
                    "from_label": src,
                    "to_label": dst,
                    "count": count,
                    "rate_within_from": count / denom if denom else 0.0,
                }
            )
    return rows


def paired_rows(pool_name: str, case_ids: list[str], verdicts: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    pairs = [("A3", "A1"), ("A3", "A2"), ("A4", "A0"), ("A5", "A0"), ("A5", "A4"), ("A5", "A2")]
    rows = []
    for left, right in pairs:
        b = 0
        c = 0
        both = 0
        for case_id in case_ids:
            l = label(verdicts, left, case_id)
            r = label(verdicts, right, case_id)
            if not l or not r:
                continue
            both += 1
            l_ok = l == "correct"
            r_ok = r == "correct"
            if l_ok and not r_ok:
                b += 1
            elif r_ok and not l_ok:
                c += 1
        rows.append({"pool": pool_name, "comparison": f"{left}_vs_{right}", "n": both, "b": b, "c": c, "p_value": exact_mcnemar_p(b, c)})
    return rows


def group_rate(samples_by_case: dict[str, dict[str, Any]], case_ids: list[str], verdicts: dict[str, dict[str, dict[str, Any]]], field: str) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for case_id in case_ids:
        grouped[str(samples_by_case[case_id].get(field))].append(case_id)
    rows = []
    for value, ids in sorted(grouped.items()):
        for condition in ["A1", "A2", "A3", "A4", "A5"]:
            labels = [label(verdicts, condition, case_id) for case_id in ids]
            labels = [item for item in labels if item]
            correct = sum(1 for item in labels if item == "correct")
            rows.append(
                {
                    field: value,
                    "condition": condition,
                    "n": len(labels),
                    "correct": correct,
                    "flip_rate": correct / len(labels) if labels else 0.0,
                }
            )
    return rows


def main() -> None:
    args = parse_args()
    samples = load_samples()
    samples_by_case = {str(row["case_id"]): row for row in samples}
    verdicts = load_verdicts()
    missing = {
        condition: len(samples) - len(verdicts.get(condition, {}))
        for condition in CONDITIONS
    }
    if args.require_complete and any(value != 0 for value in missing.values()):
        raise RuntimeError(f"Missing verdicts: {missing}")

    a0_case_ids = [case_id for case_id in samples_by_case if label(verdicts, "A0", case_id)]
    stable_wrong = [case_id for case_id in a0_case_ids if label(verdicts, "A0", case_id) != "correct"]
    retrieved_strict = [
        case_id
        for case_id in stable_wrong
        if samples_by_case[case_id].get("retrieval_stratum") == "strict_supported"
    ]
    # E1' 主分析口径:gold 证据真正进入了 LLM 上下文的样本(763 口径)
    visible_supported = [
        case_id
        for case_id in stable_wrong
        if samples_by_case[case_id].get("visible_stratum") == "visible_supported"
    ]
    serialization_loss = [
        case_id
        for case_id in stable_wrong
        if samples_by_case[case_id].get("visible_stratum") == "serialization_loss"
    ]

    a0_noncorrect_rate = len(stable_wrong) / len(samples) if samples else 0.0
    unstable = a0_noncorrect_rate < 0.85

    rate_table = (
        rate_rows("full_pool", stable_wrong, verdicts)
        + rate_rows("retrieved_strict", retrieved_strict, verdicts)
        + rate_rows("visible_supported", visible_supported, verdicts)
        + rate_rows("serialization_loss", serialization_loss, verdicts)
    )
    write_csv(
        OUT_DIR / "flip_rates.csv",
        rate_table,
        ["pool", "condition", "n", "correct", "flip_rate", "wilson_low", "wilson_high"],
    )

    transition_rows = []
    strict_transition_rows = []
    visible_transition_rows = []
    for condition in ["A1", "A2", "A3", "A4", "A5"]:
        transition_rows.extend(transitions("full_pool", stable_wrong, verdicts, condition))
        strict_transition_rows.extend(transitions("retrieved_strict", retrieved_strict, verdicts, condition))
        visible_transition_rows.extend(transitions("visible_supported", visible_supported, verdicts, condition))
    fields = ["pool", "condition", "from_label", "to_label", "count", "rate_within_from"]
    write_csv(OUT_DIR / "transitions_full_pool.csv", transition_rows, fields)
    write_csv(OUT_DIR / "transitions_retrieved_strict.csv", strict_transition_rows, fields)
    write_csv(OUT_DIR / "transitions_visible_supported.csv", visible_transition_rows, fields)

    mcnemar = (
        paired_rows("full_pool", stable_wrong, verdicts)
        + paired_rows("retrieved_strict", retrieved_strict, verdicts)
        + paired_rows("visible_supported", visible_supported, verdicts)
    )
    write_csv(OUT_DIR / "mcnemar.csv", mcnemar, ["pool", "comparison", "n", "b", "c", "p_value"])

    rates = {(row["pool"], row["condition"]): row["flip_rate"] for row in rate_table}
    waterfall_rows = []
    for pool in ["full_pool", "retrieved_strict", "visible_supported"]:
        waterfall_rows.extend(
            [
                {"pool": pool, "component": "position_A1", "value": rates.get((pool, "A1"), 0.0)},
                {"pool": pool, "component": "filter_A2_minus_A1", "value": rates.get((pool, "A2"), 0.0) - rates.get((pool, "A1"), 0.0)},
                {"pool": pool, "component": "license_A3_minus_A2", "value": rates.get((pool, "A3"), 0.0) - rates.get((pool, "A2"), 0.0)},
                {"pool": pool, "component": "license_only_A4_minus_A0", "value": rates.get((pool, "A4"), 0.0)},
                {"pool": pool, "component": "vouch_all_A5_minus_A0", "value": rates.get((pool, "A5"), 0.0)},
                {"pool": pool, "component": "vouch_increment_A5_minus_A4", "value": rates.get((pool, "A5"), 0.0) - rates.get((pool, "A4"), 0.0)},
            ]
        )
    write_csv(OUT_DIR / "waterfall_full_pool.csv", [row for row in waterfall_rows if row["pool"] == "full_pool"], ["pool", "component", "value"])
    write_csv(OUT_DIR / "waterfall_retrieved_strict.csv", [row for row in waterfall_rows if row["pool"] == "retrieved_strict"], ["pool", "component", "value"])
    write_csv(OUT_DIR / "waterfall_visible_supported.csv", [row for row in waterfall_rows if row["pool"] == "visible_supported"], ["pool", "component", "value"])

    write_csv(OUT_DIR / "by_dataset.csv", group_rate(samples_by_case, stable_wrong, verdicts, "dataset"), ["dataset", "condition", "n", "correct", "flip_rate"])
    write_csv(OUT_DIR / "by_question_type.csv", group_rate(samples_by_case, stable_wrong, verdicts, "question_type"), ["question_type", "condition", "n", "correct", "flip_rate"])
    write_csv(OUT_DIR / "by_retrieval_stratum.csv", group_rate(samples_by_case, stable_wrong, verdicts, "retrieval_stratum"), ["retrieval_stratum", "condition", "n", "correct", "flip_rate"])
    write_csv(OUT_DIR / "by_visible_stratum.csv", group_rate(samples_by_case, stable_wrong, verdicts, "visible_stratum"), ["visible_stratum", "condition", "n", "correct", "flip_rate"])
    write_csv(OUT_DIR / "by_baseline_label.csv", group_rate(samples_by_case, stable_wrong, verdicts, "baseline_label"), ["baseline_label", "condition", "n", "correct", "flip_rate"])
    write_csv(OUT_DIR / "by_semantic_any_contradicted.csv", group_rate(samples_by_case, stable_wrong, verdicts, "semantic_any_contradicted"), ["semantic_any_contradicted", "condition", "n", "correct", "flip_rate"])

    summary = {
        "sample_count": len(samples),
        "missing_verdicts": missing,
        "a0_judged": len(a0_case_ids),
        "stable_wrong": len(stable_wrong),
        "retrieved_strict": len(retrieved_strict),
        "visible_supported": len(visible_supported),
        "serialization_loss": len(serialization_loss),
        "a0_replay_noncorrect_rate": a0_noncorrect_rate,
        "replay_unstable": unstable,
        "flip_rates": rate_table,
        "mcnemar": mcnemar,
    }
    write_json(OUT_DIR / "results_summary.json", summary)

    lines = [
        "# E1 Memos Full Oracle Results",
        "",
        f"- samples: {len(samples)}",
        f"- A0 judged: {len(a0_case_ids)}",
        f"- stable_wrong: {len(stable_wrong)}",
        f"- retrieved_strict stable_wrong: {len(retrieved_strict)}",
        f"- visible_supported stable_wrong: {len(visible_supported)}",
        f"- serialization_loss stable_wrong: {len(serialization_loss)}",
        f"- A0 replay non-correct rate: {a0_noncorrect_rate:.2%}",
        f"- replay unstable: {unstable}",
        "",
        "## Flip Rates",
        "",
        "| pool | condition | n | correct | flip_rate | Wilson 95% CI |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in rate_table:
        lines.append(
            f"| {row['pool']} | {row['condition']} | {row['n']} | {row['correct']} | {row['flip_rate']:.2%} | [{row['wilson_low']:.2%}, {row['wilson_high']:.2%}] |"
        )
    lines.extend(["", "## McNemar", "", "| pool | comparison | n | b | c | p_value |", "|---|---|---:|---:|---:|---:|"])
    for row in mcnemar:
        p = "" if row["p_value"] is None else f"{row['p_value']:.6g}"
        lines.append(f"| {row['pool']} | {row['comparison']} | {row['n']} | {row['b']} | {row['c']} | {p} |")
    (OUT_DIR / "results_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote analysis to {OUT_DIR / 'results_summary.md'}")


if __name__ == "__main__":
    main()
