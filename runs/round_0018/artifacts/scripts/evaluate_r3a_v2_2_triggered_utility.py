from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import Workbook


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from r3a_v2_selector import select_counterevidence_v2  # noqa: E402
from run_mem0_medium_ab5_offline import (  # noqa: E402
    DEFAULT_MODEL,
    LABELS,
    build_a2_evidence_prompt,
    build_correction_prompt,
    call_chat,
    call_judge,
    format_context,
)


EXPECTED_TRIGGERED = 78
EXPECTED_TYPE = "Memory Conflict"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_triggered(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_TRIGGERED:
        raise RuntimeError(f"Expected {EXPECTED_TRIGGERED} triggered samples, found {len(rows)}")
    keys = [row["qa_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Triggered CSV contains duplicate qa_key values")
    non_mc = [row["qa_key"] for row in rows if row.get("question_type") != EXPECTED_TYPE]
    if non_mc:
        raise RuntimeError(f"Triggered CSV contains non-{EXPECTED_TYPE} rows: {non_mc[:10]}")
    return rows


def make_client() -> Any:
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY or OPENAI_API_KEY, or rerun with complete cache.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.deepseek.com"
    return OpenAI(api_key=api_key, base_url=base_url)


def read_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        qa_key = str(row.get("qa_key") or "")
        if qa_key:
            out[qa_key] = row
    return out


def norm_label(value: Any) -> str:
    label = str(value or "").strip().lower()
    return label if label in LABELS else "omission"


def same_evidence(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    if not left or not right:
        return False
    l0, r0 = left[0], right[0]
    return (
        str(l0.get("memory_id") or "") == str(r0.get("memory_id") or "")
        and str(l0.get("memory_text") or "").strip() == str(r0.get("memory_text") or "").strip()
    )


def build_route_rows(args: argparse.Namespace, triggered: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    qa_rows = {str(row.get("qa_key")): row for row in load_jsonl(Path(args.qa))}
    old_ab5 = read_cache(Path(args.ab5_cache))
    v2_cache = read_cache(Path(args.v2_cache))
    existing = read_cache(Path(args.route_output))
    client = None
    route_rows: list[dict[str, Any]] = []
    generated = {"a_answer": 0, "a_judge": 0, "b_answer": 0, "b_judge": 0}
    reused = {"a_old_ab5": 0, "b_v2_cache": 0, "existing_output": 0}

    for seq, trig in enumerate(triggered, start=1):
        qa_key = trig["qa_key"]
        if qa_key not in qa_rows:
            raise RuntimeError(f"Triggered qa_key not found in QA file: {qa_key}")
        qa = qa_rows[qa_key]
        if qa.get("question_type") != EXPECTED_TYPE:
            raise RuntimeError(f"QA row {qa_key} is not {EXPECTED_TYPE}: {qa.get('question_type')}")
        for field in ("question", "raw_memories", "baseline_response", "baseline_label", "gold_answer"):
            if field not in qa:
                raise RuntimeError(f"QA row {qa_key} missing required field {field}")

        question = str(qa["question"])
        raw_memories = qa.get("raw_memories") or []
        context = format_context(raw_memories)
        selection = select_counterevidence_v2(question, raw_memories, max_evidence=args.max_evidence)
        selected = list(selection.get("evidence") or [])
        if not selection.get("triggered") or len(selected) != int(trig.get("selected_evidence_count") or 0):
            raise RuntimeError(
                f"R3a-v2.2 reselection mismatch for {qa_key}: triggered={selection.get('triggered')} "
                f"selected={len(selected)} csv_count={trig.get('selected_evidence_count')}"
            )

        a_prompt = build_correction_prompt(question, context)
        b_prompt = build_a2_evidence_prompt(question, context, selected)
        r0_response = str(qa.get("baseline_response", ""))
        r0_label = norm_label(qa.get("baseline_label"))
        old = old_ab5.get(qa_key, {})
        cached = v2_cache.get(qa_key, {})
        exists = existing.get(qa_key, {})
        if exists and exists.get("selector_version") == selection.get("selector_version") and same_evidence(exists.get("selected_evidence") or [], selected):
            route_rows.append(exists)
            reused["existing_output"] += 1
            continue

        if old.get("a_all_response") and old.get("a_all_label"):
            a_response = str(old["a_all_response"])
            a_label = norm_label(old["a_all_label"])
            a_rationale = str(old.get("a_all_judge_rationale", "reused old AB5 a_all judge"))
            a_source = "outputs/a2_ab5/mem0_medium_ab5.jsonl:a_all"
            reused["a_old_ab5"] += 1
        else:
            if not args.allow_api:
                raise RuntimeError(f"Missing A route cache for {qa_key}; rerun with --allow_api true")
            client = client or make_client()
            start = time.time()
            a_response = call_chat(client, args.model, a_prompt)
            generated["a_answer"] += 1
            a_judge = call_judge(client, args.model, question, str(qa.get("gold_answer", "")), a_response)
            generated["a_judge"] += 1
            a_label = norm_label(a_judge["label"])
            a_rationale = a_judge["rationale"]
            a_source = f"api:{time.time() - start:.2f}s"

        cache_ev = list(cached.get("a2_evidence") or [])
        if (
            cached.get("r3a_selector_version") == selection.get("selector_version")
            and cached.get("b_gated_response")
            and cached.get("b_gated_label")
            and same_evidence(cache_ev, selected)
        ):
            b_response = str(cached["b_gated_response"])
            b_label = norm_label(cached["b_gated_label"])
            b_rationale = str(cached.get("b_gated_judge_rationale", "reused v2 smoke judge"))
            b_source = "outputs/r3a_v2_2_ab5_smoke/r3a_v2_2_ab5_smoke.jsonl:b_gated"
            reused["b_v2_cache"] += 1
        else:
            if not args.allow_api:
                raise RuntimeError(f"Missing R3a-v2.2 B route cache for {qa_key}; rerun with --allow_api true")
            if seq > args.max_samples:
                raise RuntimeError(f"Refusing to generate beyond --max_samples={args.max_samples}")
            client = client or make_client()
            start = time.time()
            b_response = call_chat(client, args.model, b_prompt)
            generated["b_answer"] += 1
            b_judge = call_judge(client, args.model, question, str(qa.get("gold_answer", "")), b_response)
            generated["b_judge"] += 1
            b_label = norm_label(b_judge["label"])
            b_rationale = b_judge["rationale"]
            b_source = f"api:{time.time() - start:.2f}s"

        route_row = {
            "qa_key": qa_key,
            "idx": int(trig["idx"]),
            "question": question,
            "question_type": qa.get("question_type"),
            "gold_answer": qa.get("gold_answer"),
            "n_raw": len(raw_memories),
            "r0_response": r0_response,
            "r0_label": r0_label,
            "r0_source": "qa_baseline_cache",
            "a_triggered_response": a_response,
            "a_triggered_label": a_label,
            "a_triggered_judge_rationale": a_rationale,
            "a_triggered_prompt": a_prompt,
            "a_triggered_source": a_source,
            "b_triggered_response": b_response,
            "b_triggered_label": b_label,
            "b_triggered_judge_rationale": b_rationale,
            "b_triggered_prompt": b_prompt,
            "b_triggered_source": b_source,
            "b_memory_only_response": None,
            "b_memory_only_label": None,
            "b_memory_only_note": "skipped_by_design",
            "selector_version": selection.get("selector_version"),
            "selection_reason": selection.get("reason"),
            "selected_evidence_count": len(selected),
            "selected_evidence": selected,
            "premise": selection.get("premise"),
            "r3a_rejected": selection.get("rejected", []),
            "model": args.model,
            "temperature": 0,
            "answer_max_tokens": 160,
            "judge_max_tokens": 256,
        }
        append_jsonl(Path(args.route_output), route_row)
        route_rows.append(route_row)
        print(f"[progress] {seq}/{len(triggered)} {qa_key}", flush=True)

    return sorted(route_rows, key=lambda row: row["idx"]), {"generated": generated, "reused": reused}


def label_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(norm_label(row.get(key)) for row in rows)
    return {label: counts[label] for label in LABELS}


def rate(rows: list[dict[str, Any]], key: str, label: str) -> float:
    return sum(1 for row in rows if row.get(key) == label) / len(rows)


def paired_delta(rows: list[dict[str, Any]], base: str, target: str, label: str) -> float:
    return rate(rows, target, label) - rate(rows, base, label)


def repairs(rows: list[dict[str, Any]], base: str, target: str) -> dict[str, int]:
    repair = sum(1 for row in rows if row.get(base) != "correct" and row.get(target) == "correct")
    harm = sum(1 for row in rows if row.get(base) == "correct" and row.get(target) != "correct")
    return {"repairs": repair, "harm": harm, "net_repairs": repair - harm}


def bootstrap_ci(rows: list[dict[str, Any]], base: str, target: str, metric: str, n_boot: int, seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    n = len(rows)
    vals: list[float] = []
    for _ in range(n_boot):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        if metric in LABELS:
            vals.append(paired_delta(sample, base, target, metric))
        else:
            vals.append(repairs(sample, base, target)[metric] / n)
    vals.sort()
    lo = vals[int(0.025 * n_boot)]
    hi = vals[min(n_boot - 1, int(0.975 * n_boot))]
    if metric in LABELS:
        point = paired_delta(rows, base, target, metric)
    else:
        point = repairs(rows, base, target)[metric] / n
    return {"point": point, "ci95_low": lo, "ci95_high": hi}


def mcnemar_exact(rows: list[dict[str, Any]], base: str, target: str, label: str) -> dict[str, Any]:
    b = sum(1 for row in rows if row.get(base) == label and row.get(target) != label)
    c = sum(1 for row in rows if row.get(base) != label and row.get(target) == label)
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p_two_sided": 1.0}
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2**n)
    return {"b": b, "c": c, "p_two_sided": min(1.0, 2 * tail)}


def transition(row: dict[str, Any], base: str, target: str) -> str:
    return f"{row.get(base)}->{row.get(target)}"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "triggered_audit"
    ws.append(fieldnames)
    for row in rows:
        ws.append([row.get(field, "") for field in fieldnames])
    ws.freeze_panes = "A2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def make_outputs(args: argparse.Namespace, rows: list[dict[str, Any]], cache_meta: dict[str, Any]) -> None:
    outdir = Path(args.outdir)
    route_output = outdir / "triggered_route_outputs.jsonl"
    write_jsonl(route_output, rows)

    selected_rows = []
    transitions = []
    audit_rows = []
    for row in rows:
        ev = (row.get("selected_evidence") or [{}])[0]
        selected_rows.append(
            {
                "qa_key": row["qa_key"],
                "idx": row["idx"],
                "memory_ref": ev.get("memory_ref"),
                "memory_id": ev.get("memory_id"),
                "confidence": ev.get("confidence"),
                "relation": ev.get("relation"),
                "memory_text": ev.get("memory_text"),
                "refutation_statement": ev.get("refutation_statement"),
            }
        )
        transitions.append(
            {
                "qa_key": row["qa_key"],
                "idx": row["idx"],
                "r0_label": row["r0_label"],
                "a_triggered_label": row["a_triggered_label"],
                "b_triggered_label": row["b_triggered_label"],
                "r0_to_b": transition(row, "r0_label", "b_triggered_label"),
                "a_to_b": transition(row, "a_triggered_label", "b_triggered_label"),
                "r0_to_a": transition(row, "r0_label", "a_triggered_label"),
            }
        )
        audit_rows.append(
            {
                "qa_key": row["qa_key"],
                "idx": row["idx"],
                "question": row["question"],
                "gold_answer": row["gold_answer"],
                "r0_response": row["r0_response"],
                "r0_label": row["r0_label"],
                "a_triggered_response": row["a_triggered_response"],
                "a_triggered_label": row["a_triggered_label"],
                "b_triggered_response": row["b_triggered_response"],
                "b_triggered_label": row["b_triggered_label"],
                "selected_evidence": ev.get("memory_text"),
                "b_judge_rationale": row["b_triggered_judge_rationale"],
                "manual_decision": "",
                "manual_notes": "",
            }
        )

    write_csv(outdir / "triggered_selected_evidence.csv", selected_rows, list(selected_rows[0]))
    write_csv(outdir / "triggered_transition_table.csv", transitions, list(transitions[0]))
    audit_fields = list(audit_rows[0])
    write_csv(outdir / "triggered_manual_audit_sheet.csv", audit_rows, audit_fields)
    write_xlsx(outdir / "triggered_manual_audit_sheet.xlsx", audit_rows, audit_fields)

    pairs = {
        "R0_vs_B": ("r0_label", "b_triggered_label"),
        "A_vs_B": ("a_triggered_label", "b_triggered_label"),
    }
    bootstrap = {
        pair_name: {
            metric: bootstrap_ci(rows, base, target, metric, args.bootstrap, args.seed + i)
            for i, metric in enumerate([*LABELS, "repairs", "harm", "net_repairs"])
        }
        for pair_name, (base, target) in pairs.items()
    }
    tests = {
        pair_name: {
            label: mcnemar_exact(rows, base, target, label)
            for label in LABELS
        }
        for pair_name, (base, target) in pairs.items()
    }
    stats = {
        "n": len(rows),
        "expected_triggered": EXPECTED_TRIGGERED,
        "question_type_counts": dict(Counter(row["question_type"] for row in rows)),
        "selector_versions": dict(Counter(row["selector_version"] for row in rows)),
        "selected_evidence_count_distribution": dict(Counter(row["selected_evidence_count"] for row in rows)),
        "route_label_counts": {
            "R0": label_counts(rows, "r0_label"),
            "A_triggered": label_counts(rows, "a_triggered_label"),
            "B_triggered": label_counts(rows, "b_triggered_label"),
        },
        "deltas": {
            "B_vs_R0": {label: paired_delta(rows, "r0_label", "b_triggered_label", label) for label in LABELS},
            "B_vs_A": {label: paired_delta(rows, "a_triggered_label", "b_triggered_label", label) for label in LABELS},
        },
        "repairs": {
            "B_vs_R0": repairs(rows, "r0_label", "b_triggered_label"),
            "B_vs_A": repairs(rows, "a_triggered_label", "b_triggered_label"),
        },
        "bootstrap": bootstrap,
        "paired_tests": tests,
        "cache_and_generation": cache_meta,
        "b_memory_only": "skipped_by_design",
    }
    write_json(outdir / "triggered_stats.json", stats)

    summary = {
        "task": "R3a-v2.2 triggered sample answer utility evaluation",
        "n_triggered_samples": len(rows),
        "all_memory_conflict": all(row["question_type"] == EXPECTED_TYPE for row in rows),
        "all_reselected_by_r3a_v2_2": all(row["selector_version"] == "r3a_v2_premise_refutation" for row in rows),
        "model": args.model,
        "allow_api": args.allow_api,
        "route_label_counts": stats["route_label_counts"],
        "deltas": stats["deltas"],
        "repairs": stats["repairs"],
        "bootstrap": bootstrap,
        "paired_tests": tests,
        "outputs": [
            "triggered_utility_eval_summary.json",
            "triggered_utility_eval_report.md",
            "triggered_route_outputs.jsonl",
            "triggered_transition_table.csv",
            "triggered_manual_audit_sheet.xlsx",
            "triggered_manual_audit_sheet.csv",
            "triggered_selected_evidence.csv",
            "triggered_stats.json",
        ],
    }
    write_json(outdir / "triggered_utility_eval_summary.json", summary)
    (outdir / "triggered_utility_eval_report.md").write_text(make_report(summary, stats), encoding="utf-8")


def fmt_count(counts: dict[str, int], n: int) -> str:
    return ", ".join(f"{label}={counts[label]} ({counts[label] / n:.1%})" for label in LABELS)


def make_report(summary: dict[str, Any], stats: dict[str, Any]) -> str:
    n = stats["n"]
    lines = [
        "# R3a-v2.2 Triggered Utility Evaluation",
        "",
        "## Scope",
        "",
        f"- Triggered samples evaluated: {n}",
        f"- All samples are Memory Conflict: {summary['all_memory_conflict']}",
        f"- All samples reselected by R3a-v2.2: {summary['all_reselected_by_r3a_v2_2']}",
        "- R0 uses cached baseline response/label from the QA file.",
        "- A_triggered uses the AB5 generic conflict-warning prompt without selected evidence.",
        "- B_triggered admits only R3a-v2.2 selected evidence.",
        "- B_memory_only was skipped by design.",
        "",
        "## Route Label Counts",
        "",
        "| route | correct | hallucination | omission |",
        "|---|---:|---:|---:|",
    ]
    for route, counts in stats["route_label_counts"].items():
        lines.append(f"| {route} | {counts['correct']} | {counts['hallucination']} | {counts['omission']} |")
    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "| comparison | delta correct | delta hallucination | delta omission | repairs | harm | net repairs |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, deltas in stats["deltas"].items():
        repair = stats["repairs"][name]
        lines.append(
            f"| {name} | {deltas['correct']:+.3f} | {deltas['hallucination']:+.3f} | "
            f"{deltas['omission']:+.3f} | {repair['repairs']} | {repair['harm']} | {repair['net_repairs']} |"
        )
    lines.extend(["", "## Paired Tests", "", "| comparison | label | b | c | p_two_sided |", "|---|---|---:|---:|---:|"])
    for pair, labels in stats["paired_tests"].items():
        for label, test in labels.items():
            lines.append(f"| {pair} | {label} | {test['b']} | {test['c']} | {test['p_two_sided']:.6f} |")
    lines.extend(["", "## Cache And Generation", "", "```json", json.dumps(stats["cache_and_generation"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate answer-level utility for the 78 R3a-v2.2 triggered samples.")
    parser.add_argument("--triggered", default=str(ROOT / "outputs" / "r3a_v2_2_full_offline_opportunity_census" / "r3a_triggered_samples.csv"))
    parser.add_argument("--qa", default=str(ROOT / "data" / "mem0" / "medium" / "mem0_medium_qa.jsonl"))
    parser.add_argument("--selector", default=str(SCRIPT_DIR / "r3a_v2_selector.py"))
    parser.add_argument("--outdir", default=str(ROOT / "outputs" / "r3a_v2_2_triggered_utility_eval"))
    parser.add_argument("--ab5-cache", default=str(ROOT / "outputs" / "a2_ab5" / "mem0_medium_ab5.jsonl"))
    parser.add_argument("--v2-cache", default=str(ROOT / "outputs" / "r3a_v2_2_ab5_smoke" / "r3a_v2_2_ab5_smoke.jsonl"))
    parser.add_argument("--route-output", default=str(ROOT / "outputs" / "r3a_v2_2_triggered_utility_eval" / "triggered_route_outputs.jsonl"))
    parser.add_argument("--allow_api", nargs="?", const=True, default=False, type=lambda value: str(value).lower() in {"1", "true", "yes", "y"})
    parser.add_argument("--max_samples", type=int, default=EXPECTED_TRIGGERED)
    parser.add_argument("--max-evidence", type=int, default=1)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--bootstrap", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260625)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if Path(args.selector).resolve() != (SCRIPT_DIR / "r3a_v2_selector.py").resolve():
        raise RuntimeError("This evaluator is pinned to 脚本/3.0/r3a_v2_selector.py")
    triggered = load_triggered(Path(args.triggered))
    if args.allow_api and args.max_samples != EXPECTED_TRIGGERED:
        raise RuntimeError(f"Explicit API run must use --max_samples {EXPECTED_TRIGGERED}")
    rows, cache_meta = build_route_rows(args, triggered)
    if len(rows) != EXPECTED_TRIGGERED:
        raise RuntimeError(f"Incomplete route output: {len(rows)}/{EXPECTED_TRIGGERED}")
    make_outputs(args, rows, cache_meta)
    print(f"[done] wrote {Path(args.outdir)}", flush=True)


if __name__ == "__main__":
    main()
