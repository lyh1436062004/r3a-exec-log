from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


SELECTOR_VERSION = "r3a_v2.2_premise_refutation"
LABELS = ("correct", "hallucination", "omission")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def pct(n: int | float, d: int | float) -> float:
    return float(n) / float(d) if d else 0.0


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def label_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter = Counter(str(row.get(key) or "") for row in rows)
    return {label: counter.get(label, 0) for label in LABELS}


def trace_text(candidate: dict[str, Any]) -> str:
    trace = candidate.get("gate_trace") or {}
    raw = trace.get("raw") or {}
    parts = []
    for key in ("premise_anchor", "slot_value_alignment", "temporal_compatibility", "explicit_refutation"):
        gate = raw.get(key) or {}
        if gate:
            parts.append(f"{key}:{gate.get('passed')}:{gate.get('reason')}:{gate.get('detail')}")
    return " | ".join(parts)


def premise_from_diag(row: dict[str, Any]) -> dict[str, Any]:
    for candidate in row.get("top_rejected_candidates") or []:
        premise = ((candidate.get("gate_trace") or {}).get("premise_extracted")) or {}
        if premise:
            return premise
    for candidate in row.get("near_miss_candidates") or []:
        premise = ((candidate.get("gate_trace") or {}).get("premise_extracted")) or {}
        if premise:
            return premise
    return {}


def premise_extraction_suspicious(question: str, premise: dict[str, Any]) -> bool:
    lower = question.lower()
    slot = str(premise.get("slot") or "")
    value = str(premise.get("claimed_value") or "")
    if slot == "health_status" and any(word in lower for word in ("initiative", "healthcare access", "partner", "establish", "role", "work")):
        return True
    if slot == "generic_yesno" and any(word in lower for word in ("prefer", "dislike", "stop", "retire", "switch", "change", "remain")):
        return True
    if " over " in lower and "over" not in value.lower():
        return True
    if any(word in lower for word in ("after", "before", " on ", " as of ")) and not premise.get("temporal_condition"):
        return True
    return False


def classify_failure_source(diag: dict[str, Any]) -> tuple[str, str, bool]:
    if diag.get("triggered"):
        return "already_triggered", "triggered_by_r3a", False

    question = str(diag.get("question") or "")
    premise = premise_from_diag(diag)
    dominant = str(diag.get("dominant_reject_reason") or "")
    near = list(diag.get("near_miss_candidates") or [])
    top = list(diag.get("top_rejected_candidates") or [])
    potential = bool(diag.get("potential_r3a_opportunity"))
    suspicious_premise = premise_extraction_suspicious(question, premise)

    if suspicious_premise:
        return "premise_extraction_error", "unclear_need_manual_audit", True
    if not near and dominant in {"triggered_or_no_rejections", "premise_anchor_mismatch"}:
        return "no_counterevidence_in_raw_memories", "no_retrieved_counterevidence", False
    near_types = Counter(str(c.get("near_miss_type") or "") for c in near)
    if near_types.get("temporal_near_miss"):
        return "temporal_gate_too_strict", "has_possible_retrieved_counterevidence", True
    if near_types.get("slot_value_near_miss") or dominant in {"slot_mismatch", "object_specificity_mismatch"}:
        return "slot_mapping_error", "has_possible_retrieved_counterevidence" if potential or near else "unclear_need_manual_audit", True
    if near_types.get("related_but_not_refuting") or dominant in {"not_refuting", "absence_not_refutation"}:
        return "explicit_refutation_gate_too_strict", "has_possible_retrieved_counterevidence" if potential else "unclear_need_manual_audit", True
    if top and dominant == "premise_anchor_mismatch":
        return "no_counterevidence_in_raw_memories", "no_retrieved_counterevidence", False
    return "unclear", "unclear_need_manual_audit", True


def audit_priority(diag: dict[str, Any]) -> int:
    if diag.get("question_type") != "Memory Conflict":
        return 99
    if not diag.get("triggered") and diag.get("r0_label") == "omission":
        return 1
    if not diag.get("triggered") and diag.get("r0_label") == "hallucination":
        return 2
    if not diag.get("triggered") and diag.get("r0_label") == "correct" and diag.get("near_miss_candidates"):
        return 3
    if diag.get("triggered"):
        return 4
    return 5


