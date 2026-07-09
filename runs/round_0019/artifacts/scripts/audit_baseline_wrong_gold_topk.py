import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "baseline_wrong_gold_topk_audit"

INPUTS = [
    {
        "run_id": "mem0_medium",
        "dataset": "medium",
        "system": "mem0",
        "path": ROOT / "outputs" / "baseline_sharded_v2" / "mem0_medium" / "merged" / "mem0_medium_qa_merged.jsonl",
    },
    {
        "run_id": "supermemory_medium",
        "dataset": "medium",
        "system": "supermemory",
        "path": ROOT / "outputs" / "baseline_sharded_v2_medium_only" / "supermemory" / "merged" / "supermemory_medium_qa_merged.jsonl",
    },
    {
        "run_id": "memobase_medium",
        "dataset": "medium",
        "system": "memobase",
        "path": ROOT / "outputs" / "baseline_full" / "memobase_medium" / "memobase_medium_qa.jsonl",
    },
    {
        "run_id": "memos_medium",
        "dataset": "medium",
        "system": "memos",
        "path": ROOT / "outputs" / "baseline_full" / "memos_medium" / "memos_medium_qa.jsonl",
    },
    {
        "run_id": "mem0_long",
        "dataset": "long",
        "system": "mem0",
        "path": ROOT / "outputs" / "baseline_full" / "mem0_long" / "mem0_long_qa.jsonl",
    },
    {
        "run_id": "memobase_long",
        "dataset": "long",
        "system": "memobase",
        "path": ROOT / "outputs" / "baseline_full" / "memobase_long" / "memobase_long_qa.jsonl",
    },
    {
        "run_id": "memos_long",
        "dataset": "long",
        "system": "memos",
        "path": ROOT / "outputs" / "baseline_full" / "memos_long" / "memos_long_qa.jsonl",
    },
]

TOKEN_RE = re.compile(r"[a-z0-9]+")


def norm_text(value):
    value = str(value or "").lower()
    value = value.replace("user's", "users")
    return " ".join(TOKEN_RE.findall(value))


def tokens(value):
    return set(TOKEN_RE.findall(str(value or "").lower()))


