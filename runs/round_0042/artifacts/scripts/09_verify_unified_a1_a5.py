from __future__ import annotations

from collections import Counter
from typing import Any

from e1_memos_oracle_common import (
    OUT_DIR,
    UNIFIED_A_CONDITIONS,
    build_context,
    ids_for_raw,
    load_samples,
    write_json,
)


def main() -> None:
    samples = load_samples()
    failures: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    condition_counts: dict[str, Counter[str]] = {condition: Counter() for condition in UNIFIED_A_CONDITIONS}

    for sample in samples:
        if sample.get("retrieval_stratum") != "strict_supported":
            continue
        raw_ids = ids_for_raw(list(sample.get("raw_memories") or []))
        gold_ids = [mid for mid in sample.get("gold_memory_ids") or [] if mid in set(raw_ids)]
        expected = {
            "UA1": gold_ids + [mid for mid in raw_ids if mid not in set(gold_ids)],
            "UA2": gold_ids,
            "UA3": gold_ids,
            "UA4": raw_ids,
            "UA5": raw_ids,
        }
        case_errors: list[str] = []
        contexts: dict[str, str] = {}
        metas: dict[str, dict[str, Any]] = {}
        for condition in UNIFIED_A_CONDITIONS:
            context, meta = build_context(sample, condition)
            contexts[condition] = context
            metas[condition] = meta
            admitted = list(meta.get("admitted_memory_ids") or [])
            if admitted != expected[condition]:
                case_errors.append(f"{condition}:admitted_ids_mismatch")
            if meta.get("leakage_errors"):
                case_errors.append(f"{condition}:license_leakage")
            condition_counts[condition]["samples"] += 1
            condition_counts[condition]["admitted"] += len(admitted)
            condition_counts[condition]["gold_admitted"] += len(meta.get("gold_admitted_ids") or [])

        if contexts["UA2"] != contexts["UA3"] and not any(
            metas["UA3"].get("license_counts", {}).get(name, 0)
            for name in ("REFUTE", "SELECT", "CONDITION")
        ):
            case_errors.append("UA2_UA3_unexplained_context_difference")
        if metas["UA4"].get("admitted_memory_ids") != metas["UA5"].get("admitted_memory_ids"):
            case_errors.append("UA4_UA5_memory_set_or_order_difference")
        if metas["UA1"].get("n_admitted_memories") != metas["UA4"].get("n_admitted_memories"):
            case_errors.append("UA1_UA4_admission_count_difference")

        totals["samples"] += 1
        totals["raw_memories"] += len(raw_ids)
        totals["gold_memories"] += len(gold_ids)
        if case_errors:
            failures.append({"case_id": sample.get("case_id"), "errors": sorted(set(case_errors))})

    summary = {
        "scope": "all strict_supported samples before A0-correct exclusion",
        "totals": dict(totals),
        "conditions": {condition: dict(counts) for condition, counts in condition_counts.items()},
        "failure_count": len(failures),
        "failures": failures,
    }
    write_json(OUT_DIR / "unified_a1_a5_preflight.json", summary)
    lines = [
        "# Unified A1-A5 Preflight",
        "",
        f"- strict samples: {totals['samples']}",
        f"- raw memories: {totals['raw_memories']}",
        f"- strict gold memories: {totals['gold_memories']}",
        f"- failures: {len(failures)}",
        "",
        "| condition | samples | admitted | gold admitted |",
        "|---|---:|---:|---:|",
    ]
    for condition in UNIFIED_A_CONDITIONS:
        counts = condition_counts[condition]
        lines.append(
            f"| {condition} | {counts['samples']} | {counts['admitted']} | {counts['gold_admitted']} |"
        )
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "unified_a1_a5_preflight.md").write_text(report, encoding="utf-8")
    print(report)
    if failures:
        raise SystemExit(f"unified A1-A5 preflight failed for {len(failures)} samples")


if __name__ == "__main__":
    main()
