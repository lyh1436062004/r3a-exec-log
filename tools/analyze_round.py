from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
ANALYSIS_DIR = ROOT / "analysis"

BANNED_FULL_REPORT_TERMS = [
    "post-filter precision",
    "post_filter_precision",
    "true retention",
    "false rejection",
    "false triggered",
]

LEAKAGE_TERMS = [
    "gold_answer",
    "question_type",
    "baseline_label",
]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def find_latest_round() -> Path | None:
    if not RUNS_DIR.exists():
        return None
    rounds = sorted(
        [p for p in RUNS_DIR.iterdir() if p.is_dir() and re.match(r"round_\d{4}$", p.name)]
    )
    return rounds[-1] if rounds else None


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_json_error": str(exc)}


def parse_percent_fraction(text: str, label: str) -> str | None:
    # Matches:
    # true retention: 9/18 (50.00%)
    pattern = rf"{re.escape(label)}\s*:\s*([0-9]+/[0-9]+\s*\([0-9.]+%\))"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1) if m else None


def parse_integer_line(text: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*:\s*([0-9]+)"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1) if m else None


def latest_existing_report(name: str) -> Path | None:
    candidates = list(ROOT.rglob(name))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]


def analyze_selected_report() -> dict[str, Any]:
    path = latest_existing_report("r3a_v2_selected_evidence_replay_report.md")
    text = read_text(path) if path else ""
    return {
        "path": str(path.relative_to(ROOT)) if path else None,
        "true_retention": parse_percent_fraction(text, "true retention"),
        "false_rejection": parse_percent_fraction(text, "false rejection"),
        "false_retention": parse_percent_fraction(text, "false retention"),
        "retained_precision_strict": parse_percent_fraction(text, "retained precision strict"),
        "retained_acceptable_rate": parse_percent_fraction(text, "retained acceptable rate"),
        "kept_count": parse_integer_line(text, "v2 kept count") or parse_integer_line(text, "kept count"),
    }


def analyze_full_report() -> dict[str, Any]:
    path = latest_existing_report("r3a_v2_full_selector_replay_report.md")
    text = read_text(path) if path else ""
    banned_hits = [term for term in BANNED_FULL_REPORT_TERMS if term.lower() in text.lower()]
    return {
        "path": str(path.relative_to(ROOT)) if path else None,
        "v2_triggered_count": parse_integer_line(text, "v2 triggered count"),
        "matched_original_v1_selected": parse_percent_fraction(text, "matched_original_v1_selected"),
        "banned_metric_terms_found": banned_hits,
        "full_report_metric_protocol_ok": not banned_hits,
    }


def check_selector_leakage() -> dict[str, Any]:
    selector_paths = list(ROOT.rglob("r3a_v2_selector.py"))
    hits: dict[str, list[str]] = {}
    for path in selector_paths:
        text = read_text(path)
        found = [term for term in LEAKAGE_TERMS if term in text]
        if found:
            hits[str(path.relative_to(ROOT))] = found
    return {
        "selector_files_checked": [str(p.relative_to(ROOT)) for p in selector_paths],
        "leakage_hits": hits,
        "leakage_ok": not hits,
    }


def summarize_file_changes(round_dir: Path | None) -> dict[str, Any]:
    if not round_dir:
        return {"round": None, "file_change_txt": None, "run_summary": {}}
    file_change = read_text(round_dir / "file_change.txt")
    run_summary = load_json(round_dir / "run_summary.json")
    return {
        "round": round_dir.name,
        "file_change_txt": file_change.strip().splitlines(),
        "run_summary": run_summary,
    }


def write_reports(result: dict[str, Any]) -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    round_name = result.get("round", "unknown")
    json_path = ANALYSIS_DIR / f"{round_name}_analysis.json"
    md_path = ANALYSIS_DIR / f"{round_name}_analysis.md"
    latest_json = ANALYSIS_DIR / "latest_round_analysis.json"
    latest_md = ANALYSIS_DIR / "latest_round_analysis.md"

    json_text = json.dumps(result, ensure_ascii=False, indent=2)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    latest_json.write_text(json_text + "\n", encoding="utf-8")

    selected = result.get("selected_evidence_report", {})
    full = result.get("full_selector_report", {})
    leakage = result.get("selector_leakage_check", {})

    md = [
        f"# R3a Round Analysis: {round_name}",
        "",
        "## File Changes",
        "",
    ]
    for line in result.get("file_change_txt", []) or []:
        md.append(f"- `{line}`")
    if not result.get("file_change_txt"):
        md.append("- none")
    md.extend([
        "",
        "## Selected-Evidence Replay",
        "",
        f"- report: `{selected.get('path')}`",
        f"- true retention: {selected.get('true_retention')}",
        f"- false rejection: {selected.get('false_rejection')}",
        f"- false retention: {selected.get('false_retention')}",
        f"- retained precision strict: {selected.get('retained_precision_strict')}",
        f"- retained acceptable rate: {selected.get('retained_acceptable_rate')}",
        f"- kept count: {selected.get('kept_count')}",
        "",
        "## Full-Selector Replay",
        "",
        f"- report: `{full.get('path')}`",
        f"- v2 triggered count: {full.get('v2_triggered_count')}",
        f"- matched original v1 selected: {full.get('matched_original_v1_selected')}",
        f"- metric protocol ok: {full.get('full_report_metric_protocol_ok')}",
        f"- banned metric terms found: {full.get('banned_metric_terms_found')}",
        "",
        "## Leakage Check",
        "",
        f"- selector files checked: {leakage.get('selector_files_checked')}",
        f"- leakage ok: {leakage.get('leakage_ok')}",
        f"- leakage hits: {leakage.get('leakage_hits')}",
        "",
    ])
    md_text = "\n".join(md) + "\n"
    md_path.write_text(md_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")


def main() -> None:
    latest_round = find_latest_round()
    changes = summarize_file_changes(latest_round)

    result = {
        "round": changes.get("round"),
        "file_change_txt": changes.get("file_change_txt"),
        "run_summary": changes.get("run_summary"),
        "selected_evidence_report": analyze_selected_report(),
        "full_selector_report": analyze_full_report(),
        "selector_leakage_check": check_selector_leakage(),
    }

    write_reports(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