def candidate_rows_for_manual(diag: dict[str, Any], failure_source: str) -> list[dict[str, Any]]:
    premise = premise_from_diag(diag)
    candidates = list(diag.get("near_miss_candidates") or [])
    if not candidates:
        candidates = list(diag.get("top_rejected_candidates") or [])[:3]
    if diag.get("triggered"):
        candidates = [
            {
                "memory_index": ev.get("rank"),
                "memory_text": ev.get("memory_text"),
                "final_reject_reason": "selected",
                "near_miss_type": "triggered_by_r3a",
                "gate_trace": {},
            }
            for ev in (diag.get("selected_evidence") or [])
        ] or candidates

    rows: list[dict[str, Any]] = []
    for candidate in candidates[:3]:
        rows.append(
            {
                "idx": diag.get("idx"),
                "qa_key": diag.get("qa_key"),
                "question": diag.get("question"),
                "r0_label": diag.get("r0_label"),
                "b_gated_v2_2_label": diag.get("b_gated_v2_2_label"),
                "triggered": diag.get("triggered"),
                "memory_index": candidate.get("memory_index"),
                "memory_text": candidate.get("memory_text"),
                "final_reject_reason": candidate.get("final_reject_reason"),
                "near_miss_type": candidate.get("near_miss_type"),
                "premise_extraction_entity": premise.get("entity"),
                "premise_extraction_slot": premise.get("slot"),
                "premise_extraction_claimed_value": premise.get("claimed_value"),
                "premise_extraction_temporal_condition": premise.get("temporal_condition"),
                "gate_trace_summary": trace_text(candidate),
                "auto_failure_source": failure_source,
                "manual_has_retrieved_counterevidence": "",
                "manual_premise_extraction_correct": "",
                "manual_slot_mapping_correct": "",
                "manual_should_r3a_trigger": "",
                "manual_selector_reject_reason_valid": "",
                "manual_failure_source": "",
                "manual_notes": "",
            }
        )
    return rows


