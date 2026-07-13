from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from e1_memos_oracle_common import (
    CONDITIONS,
    EXPECTED_COUNTS,
    LICENSE_TEMPLATES,
    LONG_QA,
    MEDIUM_QA,
    MODEL,
    OUT_DIR,
    PROMPT_MEMOS,
    ROOT,
    SEED,
    SEMANTIC_DETAIL,
    build_gold_only_judge_prompt,
    evidence_texts,
    extract_note_block,
    ids_for_raw,
    prompt_hashes,
    read_jsonl,
    sha256_text,
    write_json,
)


RUNS = {
    "memos_medium": ("medium", MEDIUM_QA),
    "memos_long": ("long", LONG_QA),
}


def load_semantic_cache() -> dict[str, dict[str, Any]]:
    rows = {}
    for row in read_jsonl(SEMANTIC_DETAIL):
        if row.get("run_id") in RUNS:
            rows[str(row["case_id"])] = row
    return rows


def collect_memory_ids(semantic: dict[str, Any], raw_count: int) -> tuple[list[str], list[str], list[str]]:
    all_ids = set(ids_for_raw([None] * raw_count))
    gold_ids: list[str] = []
    partial_ids: list[str] = []
    for result in semantic.get("evidence_results") or []:
        status = result.get("status")
        best_ids = [mid for mid in result.get("best_memory_ids") or [] if mid in all_ids]
        if status == "supported":
            gold_ids.extend(best_ids)
        elif status == "partially_supported":
            partial_ids.extend(best_ids)

    def unique(values: list[str]) -> list[str]:
        out = []
        seen = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                out.append(value)
        return out

    gold = unique(gold_ids)
    partial = [mid for mid in unique(partial_ids) if mid not in set(gold)]
    other = [mid for mid in ids_for_raw([None] * raw_count) if mid not in set(gold) and mid not in set(partial)]
    return gold, partial, other


def build_samples() -> list[dict[str, Any]]:
    semantic_cache = load_semantic_cache()
    samples: list[dict[str, Any]] = []
    missing_semantic: list[str] = []

    for run_id, (dataset, path) in RUNS.items():
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("baseline_label") == "correct":
                    continue
                evidence = evidence_texts(record)
                if not evidence:
                    continue
                case_id = f"{run_id}:{line_no}"
                semantic = semantic_cache.get(case_id)
                if semantic is None:
                    missing_semantic.append(case_id)
                    continue
                raw_memories = record.get("raw_memories") or []
                gold_ids, partial_ids, other_ids = collect_memory_ids(semantic, len(raw_memories))
                if gold_ids:
                    stratum = "strict_supported"
                elif partial_ids:
                    stratum = "partial_supported"
                else:
                    stratum = "no_gold_retrieved"

                samples.append(
                    {
                        "case_id": case_id,
                        "run_id": run_id,
                        "dataset": dataset,
                        "source_file": str(path.relative_to(ROOT)),
                        "line_no": line_no,
                        "qa_key": record.get("qa_key") or "",
                        "uuid": record.get("uuid") or "",
                        "user_name": record.get("user_name") or "",
                        "question_type": record.get("question_type") or "UNKNOWN",
                        "question": record.get("question") or "",
                        "gold_answer": record.get("gold_answer") or "",
                        "gold_evidence": evidence,
                        "raw_memories": raw_memories,
                        "baseline_answer": record.get("baseline_response") or "",
                        "baseline_response": record.get("baseline_response") or "",
                        "baseline_verdict": record.get("baseline_label") or "",
                        "baseline_label": record.get("baseline_label") or "",
                        "context_str_full": record.get("context_str_full") or "",
                        "memos_note": extract_note_block(record.get("context_str_full") or ""),
                        "retrieval_stratum": stratum,
                        "semantic_any_supported": bool(semantic.get("semantic_any_supported")),
                        "semantic_any_partial_or_supported": bool(semantic.get("semantic_any_partial_or_supported")),
                        "semantic_any_contradicted": bool(semantic.get("semantic_any_contradicted")),
                        "gold_memory_ids": gold_ids,
                        "partial_memory_ids": partial_ids,
                        "other_memory_ids": other_ids,
                        "support_evidence_results": semantic.get("evidence_results") or [],
                        "case_rationale": semantic.get("case_rationale") or "",
                    }
                )

    if missing_semantic:
        raise RuntimeError(f"Missing semantic cache rows: {len(missing_semantic)}; first={missing_semantic[:5]}")
    return samples


