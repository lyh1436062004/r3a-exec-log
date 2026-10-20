"""Assemble owned round 0075 artifacts; never stage, commit, or push implicitly."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "outputs" / "a2_mvp_v1"
LOG = ROOT / "r3a-exec-log"
ROUND = LOG / "runs" / "round_0075"
PREVIOUS = LOG / "runs" / "round_0074" / "artifacts"
SOURCES = ["a2_schema.py", "a2_stage0_adapter.py", "a2_stage1_estimator.py",
           "a2_stage2_decision.py", "a2_stage3_render.py", "a2_pipeline.py", "a2_arms.py",
           "a2_calibrate.py", "20_build_pool.py", "21_run_generation.py", "22_judge.py",
           "23_analyze.py", "24_intrinsic_eval.py", "25_build_longmemeval.py",
           "26_run_amendment01.py", "test_a2_invariants.py", "test_amendment01_workflow.py",
           "e1_memos_oracle_common.py", "00_verify_serializer.py", "_archive_amendment01.py",
           "04_analyze_memos_full.py", "audit_gold_evidence_semantic_retrieval.py",
           "CODEX_TASK_A2_MVP.md", "CODEX_TASK_A2_MVP_AMENDMENT_01.md"]
CHANGED = ["a2_calibrate.py", "21_run_generation.py", "23_analyze.py", "25_build_longmemeval.py",
           "test_a2_invariants.py", "26_run_amendment01.py", "test_amendment01_workflow.py",
           "_archive_amendment01.py"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def command(arguments: list[str], cwd: Path) -> str:
    return subprocess.check_output(arguments, cwd=cwd, encoding="utf-8", errors="strict").strip()


def audit_complete() -> dict:
    importlib.import_module("26_run_amendment01").verify_frozen()
    assert read_json(OUT / "analysis" / "full_source_serializer_verify.json")["passed"]
    for name in ("invariants_full", "amendment01_outer_regression"):
        checks = read_json(OUT / "analysis" / f"{name}.json")
        assert checks.get("failed", checks.get("failures", 0)) == 0
        assert checks.get("errors", 0) == 0
        assert checks.get("pending", 0) == 0
    primary = read_json(OUT / "analysis" / "memos__deepseek-chat_summary.json")
    required = set(importlib.import_module("a2_arms").MAIN_ARMS)
    rates = [r for r in primary["metrics"]["rates"] if r["arm"] in required]
    assert primary["n_pool"] == 4062 and {r["arm"] for r in rates} == required
    assert all(r["complete"] and r["n_evaluated"] == 4062 for r in rates)
    stage_e = {}
    for pool, n in (("mem0", 4476), ("memobase", 4940), ("supermemory", 184)):
        value = read_json(OUT / "analysis" / f"{pool}__deepseek-chat_summary.json")
        flips = [r for r in value["metrics"]["flips"] if r["arm"] in ("B1", "A2")]
        assert value["n_pool"] == n and {r["arm"] for r in flips} == {"B1", "A2"}
        assert all(r["n_paired"] == n and r["missing"] == 0 for r in flips)
        stage_e[pool] = flips
    subset = read_json(OUT / "analysis" / "memos__deepseek-chat__subset400_summary.json")
    expected = {"A2", "A2__lambda_o_0.3", "A2__lambda_o_0.6", "A2__lambda_o_2"}
    sensitivity = [r for r in subset["metrics"]["rates"] if r["arm"] in expected]
    assert {r["arm"] for r in sensitivity} == expected
    assert all(r["complete"] and r["n_evaluated"] == 400 for r in sensitivity)
    assert read_json(OUT / "analysis" / "memos__deepseek-chat__smoke_summary.json")["smoke"]["passed"]
    calibration = read_json(OUT / "calibration" / "memos.json")
    assert calibration["alpha"] == .20 and calibration["tau"] == .15 and not calibration["degenerate_flag"]
    assert len(read_json(OUT / "analysis" / "memos_failure_examples.json")) >= 5
    lme_pool = OUT / "pools" / "longmemeval_pool.jsonl"
    if lme_pool.exists():
        lme = read_json(OUT / "analysis" / "longmemeval__deepseek-chat_summary.json")
        relevant = [r for r in lme["metrics"]["rates"] if r["arm"] in ("B0", "B1", "A2")]
        assert {r["arm"] for r in relevant} == {"B0", "B1", "A2"} and all(r["complete"] for r in relevant)
    else:
        attempts = read_json(OUT / "analysis" / "longmemeval_acquisition_attempts.json")["attempts"]
        assert len(attempts) == 3 and all(r["status"] == "failed" for r in attempts)
    return {"main_rates": rates, "A2_vs_B1": [r for r in primary["metrics"]["mcnemar"] if r["arm"] == "A2" and r["reference"] == "B1"],
            "stage_E": stage_e, "LME_source_available": lme_pool.exists()}


def verify_blobs(head: bool = False) -> None:
    args = ["ls-tree", "-r", "--name-only", "HEAD", "--", "runs/round_0075"] if head else ["diff", "--cached", "--name-only", "--", "runs/round_0075"]
    names = command(["git", "-c", "core.quotepath=false", *args], LOG).splitlines()
    assert names, "No owned round blobs found; cannot claim a byte check passed"
    for name in names:
        data = subprocess.check_output(["git", "cat-file", "blob", ("HEAD:" if head else ":") + name], cwd=LOG)
        assert data == (LOG / name).read_bytes(), f"Staged bytes differ: {name}"
    print(json.dumps({"head_files_byte_exact" if head else "staged_files_byte_exact": len(names), "passed": True}))


def export_label_tables() -> None:
    analysis = importlib.import_module("23_analyze")
    arms = importlib.import_module("a2_arms").MAIN_ARMS
    for pool in ("memos", "longmemeval", "mem0", "memobase", "supermemory"):
        summary_path = OUT / "analysis" / f"{pool}__deepseek-chat_summary.json"
        if not summary_path.exists():
            continue
        summary = read_json(summary_path)
        selection = summary.get("selection_manifest")
        selected = set(summary["selected_case_ids"])
        required = arms if pool == "memos" else ("B0", "B1", "A2") if pool == "longmemeval" else ("B1", "A2")
        rows = []
        for arm in required:
            labels, _, _ = analysis.load_arm_cache(OUT, pool, arm, "deepseek-chat", selection)
            rejected = set(summary.get("rejected_or_stale_judgment_ids", {}).get(arm, []))
            for cid, value in sorted(labels.items()):
                if cid not in selected or cid in rejected:
                    continue
                record = {"case_id": cid, "arm": arm,
                          "sample_input_hash": value.get("sample_input_hash"),
                          "generation_cache_key": value.get("generation_cache_key", value.get("generation_input_hash"))}
                if pool in ("mem0", "memobase", "supermemory"):
                    record["rescued"] = analysis.label(value) == "correct"
                else:
                    record["judge_label"] = analysis.label(value)
                rows.append(record)
        importlib.import_module("20_build_pool").write_jsonl(OUT / "analysis" / f"{pool}_evaluation_labels_slim.jsonl", rows)


def assemble(status: str, blocker: str | None) -> None:
    existing = read_json(ROUND / "run_summary.json")
    assert existing["task"] == "Execute CODEX_TASK_A2_MVP_AMENDMENT_01 through mandatory Stage E"
    verification = audit_complete() if status == "complete" else {"external_blocker": blocker}
    if status != "complete":
        assert blocker, "Partial archive requires an actual external blocker"
    export_label_tables()
    source_hashes = {name: digest(HERE / name) for name in SOURCES}
    write_json(OUT / "source_file_hashes.json", {"scope": "amendment01 final source checkpoint", "sha256": source_hashes})
    paths = [HERE / name for name in SOURCES]
    paths.extend(OUT / name for name in ("RESULTS.md", "RESULTS_subset400.md", "preflight.json", "run_config.json",
                                       "source_file_hashes.json", "leakage_failures.jsonl", "longmemeval_blocker.json", "api_run_blocker.json"))
    for folder, patterns in (("analysis", ("*.json", "*.csv", "*.md", "*_evaluation_labels_slim.jsonl")), ("calibration", ("*.json",)),
                             ("pools", ("*_summary.json", "*_equivalence.json"))):
        for pattern in patterns:
            paths.extend((OUT / folder).glob(pattern))
    paths.extend((OUT / "datasets" / "longmemeval_cleaned_s").glob("source_lock.json"))
    paths = sorted({p for p in paths if p.is_file()})
    # Secret values are compared in memory; never printed or persisted.
    from dotenv import dotenv_values
    common = importlib.import_module("e1_memos_oracle_common")
    secrets = [str(v).encode("utf-8") for k, v in dotenv_values(common.ENV_PATH).items()
               if v and any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD")) and len(str(v)) >= 12]
    manifest = []
    for path in paths:
        assert path.suffix.lower() not in (".xlsx", ".key", ".pem") and path.name != ".env"
        data = path.read_bytes()
        assert len(data) < 15_000_000, f"Unexpected large artifact: {path.name}"
        assert not any(secret in data for secret in secrets), f"Secret scan hit: {path.name}"
        assert re.search(rb"(?<![A-Za-z0-9_])(?:sk-|hf_)[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}", data) is None, "Possible credential-shaped artifact; do not upload"
        relative = path.relative_to(ROOT)
        destination = ROUND / "artifacts" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        assert destination.read_bytes() == data
        manifest.append({"path": relative.as_posix(), "bytes": len(data), "sha256": digest(path)})
    project_status = command(["git", "status", "--short"], ROOT)
    changes = [f"Modified/new task source: 脚本/3.0/{name}" for name in CHANGED]
    changes.append("Unmodified user amendment archived: 脚本/3.0/CODEX_TASK_A2_MVP_AMENDMENT_01.md")
    changes.extend("Artifact: " + entry["path"] for entry in manifest if entry["path"].startswith("outputs/"))
    changes += ["Seven core source files unchanged; memory store and memos retriever unchanged.",
                "Unrelated project changes preserved and not staged.", "Final project git status --short:", project_status]
    (ROUND / "file_change.txt").write_text("\n".join(changes) + "\n", encoding="utf-8")
    difference = []
    for name in CHANGED:
        before = PREVIOUS / "脚本" / "3.0" / name
        old = before.read_text(encoding="utf-8").splitlines(keepends=True) if before.exists() else []
        new = (HERE / name).read_text(encoding="utf-8").splitlines(keepends=True)
        difference.extend(difflib.unified_diff(old, new, fromfile="round_0074/" + name, tofile="round_0075/" + name))
    (ROUND / "diff.txt").write_text("".join(difference), encoding="utf-8")
    write_json(ROUND / "artifact_manifest.json", manifest)
    summary = {**existing, "status": status, "verification": verification, "modified_source_files": CHANGED,
               "output_files": [entry["path"] for entry in manifest if entry["path"].startswith("outputs/")],
               "source_sha256": source_hashes, "recorded_tokens": importlib.import_module("23_analyze").cache_usage(OUT),
               "repo": "r3a-exec-log", "artifact_count": len(manifest), "secret_scan_passed": True,
               "byte_preservation": "round-local * -text and artifacts/** -text; verify staged and committed blobs after renormalization",
               "excluded": ["credentials", "raw pools/datasets", "generation/context/estimator/support caches", "attempt ledgers", "Python caches"],
               "final_project_git_status_short": project_status}
    summary.pop("note", None)
    write_json(ROUND / "run_summary.json", summary)
    assert not any(secret in path.read_bytes() for path in ROUND.rglob("*") if path.is_file() for secret in secrets), "Secret scan hit owned round metadata"
    print(json.dumps({"round": "round_0075", "status": status, "artifacts": len(manifest),
                      "bytes": sum(r["bytes"] for r in manifest), "secret_scan_passed": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", choices=("complete", "blocked_external"), default="complete")
    parser.add_argument("--blocker")
    parser.add_argument("--verify-index", action="store_true")
    parser.add_argument("--verify-head", action="store_true")
    args = parser.parse_args()
    if args.verify_index or args.verify_head:
        verify_blobs(args.verify_head)
    else:
        assemble(args.status, args.blocker)
