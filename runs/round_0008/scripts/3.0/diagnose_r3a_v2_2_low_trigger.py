from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LABELS = ("correct", "hallucination", "omission")
SELECTOR_VERSION = "r3a_v2.2_premise_refutation"


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


def gate_passed(gate_trace: dict[str, Any], key: str) -> bool:
    value = gate_trace.get(key) or {}
    return bool(value.get("passed"))


def gate_trace_summary(gate_trace: dict[str, Any]) -> dict[str, Any]:
    return {
        "premise_anchor_match": gate_passed(gate_trace, "premise_anchor"),
        "slot_value_alignment": gate_passed(gate_trace, "slot_value_alignment"),
        "temporal_compatible": gate_passed(gate_trace, "temporal_compatibility"),
        "explicit_refutation": gate_passed(gate_trace, "explicit_refutation"),
        "raw": gate_trace,
    }


def near_miss_score(rejection: dict[str, Any]) -> int:
    trace = rejection.get("gate_trace") or {}
    score = 0
    if gate_passed(trace, "premise_anchor"):
        score += 3
    if gate_passed(trace, "slot_value_alignment"):
        score += 3
    if gate_passed(trace, "temporal_compatibility"):
        score += 2
    reason = rejection.get("reject_reason")
    if reason in {"not_refuting", "absence_not_refutation"}:
        score += 1
    if reason in {"object_specificity_mismatch", "temporal_mismatch"}:
        score += 1
    return score


def near_miss_type(rejection: dict[str, Any]) -> str:
    reason = rejection.get("reject_reason") or ""
    trace = rejection.get("gate_trace") or {}
    if reason == "premise_anchor_mismatch":
        return "premise_anchor_near_miss" if near_miss_score(rejection) >= 2 else "no_candidate_overlap"
    if reason in {"slot_mismatch", "object_specificity_mismatch"}:
        return "slot_value_near_miss"
    if reason == "temporal_mismatch":
        return "temporal_near_miss"
    if reason == "absence_not_refutation":
        return "absence_not_refutation"
    if reason == "not_refuting":
        return "related_but_not_refuting"
    if gate_passed(trace, "premise_anchor") and gate_passed(trace, "slot_value_alignment"):
        return "possible_true_counterevidence_rejected"
    return "diagnostic_inconclusive"


def diagnostic_category(row: dict[str, Any], top_rejections: list[dict[str, Any]]) -> str:
    if row.get("a2_gate"):
        return "triggered"
    if not top_rejections:
        return "no_candidate_overlap"
    ranked = sorted(top_rejections, key=lambda r: (near_miss_score(r), -int(r.get("rank") or 999)), reverse=True)
    top_type = near_miss_type(ranked[0])
    if top_type == "no_candidate_overlap":
        qtype = str(row.get("question_type") or "")
        if qtype and qtype not in {"Memory Conflict", "Dynamic Update"}:
            return "non_R3a_case"
    return top_type


def why_potentially_repairable(row: dict[str, Any], rejection: dict[str, Any], miss_type: str) -> str:
    r0 = row.get("r0_label")
    if r0 not in {"omission", "hallucination"}:
        return "R0 was already correct; use as harm-risk review, not repair opportunity."
    if miss_type in {"slot_value_near_miss", "temporal_near_miss", "related_but_not_refuting"}:
        return "R0 failed and the rejected memory passed at least one earlier gate; manual audit can decide whether this is real counterevidence."
    if miss_type == "premise_anchor_near_miss":
        return "R0 failed and the rejected memory appears lexically close to the premise but failed anchor alignment."
    if miss_type == "possible_true_counterevidence_rejected":
        return "R0 failed and the rejection passed multiple gates before final rejection."
    return "Probably not repairable by R3a-v2.2 without new evidence."


def compact_rejection(row: dict[str, Any], rejection: dict[str, Any]) -> dict[str, Any]:
    trace = rejection.get("gate_trace") or {}
    score = near_miss_score(rejection)
    miss_type = near_miss_type(rejection)
    return {
        "memory_index": rejection.get("rank"),
        "memory_text": rejection.get("memory_text"),
        "final_reject_reason": rejection.get("reject_reason"),
        "gate_trace": {
            "premise_extracted": row.get("a2_premise"),
            **gate_trace_summary(trace),
        },
        "near_miss_score": score,
        "near_miss_type": miss_type,
        "why_top_rejected": why_potentially_repairable(row, rejection, miss_type),
    }