def flatten_strings(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for key in [
            "memory",
            "memory_content",
            "memory_key",
            "memory_value",
            "text",
            "preference",
            "reasoning",
            "section",
            "tags",
            "reference_memory_content",
        ]:
            if key in value:
                out.extend(flatten_strings(value[key]))
        if not out:
            for item in value.values():
                out.extend(flatten_strings(item))
        return out
    return [str(value)]


def raw_memory_texts(raw_memories):
    if not isinstance(raw_memories, list):
        return []
    texts = []
    for item in raw_memories:
        text = " | ".join(s for s in flatten_strings(item) if s)
        texts.append(text)
    return texts


def evidence_texts(record):
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        return []
    texts = []
    for item in evidence:
        if isinstance(item, dict):
            text = item.get("memory_content") or item.get("text") or item.get("memory")
            if text:
                texts.append(str(text))
        elif item:
            texts.append(str(item))
    return texts


def evidence_hit(evidence, retrieved_texts, coverage_threshold=0.60):
    retrieved_norm = [norm_text(text) for text in retrieved_texts]
    retrieved_tokens = [tokens(text) for text in retrieved_texts]

    per_evidence = []
    for ev in evidence:
        ev_norm = norm_text(ev)
        ev_tokens = tokens(ev)
        strict = False
        coverage = 0.0
        if ev_norm:
            strict = any(ev_norm in rt or (rt and rt in ev_norm) for rt in retrieved_norm)
        if ev_tokens:
            coverage = max((len(ev_tokens & rt) / len(ev_tokens) for rt in retrieved_tokens), default=0.0)
        per_evidence.append(
            {
                "evidence": ev,
                "strict_hit": strict,
                "coverage": round(coverage, 4),
                "coverage_hit": coverage >= coverage_threshold,
            }
        )

    any_strict = any(item["strict_hit"] for item in per_evidence)
    all_strict = bool(per_evidence) and all(item["strict_hit"] for item in per_evidence)
    any_coverage = any(item["coverage_hit"] for item in per_evidence)
    all_coverage = bool(per_evidence) and all(item["coverage_hit"] for item in per_evidence)

    return {
        "any_strict_hit": any_strict,
        "all_strict_hit": all_strict,
        "any_coverage_hit": any_coverage,
        "all_coverage_hit": all_coverage,
        "per_evidence": per_evidence,
    }


def pct(num, den):
    return round(num / den * 100, 2) if den else 0.0


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = []
    summaries = []
    qtype_rows = []
    missing = []

    for spec in INPUTS:
        path = spec["path"]
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue

        stats = Counter()
        by_type = defaultdict(Counter)
        label_counts = Counter()

        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                label = record.get("baseline_label")
                qtype = record.get("question_type") or "UNKNOWN"
                label_counts[label] += 1
                stats["records"] += 1
                by_type[qtype]["records"] += 1

                if label == "correct":
                    continue

                evidence = evidence_texts(record)
                retrieved = raw_memory_texts(record.get("raw_memories"))
                hit = evidence_hit(evidence, retrieved)

                stats["wrong"] += 1
                stats[f"wrong_{label}"] += 1
                by_type[qtype]["wrong"] += 1
                by_type[qtype][f"wrong_{label}"] += 1

                if evidence:
                    stats["wrong_with_evidence"] += 1
                    by_type[qtype]["wrong_with_evidence"] += 1
                    for key in ["any_strict_hit", "all_strict_hit", "any_coverage_hit", "all_coverage_hit"]:
                        if hit[key]:
                            stats[f"wrong_with_evidence_{key}"] += 1
                            by_type[qtype][f"wrong_with_evidence_{key}"] += 1
                else:
                    stats["wrong_without_evidence"] += 1
                    by_type[qtype]["wrong_without_evidence"] += 1

                details.append(
                    {
                        "run_id": spec["run_id"],
                        "dataset": spec["dataset"],
                        "system": spec["system"],
                        "source_file": str(path.relative_to(ROOT)),
                        "line_no": line_no,
                        "qa_key": record.get("qa_key") or "",
                        "uuid": record.get("uuid") or "",
                        "question_type": qtype,
                        "question": record.get("question") or "",
                        "gold_answer": record.get("gold_answer") or "",
                        "baseline_response": record.get("baseline_response") or "",
                        "baseline_label": label or "",
                        "evidence_count": len(evidence),
                        "retrieved_count": len(retrieved),
                        "any_strict_hit": hit["any_strict_hit"],
                        "all_strict_hit": hit["all_strict_hit"],
                        "any_coverage_hit_0p60": hit["any_coverage_hit"],
                        "all_coverage_hit_0p60": hit["all_coverage_hit"],
                        "max_evidence_coverage": max((item["coverage"] for item in hit["per_evidence"]), default=0.0),
                        "evidence_json": json.dumps(evidence, ensure_ascii=False),
                    }
                )

        row = {
            "run_id": spec["run_id"],
            "dataset": spec["dataset"],
            "system": spec["system"],
            "source_file": str(path.relative_to(ROOT)),
            "records": stats["records"],
            "correct": label_counts["correct"],
            "hallucination": label_counts["hallucination"],
            "omission": label_counts["omission"],
            "wrong": stats["wrong"],
            "wrong_rate": pct(stats["wrong"], stats["records"]),
            "wrong_with_evidence": stats["wrong_with_evidence"],
            "wrong_without_evidence": stats["wrong_without_evidence"],
            "wrong_any_strict_hit": stats["wrong_with_evidence_any_strict_hit"],
            "wrong_any_strict_hit_rate_all_wrong": pct(stats["wrong_with_evidence_any_strict_hit"], stats["wrong"]),
            "wrong_any_strict_hit_rate_evidence_wrong": pct(
                stats["wrong_with_evidence_any_strict_hit"], stats["wrong_with_evidence"]
            ),
            "wrong_all_strict_hit": stats["wrong_with_evidence_all_strict_hit"],
            "wrong_all_strict_hit_rate_evidence_wrong": pct(
                stats["wrong_with_evidence_all_strict_hit"], stats["wrong_with_evidence"]
            ),
            "wrong_any_coverage_hit_0p60": stats["wrong_with_evidence_any_coverage_hit"],
            "wrong_any_coverage_hit_rate_all_wrong": pct(
                stats["wrong_with_evidence_any_coverage_hit"], stats["wrong"]
            ),
            "wrong_any_coverage_hit_rate_evidence_wrong": pct(
                stats["wrong_with_evidence_any_coverage_hit"], stats["wrong_with_evidence"]
            ),
            "wrong_all_coverage_hit_0p60": stats["wrong_with_evidence_all_coverage_hit"],
            "wrong_all_coverage_hit_rate_evidence_wrong": pct(
                stats["wrong_with_evidence_all_coverage_hit"], stats["wrong_with_evidence"]
            ),
        }
        summaries.append(row)

        for qtype, qstats in sorted(by_type.items()):
            qtype_rows.append(
                {
                    "run_id": spec["run_id"],
                    "dataset": spec["dataset"],
                    "system": spec["system"],
                    "question_type": qtype,
                    "records": qstats["records"],
                    "wrong": qstats["wrong"],
                    "wrong_rate": pct(qstats["wrong"], qstats["records"]),
                    "wrong_hallucination": qstats["wrong_hallucination"],
                    "wrong_omission": qstats["wrong_omission"],
                    "wrong_with_evidence": qstats["wrong_with_evidence"],
                    "wrong_without_evidence": qstats["wrong_without_evidence"],
                    "wrong_any_strict_hit": qstats["wrong_with_evidence_any_strict_hit"],
                    "wrong_any_strict_hit_rate_evidence_wrong": pct(
                        qstats["wrong_with_evidence_any_strict_hit"], qstats["wrong_with_evidence"]
                    ),
                    "wrong_any_coverage_hit_0p60": qstats["wrong_with_evidence_any_coverage_hit"],
                    "wrong_any_coverage_hit_rate_evidence_wrong": pct(
                        qstats["wrong_with_evidence_any_coverage_hit"], qstats["wrong_with_evidence"]
                    ),
                }
            )

    details_path = OUT_DIR / "baseline_wrong_samples_gold_topk.csv"
    qtype_path = OUT_DIR / "baseline_wrong_gold_topk_by_question_type.csv"
    summary_path = OUT_DIR / "baseline_wrong_gold_topk_summary.json"
    report_path = OUT_DIR / "baseline_wrong_gold_topk_report.md"

    detail_fields = [
        "run_id",
        "dataset",
        "system",
        "source_file",
        "line_no",
        "qa_key",
        "uuid",
        "question_type",
        "question",
        "gold_answer",
        "baseline_response",
        "baseline_label",
        "evidence_count",
        "retrieved_count",
        "any_strict_hit",
        "all_strict_hit",
        "any_coverage_hit_0p60",
        "all_coverage_hit_0p60",
        "max_evidence_coverage",
        "evidence_json",
    ]
    with details_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)

    qtype_fields = [
        "run_id",
        "dataset",
        "system",
        "question_type",
        "records",
        "wrong",
        "wrong_rate",
        "wrong_hallucination",
        "wrong_omission",
        "wrong_with_evidence",
        "wrong_without_evidence",
        "wrong_any_strict_hit",
        "wrong_any_strict_hit_rate_evidence_wrong",
        "wrong_any_coverage_hit_0p60",
        "wrong_any_coverage_hit_rate_evidence_wrong",
    ]
    with qtype_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=qtype_fields)
        writer.writeheader()
        writer.writerows(qtype_rows)

    payload = {
        "notes": [
            "The HaluMem dataset itself contains questions, gold answers, and gold evidence, but not baseline model outputs or correctness labels.",
            "Wrong samples are defined from existing baseline QA JSONL files with baseline_label != 'correct'.",
            "Top-k is approximated by each baseline record's raw_memories field, i.e. the retrieval context available to the baseline answerer.",
            "Strict hit uses normalized substring matching. Coverage hit uses >=0.60 token coverage of an evidence item by any retrieved item; this is a diagnostic proxy for paraphrased memories.",
        ],
        "missing_inputs": missing,
        "summaries": summaries,
        "by_question_type": qtype_rows,
        "detail_file": str(details_path.relative_to(ROOT)),
        "question_type_file": str(qtype_path.relative_to(ROOT)),
    }
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Baseline Wrong Samples vs Gold Evidence in Top-k\n\n")
        f.write("## Answer\n\n")
        f.write(
            "HaluMem source data alone is not enough to identify baseline-wrong samples; "
            "it must be joined with baseline outputs and judge labels. Existing baseline QA JSONL files "
            "do contain those labels plus retrieved `raw_memories`, so the audit can be computed offline.\n\n"
        )
        f.write("## Overall Summary\n\n")
        f.write(
            "| run_id | records | wrong | wrong rate | wrong with evidence | any strict hit | any strict / evidence-wrong | any coverage hit >=0.60 | coverage / evidence-wrong |\n"
        )
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summaries:
            f.write(
                f"| {row['run_id']} | {row['records']} | {row['wrong']} | {row['wrong_rate']:.2f}% | "
                f"{row['wrong_with_evidence']} | {row['wrong_any_strict_hit']} | "
                f"{row['wrong_any_strict_hit_rate_evidence_wrong']:.2f}% | "
                f"{row['wrong_any_coverage_hit_0p60']} | "
                f"{row['wrong_any_coverage_hit_rate_evidence_wrong']:.2f}% |\n"
            )
        f.write("\n## Files\n\n")
        f.write(f"- Detail CSV: `{details_path.relative_to(ROOT)}`\n")
        f.write(f"- By-question-type CSV: `{qtype_path.relative_to(ROOT)}`\n")
        f.write(f"- Machine summary: `{summary_path.relative_to(ROOT)}`\n")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
