from __future__ import annotations

import json
from collections import Counter
from typing import Any

from e1_memos_oracle_common import OUT_DIR, build_context, ids_for_raw, load_samples, memory_text, write_json


def main() -> None:
    samples = load_samples()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()

    for sample in samples:
        raw = list(sample.get("raw_memories") or [])
        raw_ids = ids_for_raw(raw)
        admitted_ids = [mid for mid, item in zip(raw_ids, raw) if memory_text(item)]
        dropped_ids = [mid for mid in raw_ids if mid not in set(admitted_ids)]
        gold_ids = [mid for mid in sample.get("gold_memory_ids") or [] if mid in set(raw_ids)]
        gold_admitted = [mid for mid in gold_ids if mid in set(admitted_ids)]

        a6_context, a6_meta = build_context(sample, "A6")
        a7_context, a7_meta = build_context(sample, "A7")
        errors: list[str] = []
        if dropped_ids:
            errors.append("raw_memory_not_canonicalized")
        if a6_meta.get("admitted_memory_ids") != admitted_ids:
            errors.append("a6_admitted_ids_mismatch")
        if a7_meta.get("admitted_memory_ids") != admitted_ids:
            errors.append("a7_admitted_ids_mismatch")
        if a6_meta.get("admitted_memory_ids") != a7_meta.get("admitted_memory_ids"):
            errors.append("a6_a7_memory_set_or_order_mismatch")
        if sample.get("retrieval_stratum") == "strict_supported" and set(gold_admitted) != set(gold_ids):
            errors.append("strict_gold_memory_not_admitted")
        if int(a7_meta.get("license_counts", {}).get("UNIFIED", 0)) != len(gold_ids):
            errors.append("unified_license_count_mismatch")
        if a6_meta.get("license_counts", {}).get("UNIFIED"):
            errors.append("a6_contains_unified_license")
        if a6_meta.get("leakage_errors") or a7_meta.get("leakage_errors"):
            errors.append("license_leakage")
        if not a6_context or not a7_context:
            errors.append("empty_context")

        totals["samples"] += 1
        totals["raw_memories"] += len(raw_ids)
        totals["admitted_memories"] += len(admitted_ids)
        totals["dropped_memories"] += len(dropped_ids)
        totals["gold_memory_ids"] += len(gold_ids)
        totals["gold_admitted_ids"] += len(gold_admitted)
        if sample.get("retrieval_stratum") == "strict_supported":
            totals["strict_samples"] += 1
            totals["strict_gold_memory_ids"] += len(gold_ids)
            totals["strict_gold_admitted_ids"] += len(gold_admitted)
        if errors:
            totals["failed_samples"] += 1
            failures.append({"case_id": sample["case_id"], "errors": errors, "dropped_ids": dropped_ids})

        rows.append(
            {
                "case_id": sample["case_id"],
                "retrieval_stratum": sample.get("retrieval_stratum"),
                "visible_stratum": sample.get("visible_stratum"),
                "n_raw": len(raw_ids),
                "n_admitted": len(admitted_ids),
                "dropped_ids": dropped_ids,
                "gold_memory_ids": gold_ids,
                "gold_admitted_ids": gold_admitted,
                "a6_context_hash": a6_meta["context_hash"],
                "a7_context_hash": a7_meta["context_hash"],
                "errors": errors,
            }
        )

    out_path = OUT_DIR / "unified_admission.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = dict(totals)
    summary["raw_admission_rate"] = totals["admitted_memories"] / totals["raw_memories"] if totals["raw_memories"] else 0.0
    summary["strict_gold_admission_rate"] = (
        totals["strict_gold_admitted_ids"] / totals["strict_gold_memory_ids"]
        if totals["strict_gold_memory_ids"]
        else 0.0
    )
    write_json(OUT_DIR / "unified_admission_summary.json", summary)

    report = [
        "# Unified Post-Retrieval Admission Verification",
        "",
        f"- Samples: {totals['samples']}",
        f"- Raw memories: {totals['raw_memories']}",
        f"- Canonically admitted memories: {totals['admitted_memories']}",
        f"- Dropped memories: {totals['dropped_memories']}",
        f"- Raw admission rate: {summary['raw_admission_rate']:.2%}",
        f"- Strict samples: {totals['strict_samples']}",
        f"- Strict oracle gold ids: {totals['strict_gold_memory_ids']}",
        f"- Strict oracle gold ids admitted: {totals['strict_gold_admitted_ids']}",
        f"- Strict gold admission rate: {summary['strict_gold_admission_rate']:.2%}",
        f"- Failed samples: {totals['failed_samples']}",
    ]
    (OUT_DIR / "unified_admission_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\n".join(report[2:]))
    if failures:
        raise SystemExit(f"unified admission verification failed for {len(failures)} samples")


if __name__ == "__main__":
    main()
