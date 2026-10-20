"""Sequential, resumable outer workflow for the authorized amendment 01.

No estimator, decision, rendering, retrieval, or scoring rules are changed here.
Each paid generation phase retains the existing 30,000-call budget guard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "outputs" / "a2_mvp_v1"
REFERENCE = HERE.parents[1] / "r3a-exec-log" / "runs" / "round_0073" / "artifacts" / "脚本" / "3.0"
CORE = ("a2_schema.py", "a2_stage0_adapter.py", "a2_stage1_estimator.py",
        "a2_stage2_decision.py", "a2_stage3_render.py", "a2_pipeline.py", "a2_arms.py")
POOL_SHA = "d7cee7d676670a3d37e82b9dd82118cc1176a86ccb3e1538079c29adfb43c6c8"
PROGRESS = re.compile(r"^(generation|judged|estimates) completed=(\d+)/(\d+)")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_frozen() -> None:
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    mismatches = [name for name in CORE if digest(HERE / name) != digest(REFERENCE / name)]
    if mismatches:
        raise RuntimeError(f"Frozen controller mismatch: {mismatches}")
    if digest(OUT / "pools" / "memos_pool.jsonl") != POOL_SHA:
        raise RuntimeError("Frozen memos pool hash mismatch")
    if (OUT / "leakage_failures.jsonl").read_text(encoding="utf-8").strip():
        raise RuntimeError("Leakage check hit; workflow must stop")
    serializer = OUT / "analysis" / "full_source_serializer_verify.json"
    if serializer.exists() and json.loads(serializer.read_text(encoding="utf-8")).get("passed") is not True:
        raise RuntimeError("Source serializer hard gate failed")


def workflow() -> list[tuple[str, list[str]]]:
    stages: list[tuple[str, list[str]]] = []
    def pair(name: str, pool: str, arms: str, extra: list[str] | None = None) -> None:
        selection = extra or []
        common = ["--pool", pool, "--arm", arms, "--generator", "deepseek-chat"]
        stages.append((name + "_generation", ["21_run_generation.py", *common, *selection, "--alpha", "0.20", "--yes"]))
        # tau/alpha are generation-only options, never judge options.
        judge_selection = [value for value in selection]
        if "--tau" in judge_selection:
            index = judge_selection.index("--tau")
            del judge_selection[index:index + 2]
        stages.append((name + "_judge", ["22_judge.py", *common, *judge_selection, "--yes"]))
        analyze_selection = (["--subset", judge_selection[judge_selection.index("--subset") + 1]]
                             if "--subset" in judge_selection else [])
        stages.append((name + "_analysis", ["23_analyze.py", "--pool", pool,
                                             "--generator", "deepseek-chat", *analyze_selection]))
    pair("full_group1", "memos", "B0,B1,B2")
    pair("full_group2", "memos", "A2,A2-nogate,A2-nosal")
    pair("full_group3", "memos", "A2-nolic,A2-noblock")
    stages.append(("intrinsic", ["24_intrinsic_eval.py", "--pool", "memos"]))
    for weight in ("0.3", "0.6", "1.0", "2.0"):
        pair("sensitivity_" + weight, "memos", "A2", ["--subset", "400", "--lambda-o", weight])
    stages.append(("longmemeval_acquisition", ["25_build_longmemeval.py", "--amendment01", "--yes"]))
    pair("longmemeval", "longmemeval", "B0,B1,A2", ["--tau", "0.15"])
    for pool in ("mem0", "memobase", "supermemory"):
        pair("stageE_" + pool, pool, "B1,A2")
    stages.append(("final_memos_analysis", ["23_analyze.py", "--pool", "memos", "--generator", "deepseek-chat"]))
    stages.append(("final_report", ["23_analyze.py", "--report"]))
    return stages


def execute(name: str, arguments: list[str], history: dict) -> None:
    verify_frozen()
    event = {"stage": name, "arguments": arguments, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
             "status": "running"}
    history["events"].append(event)
    journal = OUT / "analysis" / "amendment01_workflow.json"
    write_json(journal, history)
    print(f"WORKFLOW start={name}", flush=True)
    child_env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    process = subprocess.Popen([sys.executable, "-u", *arguments], cwd=HERE, env=child_env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding="utf-8", errors="replace")
    tail: list[str] = []
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.rstrip()
        tail.append(line)
        tail = tail[-12:]
        match = PROGRESS.match(line)
        if match:
            count, total = int(match[2]), int(match[3])
            if count % 250 == 0 or count == total or "failures=0" not in line and match[1] != "estimates":
                print(f"{name}: {line}", flush=True)
        elif line.startswith(("Budget:", "Traceback", "RuntimeError", "ValueError", "WORKFLOW")):
            print(line, flush=True)
    code = process.wait()
    event.update({"exit_code": code, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                  "status": "completed" if code == 0 else "failed"})
    if code:
        event["diagnostic_tail"] = tail
    write_json(journal, history)
    print(f"WORKFLOW finish={name} exit={code}", flush=True)
    if code:
        raise RuntimeError(f"Stage {name} exited {code}; preserve caches and inspect workflow journal")
    verify_frozen()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-at", default="full_group1_generation")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    stages = workflow()
    names = [name for name, _ in stages]
    if args.start_at not in names:
        parser.error("Unknown --start-at stage")
    selected = stages[names.index(args.start_at):]
    print(json.dumps({"sequential_stages": selected, "paid_phase_limit": 30000,
                      "workers_per_script": 12, "main_alpha": 0.20, "fixed_memos_tau": 0.15}, ensure_ascii=False), flush=True)
    if not args.yes:
        return
    verify_frozen()
    journal = OUT / "analysis" / "amendment01_workflow.json"
    history = json.loads(journal.read_text(encoding="utf-8")) if journal.exists() else {"amendment": "01", "events": []}
    for name, arguments in selected:
        if name.startswith("longmemeval_") and name != "longmemeval_acquisition" and not (OUT / "pools" / "longmemeval_pool.jsonl").exists():
            print(f"WORKFLOW skip={name}: source unavailable after budgeted acquisition; continue mandatory E", flush=True)
            history["events"].append({"stage": name, "status": "skipped_source_unavailable"})
            write_json(journal, history)
            continue
        execute(name, arguments, history)
    history["workflow_commands_completed"] = True
    write_json(journal, history)
    print("WORKFLOW commands completed; scores/completeness still require final artifact audit", flush=True)


if __name__ == "__main__":
    main()
