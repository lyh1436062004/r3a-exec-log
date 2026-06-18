# AGENTS.md

This Codex session must push every completed task to GitHub r3a-exec-log.

## Mandatory GitHub Sync Rule

For every completed task in this Codex window, the agent must sync the round to the GitHub execution-log repository `r3a-exec-log` before ending the task. Use the existing local clone if present; clone or configure the remote if needed.

After each task:
- Run `git status --short` in the project workspace.
- Create the next `runs/round_XXXX/` directory in `r3a-exec-log` without overwriting existing rounds.
- Write `run_summary.json`, `file_change.txt`, and `diff.txt` for the round.
- Copy or commit the necessary task artifacts to `r3a-exec-log`, including changed code, new tests, replay reports, key jsonl/csv/md outputs, and the round files.
- Do not upload `.env`, `KEY*.xlsx`, `*.key`, `*.pem`, API keys, large unrelated raw data, caches, `__pycache__`, or `.pytest_cache`.
- Commit with `git commit -m "round_XXXX: <short task summary>"`.
- Push to `origin main`. If push fails, stop and report the error.

Final replies for tasks must include: round number, GitHub repo name, commit hash, pushed yes/no, whether GitHub Actions triggered, modified files, output files, and final `git status --short`.

This file provides guidance to AI coding agents (Codex, Cursor, Copilot, etc.) working in this repository.

## Project Identity

- **Name**: A2 — 检索后记忆准入控制器
- **Domain**: Agent Long-Term Memory Hallucination Suppression
- **Version**: A2-v0.4
- **Primary Language**: Python (conda env: `D:\conda_envs\o1`)

## Key Documents

Start with these files to understand the project:
1. `README.md` — complete project overview, methodology, and current conclusions
2. `research_questions.md` — current research questions and boundary claims
3. `Research Roadmap.md` — roadmap from A2-v0.4 to paper draft

## Script Conventions

- Active scripts: `脚本/2.0-修复版/`
- Run via: `& "D:\conda_envs\o1\python.exe" "<script_path>"`
- Experiment scripts follow naming: `run_<system>_<dataset>_baseline.py`
- Diagnostic scripts prefixed with `_` (e.g., `_check_progress.py`, `_xreport_*.py`)

## Constraints

- Never modify the memory store or retriever
- Never use HaluMem distractor labels as inference features
- A2 is a post-retrieval gating controller, not a memory re-writer
- Do not claim generality beyond memory conflict / false-premise correction