def build_diagnostics(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    near_miss_rows: list[dict[str, Any]] = []
    per_memory_reasons: Counter[str] = Counter()
    per_sample_dominant: Counter[str] = Counter()
    near_miss_type_counts: Counter[str] = Counter()
    selected_count_dist: Counter[str] = Counter()
    relation_dist: Counter[str] = Counter()
    opportunity_by_r0: Counter[str] = Counter()
    harm_risk_count = 0

    for idx, row in enumerate(rows):
        selected = list(row.get("a2_evidence") or [])
        rejections = list(row.get("a2_rejected") or [])
        reason_counts = Counter(r.get("reject_reason") or "unknown" for r in rejections)
        per_memory_reasons.update(reason_counts)
        dominant_reason = reason_counts.most_common(1)[0][0] if reason_counts else "triggered_or_no_rejections"
        per_sample_dominant[dominant_reason] += 1
        selected_count_dist[str(len(selected))] += 1
        for evidence in selected:
            relation_dist[str(evidence.get("relation") or "unknown")] += 1

        ranked_rejections = sorted(
            rejections,
            key=lambda r: (near_miss_score(r), -int(r.get("rank") or 999)),
            reverse=True,
        )
        top = ranked_rejections[:5]
        near = [r for r in ranked_rejections if near_miss_score(r) >= 4][:5]
        category = diagnostic_category(row, ranked_rejections)
        near_miss_type_counts[category] += 1
        potential = bool(
            not row.get("a2_gate")
            and row.get("r0_label") in {"omission", "hallucination"}
            and category
            in {
                "premise_anchor_near_miss",
                "slot_value_near_miss",
                "temporal_near_miss",
                "related_but_not_refuting",
                "possible_true_counterevidence_rejected",
            }
        )
        if potential:
            opportunity_by_r0[str(row.get("r0_label"))] += 1
        if row.get("r0_label") == "correct" and category in {
            "slot_value_near_miss",
            "temporal_near_miss",
            "related_but_not_refuting",
            "possible_true_counterevidence_rejected",
        }:
            harm_risk_count += 1

        top_compact = [compact_rejection(row, r) for r in top]
        near_compact = [compact_rejection(row, r) for r in near]
        diag = {
            "idx": idx,
            "qa_key": row.get("qa_key"),
            "question": row.get("question"),
            "question_type": row.get("question_type"),
            "r0_label": row.get("r0_label"),
            "a_gated_label": row.get("a_gated_label"),
            "b_gated_v2_2_label": row.get("b_gated_label"),
            "triggered": bool(row.get("a2_gate")),
            "selected_evidence_count": len(selected),
            "selected_evidence": selected,
            "relation": selected[0].get("relation") if selected else None,
            "raw_memory_count": row.get("n_raw"),
            "reject_reason_counts": dict(reason_counts),
            "dominant_reject_reason": dominant_reason,
            "top_rejected_candidates": top_compact,
            "near_miss_candidates": near_compact,
            "diagnostic_category": category,
            "potential_r3a_opportunity": potential,
            "notes": (
                "Post-hoc labels are used only for diagnostic reporting; selector decisions were already made in the input smoke run."
            ),
        }
        diagnostics.append(diag)

        for candidate in near_compact:
            miss_type = candidate["near_miss_type"]
            near_miss_rows.append(
                {
                    "idx": idx,
                    "question": row.get("question"),
                    "r0_label": row.get("r0_label"),
                    "b_gated_v2_2_label": row.get("b_gated_label"),
                    "memory_index": candidate.get("memory_index"),
                    "memory_text": candidate.get("memory_text"),
                    "final_reject_reason": candidate.get("final_reject_reason"),
                    "near_miss_type": miss_type,
                    "gate_trace_summary": json.dumps(candidate.get("gate_trace"), ensure_ascii=False),
                    "why_potentially_repairable": why_potentially_repairable(row, {"reject_reason": candidate.get("final_reject_reason"), "gate_trace": (candidate.get("gate_trace") or {}).get("raw") or {}}, miss_type),
                    "manual_audit_label_empty": "",
                    "manual_notes_empty": "",
                }
            )

    total = len(rows)
    triggered = sum(1 for r in rows if r.get("a2_gate"))
    non_triggered = total - triggered
    potential_count = sum(1 for d in diagnostics if d["potential_r3a_opportunity"])
    summary = {
        "selector_version": SELECTOR_VERSION,
        "total_samples": total,
        "triggered_samples": triggered,
        "trigger_rate": triggered / total if total else 0.0,
        "non_triggered_samples": non_triggered,
        "selected_evidence_count_distribution": dict(selected_count_dist),
        "relation_distribution": dict(relation_dist),
        "per_memory_reject_reason_distribution": dict(per_memory_reasons.most_common()),
        "per_sample_dominant_reject_reason_distribution": dict(per_sample_dominant.most_common()),
        "near_miss_type_counts": dict(near_miss_type_counts.most_common()),
        "near_miss_count": len(near_miss_rows),
        "potential_r3a_opportunity_count": potential_count,
        "potential_r3a_opportunity_by_r0_label": dict(opportunity_by_r0),
        "harm_risk_count_among_r0_correct": harm_risk_count,
        "root_cause_attribution": root_cause(rows, per_memory_reasons, near_miss_type_counts, potential_count),
        "recommended_next_decision": recommended_decision(triggered / total if total else 0.0, potential_count, near_miss_type_counts),
        "api_calls": 0,
        "changed_selector_logic": False,
        "changed_prompt": False,
        "changed_retriever": False,
        "changed_memory_store": False,
    }
    return diagnostics, near_miss_rows, summary


def root_cause(
    rows: list[dict[str, Any]],
    per_memory_reasons: Counter[str],
    near_miss_type_counts: Counter[str],
    potential_count: int,
) -> dict[str, Any]:
    total = len(rows)
    no_candidate = near_miss_type_counts.get("no_candidate_overlap", 0)
    non_r3a = near_miss_type_counts.get("non_R3a_case", 0)
    too_strict = (
        near_miss_type_counts.get("slot_value_near_miss", 0)
        + near_miss_type_counts.get("temporal_near_miss", 0)
        + near_miss_type_counts.get("related_but_not_refuting", 0)
        + near_miss_type_counts.get("possible_true_counterevidence_rejected", 0)
    )
    router = near_miss_type_counts.get("premise_anchor_near_miss", 0)
    inconclusive = near_miss_type_counts.get("diagnostic_inconclusive", 0)
    if no_candidate >= max(too_strict, router, non_r3a, inconclusive):
        dominant = "retrieved_evidence_genuinely_insufficient"
    elif potential_count < max(5, int(total * 0.05)):
        dominant = "sample_contains_few_r3a_opportunity_cases"
    elif too_strict >= router:
        dominant = "selector_too_strict"
    else:
        dominant = "router_or_premise_extraction_failure"
    return {
        "retrieved_evidence_genuinely_insufficient": {
            "count": no_candidate,
            "rate": no_candidate / total if total else 0.0,
        },
        "selector_too_strict": {
            "count": too_strict,
            "rate": too_strict / total if total else 0.0,
        },
        "router_or_premise_extraction_failure": {
            "count": router,
            "rate": router / total if total else 0.0,
        },
        "sample_contains_few_r3a_opportunity_cases": {
            "count": max(0, total - potential_count),
            "rate": (max(0, total - potential_count) / total) if total else 0.0,
        },
        "non_r3a_relation_cases": {
            "count": non_r3a,
            "rate": non_r3a / total if total else 0.0,
        },
        "diagnostic_inconclusive": {
            "count": inconclusive,
            "rate": inconclusive / total if total else 0.0,
        },
        "dominant_low_trigger_cause": dominant,
        "top_reject_reasons": dict(per_memory_reasons.most_common(8)),
    }


def recommended_decision(trigger_rate: float, potential_count: int, near_miss_type_counts: Counter[str]) -> str:
    too_strict = (
        near_miss_type_counts.get("slot_value_near_miss", 0)
        + near_miss_type_counts.get("temporal_near_miss", 0)
        + near_miss_type_counts.get("related_but_not_refuting", 0)
    )
    router = near_miss_type_counts.get("premise_anchor_near_miss", 0)
    no_candidate = near_miss_type_counts.get("no_candidate_overlap", 0)
    total_like = sum(near_miss_type_counts.values())
    if trigger_rate < 0.05 and no_candidate / total_like >= 0.60:
        return "keep_selector_and_change_sampling"
    if router > too_strict:
        return "revise_router_or_premise_extraction"
    if too_strict > 0:
        return "revise_selector"
    return "keep_selector_and_change_sampling"


def write_near_miss_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "idx",
        "question",
        "r0_label",
        "b_gated_v2_2_label",
        "memory_index",
        "memory_text",
        "final_reject_reason",
        "near_miss_type",
        "gate_trace_summary",
        "why_potentially_repairable",
        "manual_audit_label_empty",
        "manual_notes_empty",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_report(path: Path, input_path: Path, summary: dict[str, Any]) -> None:
    root = summary["root_cause_attribution"]
    lines: list[str] = [
        "# R3a-v2.2 Low-Trigger Diagnostic Report",
        "",
        "## 1. Scope",
        "",
        "This diagnostic explains low trigger behavior in the 200-sample AB5 smoke. It does not prove R3a-v2.2 effectiveness.",
        "",
        "## 2. Inputs",
        "",
        f"- smoke jsonl: {input_path}",
        "- selector version metadata: r3a_v2.2_premise_refutation",
        "",
        "## 3. Method",
        "",
        "- Offline-only analysis of existing AB5 smoke rows.",
        "- Reused existing per-row `a2_rejected` gate traces from the smoke output.",
        "- No API calls were made.",
        "- No prompt/retriever/memory-store changes were made.",
        "- Benchmark labels were used only for post-hoc reporting and opportunity estimates, not selector decisions.",
        "",
        "## 4. Trigger Summary",
        "",
        f"- total samples: {summary['total_samples']}",
        f"- triggered samples: {summary['triggered_samples']}",
        f"- trigger rate: {fmt_pct(summary['trigger_rate'])}",
        f"- selected evidence count distribution: {summary['selected_evidence_count_distribution']}",
        f"- relation distribution: {summary['relation_distribution']}",
        "",
        "## 5. Reject Reason Distribution",
        "",
        f"- non-triggered samples: {summary['non_triggered_samples']}",
        f"- per-sample dominant reject reason: {summary['per_sample_dominant_reject_reason_distribution']}",
        f"- per-memory reject reason distribution: {summary['per_memory_reject_reason_distribution']}",
        "",
        "## 6. Near-Miss Analysis",
        "",
        f"- near-miss candidate rows: {summary['near_miss_count']}",
        f"- near-miss type counts: {summary['near_miss_type_counts']}",
        f"- possible R3a opportunities: {summary['potential_r3a_opportunity_count']}",
        "",
        "## 7. Repair Opportunity Estimate",
        "",
        f"- R0 omission potential opportunities: {summary['potential_r3a_opportunity_by_r0_label'].get('omission', 0)}",
        f"- R0 hallucination potential opportunities: {summary['potential_r3a_opportunity_by_r0_label'].get('hallucination', 0)}",
        f"- R0 correct harm-risk cases if relaxed: {summary['harm_risk_count_among_r0_correct']}",
        "",
        "## 8. Low-Trigger Root Cause Attribution",
        "",
    ]
    for key in [
        "retrieved_evidence_genuinely_insufficient",
        "selector_too_strict",
        "router_or_premise_extraction_failure",
        "sample_contains_few_r3a_opportunity_cases",
        "non_r3a_relation_cases",
        "diagnostic_inconclusive",
    ]:
        item = root[key]
        lines.append(f"- {key}: {item['count']} ({fmt_pct(item['rate'])})")
    lines.extend(
        [
            f"- dominant low-trigger cause: {root['dominant_low_trigger_cause']}",
            f"- top reject reasons: {root['top_reject_reasons']}",
            "",
            "## 9. Leakage / Label Use Check",
            "",
            "- No benchmark labels were used by selector decisions in this diagnostic.",
            "- `r0_label`, `a_gated_label`, and `b_gated_label` were used only for post-hoc statistics.",
            "- No gold_answer/question_type/baseline_label was used for selector/router/gate decisions.",
            "",
            "## 10. Recommended Next Decision",
            "",
            f"- {summary['recommended_next_decision']}",
            "",
            "## 11. What Not To Conclude",
            "",
            "- This diagnostic does not prove R3a-v2.2 effectiveness.",
            "- This diagnostic only explains low trigger behavior in the 200-sample AB5 smoke.",
            "- Do not run full scale or larger smoke from this report alone.",
            "- Do not treat O_oracle as an upper bound.",
            "",
            "## 12. Files Generated",
            "",
            "- r3a_v2_2_trigger_diagnostic.jsonl",
            "- r3a_v2_2_trigger_diagnostic_report.md",
            "- r3a_v2_2_near_miss_candidates.csv",
            "- r3a_v2_2_low_trigger_summary.json",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = load_jsonl(input_path)
    diagnostics, near_miss_rows, summary = build_diagnostics(rows)
    write_jsonl(outdir / "r3a_v2_2_trigger_diagnostic.jsonl", diagnostics)
    write_near_miss_csv(outdir / "r3a_v2_2_near_miss_candidates.csv", near_miss_rows)
    (outdir / "r3a_v2_2_low_trigger_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(outdir / "r3a_v2_2_trigger_diagnostic_report.md", input_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline low-trigger diagnostic for R3a-v2.2 AB5 smoke")
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