def write_prompt_assets() -> None:
    prompt_dir = OUT_DIR / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "PROMPT_MEMOS.txt").write_text(PROMPT_MEMOS, encoding="utf-8")
    (prompt_dir / "judge_gold_only_prompt_template.txt").write_text(
        build_gold_only_judge_prompt(
            {"question": "{question}", "gold_answer": "{gold_answer}", "model_answer": "{model_answer}"}
        ),
        encoding="utf-8",
    )
    write_json(prompt_dir / "license_templates.json", LICENSE_TEMPLATES)


def write_run_config(samples: list[dict[str, Any]]) -> None:
    hashes = prompt_hashes()
    lines = [
        "experiment: e1_memos_full_oracle",
        f"root: {ROOT}",
        f"model: {MODEL}",
        "temperature: 0",
        "generation_max_tokens: 128",
        "judge_max_tokens: 256",
        f"seed: {SEED}",
        f"conditions: {', '.join(CONDITIONS)}",
        f"medium_qa: {MEDIUM_QA}",
        f"long_qa: {LONG_QA}",
        f"semantic_detail: {SEMANTIC_DETAIL}",
        f"sample_count: {len(samples)}",
        f"answer_prompt_hash: {hashes['answer_prompt_hash']}",
        f"judge_prompt_template_hash: {hashes['judge_prompt_template_hash']}",
        f"license_templates_hash: {hashes['license_templates_hash']}",
        "no_retriever_or_memory_store_changes: true",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "run_config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(samples: list[dict[str, Any]]) -> None:
    by_run = Counter(row["run_id"] for row in samples)
    by_stratum = Counter(row["retrieval_stratum"] for row in samples)
    partial_or_supported = by_stratum["strict_supported"] + by_stratum["partial_supported"]
    lines = [
        "# E1 Memos Full Sample Pool",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| memos_medium wrong+evidence | {by_run['memos_medium']} |",
        f"| memos_long wrong+evidence | {by_run['memos_long']} |",
        f"| total wrong+evidence | {len(samples)} |",
        f"| strict_supported | {by_stratum['strict_supported']} |",
        f"| partial_supported | {by_stratum['partial_supported']} |",
        f"| no_gold_retrieved | {by_stratum['no_gold_retrieved']} |",
        f"| partial_or_supported | {partial_or_supported} |",
        "",
        "## By Dataset And Stratum",
        "",
        "| run_id | strict_supported | partial_supported | no_gold_retrieved | total |",
        "|---|---:|---:|---:|---:|",
    ]
    for run_id in ("memos_medium", "memos_long"):
        rows = [row for row in samples if row["run_id"] == run_id]
        counts = Counter(row["retrieval_stratum"] for row in rows)
        lines.append(
            f"| {run_id} | {counts['strict_supported']} | {counts['partial_supported']} | {counts['no_gold_retrieved']} | {len(rows)} |"
        )
    (OUT_DIR / "sample_pool_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_counts(samples: list[dict[str, Any]]) -> None:
    by_run = Counter(row["run_id"] for row in samples)
    by_stratum = Counter(row["retrieval_stratum"] for row in samples)
    partial_or_supported = by_stratum["strict_supported"] + by_stratum["partial_supported"]
    checks = {
        "memos_medium": by_run["memos_medium"],
        "memos_long": by_run["memos_long"],
        "total": len(samples),
        "strict_supported": by_stratum["strict_supported"],
        "partial_or_supported": partial_or_supported,
    }
    mismatches = {key: (actual, EXPECTED_COUNTS[key]) for key, actual in checks.items() if actual != EXPECTED_COUNTS[key]}
    if mismatches:
        raise RuntimeError(f"Sample count mismatch: {mismatches}")


def main() -> None:
    samples = build_samples()
    validate_counts(samples)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "samples_memos_full.jsonl").open("w", encoding="utf-8") as f:
        for row in samples:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (OUT_DIR / "leakage_failures.jsonl").write_text("", encoding="utf-8")
    write_prompt_assets()
    write_run_config(samples)
    write_summary(samples)
    print(f"wrote {len(samples)} samples to {OUT_DIR / 'samples_memos_full.jsonl'}")


if __name__ == "__main__":
    main()
