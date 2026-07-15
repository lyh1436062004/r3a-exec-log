from __future__ import annotations
import json
from pathlib import Path

SRC = Path(r"D:\幻觉\outputs\e1_memos_generation_failure_oracle_v1\case_summary.jsonl")
OUTDIR = Path(r"D:\幻觉\临时\人工审查\审查生成错误率\audit_work")
OUTDIR.mkdir(parents=True, exist_ok=True)

rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
print("loaded cases:", len(rows))

def pick(r):
    return {
        "case_id": r.get("case_id"),
        "dataset": r.get("dataset"),
        "question_type": r.get("question_type"),
        "question": r.get("question"),
        "gold_answer": r.get("gold_answer"),
        "gold_evidence_rendered": r.get("gold_evidence_rendered") or "",
        "run_1_answer": r.get("run_1_answer"),
        "run_2_answer": r.get("run_2_answer"),
        "run_3_answer": r.get("run_3_answer"),
        "source_ua3_answer": r.get("source_ua3_answer"),
        "machine_ref": {
            "sufficiency_verdict": r.get("sufficiency_verdict"),
            "sufficiency_rationale": r.get("sufficiency_rationale"),
            "run_1_judge_label": r.get("run_1_judge_label"),
            "run_2_judge_label": r.get("run_2_judge_label"),
            "run_3_judge_label": r.get("run_3_judge_label"),
            "automatic_classification": r.get("automatic_classification"),
        },
    }

BATCH = 30
batches = [rows[i:i+BATCH] for i in range(0, len(rows), BATCH)]
manifest = []
for idx, b in enumerate(batches, start=1):
    fp = OUTDIR / f"batch_{idx:02d}_in.json"
    data = [pick(r) for r in b]
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest.append({"batch": idx, "file": str(fp), "n": len(data),
                     "first": data[0]["case_id"], "last": data[-1]["case_id"]})
(OUTDIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print("batches:", len(batches))
for m in manifest:
    print(m["batch"], m["n"], m["first"], "->", m["last"])
