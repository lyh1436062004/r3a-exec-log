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
    "v2 false positives",
]

LEAKAGE_TERMS = [
    "gold_answer",
    "question_type",
    "baseline_label",
]


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


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
        return json.loads(read_text(path))
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
    canonical = ROOT / "outputs" / "r3a_v2_dev_replay" / name
    if canonical.exists():
        return canonical
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
        "matched_original_v1_selected_count": parse_integer_line(text, "matched_original_v1_selected count"),
        "matched_original_v1_selected": parse_percent_fraction(text, "matched_original_v1_selected"),
        "banned_metric_terms_found": banned_hits,
        "full_report_metric_protocol_ok": not banned_hits,
    }


def check_metric_consistency(
    run_summary: dict[str, Any],
    full_report_text: str,
    selected_report_text: str,
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []

    def add_mismatch(metric: str, expected: Any, actual: Any) -> None:
        mismatches.append({
            "metric": metric,
            "run_summary_value": expected,
            "report_value": actual,
        })

    full_summary = (
        run_summary.get("dev_replay_summary", {})
        .get("full_selector", {})
    )
    selected_summary = (
        run_summary.get("dev_replay_summary", {})
        .get("selected", {})
    )

    expected_triggered = full_summary.get("v2_triggered_count")
    actual_triggered = parse_integer_line(full_report_text, "v2 triggered count")
    actual_triggered_int = int(actual_triggered) if actual_triggered is not None else None
    if expected_triggered != actual_triggered_int:
        add_mismatch("full_selector.v2_triggered_count", expected_triggered, actual_triggered_int)

    expected_matched = full_summary.get("matched_original_v1_selected_count")
    actual_matched = parse_integer_line(full_report_text, "matched_original_v1_selected count")
    actual_matched_int = int(actual_matched) if actual_matched is not None else None
    if expected_matched != actual_matched_int:
        add_mismatch(
            "full_selector.matched_original_v1_selected_count",
            expected_matched,
            actual_matched_int,
        )

    expected_kept = selected_summary.get("kept_count")
    actual_kept = (
        parse_integer_line(selected_report_text, "v2 kept count")
        or parse_integer_line(selected_report_text, "kept count")
    )
    actual_kept_int = int(actual_kept) if actual_kept is not None else None
    if expected_kept != actual_kept_int:
        add_mismatch("selected.kept_count", expected_kept, actual_kept_int)

    return {
        "metric_consistency_ok": not mismatches,
        "mismatches": mismatches,
    }


def check_selector_leakage() -> dict[str, Any]:
    ignored_dirs = {"runs", "outputs", "analysis", ".git"}
    selector_paths = [
        path for path in ROOT.rglob("r3a_v2_selector.py")
        if not any(part in ignored_dirs for part in path.relative_to(ROOT).parts)
    ]
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
    consistency = result.get("metric_consistency_check", {})
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
        f"- matched_original_v1_selected count: {full.get('matched_original_v1_selected_count')}",
        f"- matched original v1 selected: {full.get('matched_original_v1_selected')}",
        f"- full report metric protocol ok: {full.get('full_report_metric_protocol_ok')}",
        f"- banned metric terms found: {full.get('banned_metric_terms_found')}",
        "",
        "## Metric Consistency",
        "",
        f"- metric consistency ok: {consistency.get('metric_consistency_ok')}",
        f"- mismatches: {consistency.get('mismatches')}",
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
    selected_report_path = latest_existing_report("r3a_v2_selected_evidence_replay_report.md")
    full_report_path = latest_existing_report("r3a_v2_full_selector_replay_report.md")
    selected_report_text = read_text(selected_report_path) if selected_report_path else ""
    full_report_text = read_text(full_report_path) if full_report_path else ""

    result = {
        "round": changes.get("round"),
        "file_change_txt": changes.get("file_change_txt"),
        "run_summary": changes.get("run_summary"),
        "selected_evidence_report": analyze_selected_report(),
        "full_selector_report": analyze_full_report(),
        "metric_consistency_check": check_metric_consistency(
            changes.get("run_summary") or {},
            full_report_text,
            selected_report_text,
        ),
        "selector_leakage_check": check_selector_leakage(),
    }

    write_reports(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