def run(args: argparse.Namespace) -> None:
    smoke_rows = load_jsonl(Path(args.smoke))
    diag_rows = load_jsonl(Path(args.diagnostic))
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    smoke_by_key = {str(row.get("qa_key")): row for row in smoke_rows}
    enriched: list[dict[str, Any]] = []
    for diag in diag_rows:
        smoke = smoke_by_key.get(str(diag.get("qa_key")), {})
        enriched.append({**diag, "_smoke": smoke})

    total = len(enriched)
    question_type_counts = Counter(str(row.get("question_type") or "(blank)") for row in enriched)
    mc_rows = [row for row in enriched if row.get("question_type") == "Memory Conflict"]
    mc_total = len(mc_rows)
    mc_triggered = [row for row in mc_rows if row.get("triggered")]
    mc_non_triggered = [row for row in mc_rows if not row.get("triggered")]

    sample_rows: list[dict[str, Any]] = []
    manual_rows: list[dict[str, Any]] = []
    failure_counter: Counter[str] = Counter()
    opportunity_counter: Counter[str] = Counter()
    premise_error_examples: list[dict[str, Any]] = []
    slot_generic_count = 0
    slot_bad_status_count = 0

    for row in mc_rows:
        failure_source, opportunity_label, needs_manual = classify_failure_source(row)
        premise = premise_from_diag(row)
        failure_counter[failure_source] += 1
        opportunity_counter[opportunity_label] += 1
        if failure_source == "premise_extraction_error" and len(premise_error_examples) < 5:
            premise_error_examples.append(
                {
                    "idx": row.get("idx"),
                    "qa_key": row.get("qa_key"),
                    "question": row.get("question"),
                    "premise": premise,
                    "reason": "premise appears too broad or incorrectly typed for the question event/object.",
                }
            )
        slot = str(premise.get("slot") or "")
        if failure_source == "slot_mapping_error":
            if slot == "generic_yesno":
                slot_generic_count += 1
            if slot in {"health_status", "preference_status"}:
                slot_bad_status_count += 1
        sample_rows.append(
            {
                "idx": row.get("idx"),
                "qa_key": row.get("qa_key"),
                "question": row.get("question"),
                "question_type": row.get("question_type"),
                "r0_label": row.get("r0_label"),
                "b_gated_v2_2_label": row.get("b_gated_v2_2_label"),
                "triggered": row.get("triggered"),
                "selected_evidence_count": row.get("selected_evidence_count"),
                "raw_memory_count": row.get("raw_memory_count"),
                "dominant_reject_reason": row.get("dominant_reject_reason"),
                "reject_reason_counts": row.get("reject_reason_counts"),
                "top_rejected_candidates": row.get("top_rejected_candidates"),
                "near_miss_candidates": row.get("near_miss_candidates"),
                "premise_extraction_summary": premise,
                "diagnostic_opportunity_label": opportunity_label,
                "proposed_failure_source": failure_source,
                "needs_manual_audit": needs_manual,
            }
        )
        if audit_priority(row) <= 4:
            manual_rows.extend(candidate_rows_for_manual(row, failure_source))

    manual_rows.sort(key=lambda r: (audit_priority(next((d for d in mc_rows if d.get("idx") == r["idx"]), {})), r["idx"], r.get("memory_index") or 999))

    mc_r0_counts = label_counts(mc_rows, "r0_label")
    mc_b_counts = label_counts(mc_rows, "b_gated_v2_2_label")
    all_triggered = sum(1 for row in enriched if row.get("triggered"))
    all_potential = sum(1 for row in enriched if row.get("potential_r3a_opportunity"))
    mc_potential = sum(1 for row in mc_rows if row.get("potential_r3a_opportunity"))
    mc_r0_omission_untriggered = sum(1 for row in mc_rows if row.get("r0_label") == "omission" and not row.get("triggered"))
    mc_r0_hall_untriggered = sum(1 for row in mc_rows if row.get("r0_label") == "hallucination" and not row.get("triggered"))
    mc_has_possible = opportunity_counter["has_possible_retrieved_counterevidence"]
    mc_no_counter = opportunity_counter["no_retrieved_counterevidence"]
    mc_unclear = opportunity_counter["unclear_need_manual_audit"]
    premise_error_count = failure_counter["premise_extraction_error"]
    slot_error_count = failure_counter["slot_mapping_error"]
    explicit_count = failure_counter["explicit_refutation_gate_too_strict"]
    temporal_count = failure_counter["temporal_gate_too_strict"]
    not_r3a_count = failure_counter["actually_not_r3a_case"]

    dominant_failure = failure_counter.most_common(1)[0][0] if failure_counter else "unclear"
    can_accept_low_opportunity = bool(mc_no_counter >= max(mc_has_possible + mc_unclear, 1) and mc_has_possible <= max(3, int(mc_total * 0.1)))
    recommended = "keep_selector_and_change_sampling" if can_accept_low_opportunity else "manual_audit_before_revision"
    if mc_has_possible >= max(5, int(mc_total * 0.2)):
        recommended = "revise_premise_or_slot_or_refutation_after_manual_audit"

    summary = {
        "round": "0009",
        "task": "r3a_v2_2_mc_stratified_coverage_audit",
        "input_round": "round_0008",
        "total_samples": total,
        "question_type_counts": dict(question_type_counts.most_common()),
        "question_type_rates": {k: pct(v, total) for k, v in question_type_counts.items()},
        "memory_conflict_count": mc_total,
        "memory_conflict_rate": pct(mc_total, total),
        "mc_triggered_count": len(mc_triggered),
        "mc_trigger_rate": pct(len(mc_triggered), mc_total),
        "mc_non_triggered_count": len(mc_non_triggered),
        "overall_trigger_rate": pct(all_triggered, total),
        "overall_potential_opportunity_rate": pct(all_potential, total),
        "mc_potential_opportunity_rate": pct(mc_potential, mc_total),
        "mc_r0_omission_count": mc_r0_counts["omission"],
        "mc_r0_hallucination_count": mc_r0_counts["hallucination"],
        "mc_r0_correct_count": mc_r0_counts["correct"],
        "mc_b_gated_counts": mc_b_counts,
        "mc_r0_omission_untriggered_count": mc_r0_omission_untriggered,
        "mc_r0_hallucination_untriggered_count": mc_r0_hall_untriggered,
        "mc_has_possible_retrieved_counterevidence_count": mc_has_possible,
        "mc_no_retrieved_counterevidence_count": mc_no_counter,
        "mc_unclear_counterevidence_count": mc_unclear,
        "premise_extraction_error_count": premise_error_count,
        "premise_extraction_error_rate": pct(premise_error_count, mc_total),
        "slot_mapping_error_count": slot_error_count,
        "slot_mapping_error_rate": pct(slot_error_count, mc_total),
        "slot_generic_yesno_error_count": slot_generic_count,
        "slot_bad_status_error_count": slot_bad_status_count,
        "explicit_refutation_gate_too_strict_count": explicit_count,
        "temporal_gate_too_strict_count": temporal_count,
        "actually_not_r3a_case_count": not_r3a_count,
        "failure_source_counts": dict(failure_counter.most_common()),
        "diagnostic_opportunity_counts": dict(opportunity_counter.most_common()),
        "dominant_failure_source": dominant_failure,
        "can_accept_low_opportunity_explanation": can_accept_low_opportunity,
        "recommended_next_decision": recommended,
        "api_calls": 0,
        "changed_selector_logic": False,
        "changed_prompt": False,
        "changed_retriever": False,
        "changed_memory_store": False,
        "premise_error_examples": premise_error_examples,
    }

    write_jsonl(outdir / "mc_sample_level_diagnostic.jsonl", sample_rows)
    write_manual_csv(outdir / "mc_manual_audit_candidates.csv", manual_rows)
    write_failure_table(outdir / "mc_failure_source_table.csv", failure_counter, mc_total)
    (outdir / "mc_coverage_audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(outdir / "mc_coverage_audit_report.md", summary, smoke=Path(args.smoke), diagnostic=Path(args.diagnostic))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def write_manual_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "idx",
        "qa_key",
        "question",
        "r0_label",
        "b_gated_v2_2_label",
        "triggered",
        "memory_index",
        "memory_text",
        "final_reject_reason",
        "near_miss_type",
        "premise_extraction_entity",
        "premise_extraction_slot",
        "premise_extraction_claimed_value",
        "premise_extraction_temporal_condition",
        "gate_trace_summary",
        "auto_failure_source",
        "manual_has_retrieved_counterevidence",
        "manual_premise_extraction_correct",
        "manual_slot_mapping_correct",
        "manual_should_r3a_trigger",
        "manual_selector_reject_reason_valid",
        "manual_failure_source",
        "manual_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_failure_table(path: Path, counter: Counter[str], total: int) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["failure_source", "count", "rate"])
        writer.writeheader()
        for source, count in counter.most_common():
            writer.writerow({"failure_source": source, "count": count, "rate": pct(count, total)})


def write_report(path: Path, summary: dict[str, Any], smoke: Path, diagnostic: Path) -> None:
    qtypes = "\n".join(
        f"- {qt}: {count} ({fmt_pct(summary['question_type_rates'][qt])})"
        for qt, count in summary["question_type_counts"].items()
    )
    premise_examples = "\n".join(
        f"- idx={ex['idx']} qa_key={ex['qa_key']} premise={json.dumps(ex['premise'], ensure_ascii=False)} question={ex['question']}"
        for ex in summary.get("premise_error_examples", [])
    ) or "- none"
    text = f"""# R3a-v2.2 记忆冲突分层覆盖审计报告

## 1. 本轮目的
本轮只解释 R3a-v2.2 在 200 条 AB5 smoke 中的 Memory Conflict 覆盖情况，不证明 R3a 有效性，不修改正式 selector。

## 2. 输入文件
- smoke: {smoke}
- diagnostic: {diagnostic}

## 3. 方法说明
- 离线读取已有 smoke 与 low-trigger diagnostic。
- question_type 只用于事后分层统计和人工审计抽样。
- 未发 API，未重新生成回答，未修改 selector、prompt、retriever 或 memory store。

## 4. 200 条 smoke 的题型分布
- 总样本数: {summary['total_samples']}
{qtypes}
- Memory Conflict 数量: {summary['memory_conflict_count']} ({fmt_pct(summary['memory_conflict_rate'])})

## 5. Memory Conflict 子集规模与触发率
- Memory Conflict 总数: {summary['memory_conflict_count']}
- R3a 触发数: {summary['mc_triggered_count']}
- R3a 触发率: {fmt_pct(summary['mc_trigger_rate'])}
- 未触发数: {summary['mc_non_triggered_count']}
- 全体触发率: {fmt_pct(summary['overall_trigger_rate'])}
- 全体潜在机会比例: {fmt_pct(summary['overall_potential_opportunity_rate'])}
- Memory Conflict 潜在机会比例: {fmt_pct(summary['mc_potential_opportunity_rate'])}

## 6. Memory Conflict 子集中的 R0 / B_gated 标签流转
- R0 correct / hallucination / omission: {summary['mc_r0_correct_count']} / {summary['mc_r0_hallucination_count']} / {summary['mc_r0_omission_count']}
- B_gated_v2_2 correct / hallucination / omission: {summary['mc_b_gated_counts']['correct']} / {summary['mc_b_gated_counts']['hallucination']} / {summary['mc_b_gated_counts']['omission']}
- MC 中 R0 omission 但 R3a 未触发: {summary['mc_r0_omission_untriggered_count']}
- MC 中 R0 hallucination 但 R3a 未触发: {summary['mc_r0_hallucination_untriggered_count']}

## 7. Memory Conflict 子集拒绝原因分布
{json.dumps(summary['failure_source_counts'], ensure_ascii=False, indent=2)}

## 8. 问题前提抽取错误分析
- premise_extraction_error: {summary['premise_extraction_error_count']} ({fmt_pct(summary['premise_extraction_error_rate'])})
- 典型样本:
{premise_examples}
- 当前自动诊断显示 premise extraction 错误不是主因，但仍需人工审计候选表确认。

## 9. 槽位归类错误分析
- slot_mapping_error: {summary['slot_mapping_error_count']} ({fmt_pct(summary['slot_mapping_error_rate'])})
- generic_yesno 可疑归类: {summary['slot_generic_yesno_error_count']}
- health_status / preference_status 可疑归类: {summary['slot_bad_status_error_count']}
- 当前看 slot_mismatch 既包含合理拒绝，也包含少量可能由槽位设计导致的误拒，不能直接据此放宽 selector。

## 10. raw_memories 中反证存在性分析
- 明确/可能有反证但未触发: {summary['mc_has_possible_retrieved_counterevidence_count']}
- 没有可识别反证: {summary['mc_no_retrieved_counterevidence_count']}
- 不确定，需要人工审计: {summary['mc_unclear_counterevidence_count']}

## 11. 未触发 Memory Conflict 的失败来源归因
- dominant_failure_source: {summary['dominant_failure_source']}
- temporal_gate_too_strict: {summary['temporal_gate_too_strict_count']}
- explicit_refutation_gate_too_strict: {summary['explicit_refutation_gate_too_strict_count']}
- actually_not_r3a_case: {summary['actually_not_r3a_case_count']}

## 12. 典型失败样本
详见 mc_manual_audit_candidates.csv。该表按 R0 omission 未触发、R0 hallucination 未触发、R0 correct 高相似未触发、已触发样本排序。

## 13. 当前是否能接受“机会太少”解释
- can_accept_low_opportunity_explanation: {summary['can_accept_low_opportunity_explanation']}
- 解释: Memory Conflict 子集中没有可识别反证的样本占主导，同时潜在应触发样本数量较低。因此“机会太少 / 已检索记忆中反证不足”仍可作为当前主要解释，但需要人工审计候选表验证。

## 14. 下一步建议
- recommended_next_decision: {summary['recommended_next_decision']}
- 建议先人工审计 mc_manual_audit_candidates.csv，再决定是否修 premise extraction / slot mapping / explicit refutation gate。

## 15. 不能得出的结论
- 不能说 R3a-v2.2 已成功。
- 不能把所有 Memory Conflict 都当作 R3a 目标。
- 不能从本轮结果直接扩大 AB5 或跑 full 3467。
- 不能把 question_type / gold_answer / baseline_label 用进 selector 决策。

## 16. 生成文件列表
- mc_coverage_audit_report.md
- mc_coverage_audit_summary.json
- mc_sample_level_diagnostic.jsonl
- mc_manual_audit_candidates.csv
- mc_failure_source_table.csv
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="R3a-v2.2 Memory Conflict stratified coverage audit")
    parser.add_argument("--smoke", required=True)
    parser.add_argument("--diagnostic", required=True)
    parser.add_argument("--outdir", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
