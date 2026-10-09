"""Task-book empirical risk gate: exact split/formula, no invented guarantee.

This boundary script may read evaluation outcomes, unlike the deployment stages.
The empirical cumulative error ratio is NOT mathematically monotone in tau.
We retain the specified formula and expose the required monotonicity check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from a2_stage0_adapter import adapt
from a2_stage1_estimator import DEFAULT_MODEL, estimate_cache_key, estimate_cache_path
from e1_memos_oracle_common import ROOT, SEED, read_jsonl, sha256_text, write_csv, write_json

OUT_DIR = ROOT / "outputs" / "a2_mvp_v1"
ALPHAS = (0.05, 0.10, 0.20, 0.30)
VERSION = "task-book-exact-empirical-gate-v1"


def calibration_split(case_id: str) -> str:
    return "cal" if int(hashlib.sha256(str(case_id).encode("utf-8")).hexdigest()[:8], 16) % 2 == 0 else "test"


def validated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result, seen = [], set()
    for row in rows:
        case_id = str(row["case_id"])
        if case_id in seen:
            raise ValueError(f"Duplicate calibration identity: {case_id}")
        seen.add(case_id)
        wrong = row.get("baseline_wrong")
        if wrong not in (False, True, 0, 1):
            raise ValueError(f"Calibration requires an explicit boolean outcome: {case_id}")
        failed = bool(row.get("failed", False))
        risk = 0.0 if failed else float(row["risk"])
        if not math.isfinite(risk) or not 0.0 <= risk <= 1.0:
            raise ValueError(f"Invalid calibration risk: {case_id}")
        result.append({**row, "case_id": case_id, "risk": risk,
                       "baseline_wrong": bool(wrong), "failed": failed,
                       "split": calibration_split(case_id)})
    return result


def threshold_metrics(rows: list[dict[str, Any]], tau: float) -> dict[str, Any]:
    threshold = float(tau)
    selected = [row for row in rows if row["risk"] <= threshold]
    wrong = sum(row["baseline_wrong"] for row in selected)
    # Exactly section 7.3, including max(1,n_noop); no smoothing or envelopes.
    return {"tau": threshold, "coverage": len(selected) / max(1, len(rows)),
            "noop_err": wrong / max(1, len(selected)), "n": len(rows),
            "n_noop": len(selected), "n_noop_wrong": wrong}


def threshold_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checked = validated_rows(rows)
    return [threshold_metrics(checked, tau)
            for tau in [-math.inf, *sorted({row["risk"] for row in checked})]]


def monotonicity_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    curve = threshold_curve(rows)
    return [{"previous_tau": left["tau"], "tau": right["tau"],
             "previous_noop_err": left["noop_err"], "noop_err": right["noop_err"]}
            for left, right in zip(curve, curve[1:])
            if right["noop_err"] + 1e-12 < left["noop_err"]]


def assert_noop_error_monotonic(rows: list[dict[str, Any]]) -> None:
    violations = monotonicity_violations(rows)
    assert not violations, (
        "Task-book invariant 10 failed: raw empirical noop_err decreases with tau; "
        f"n_violations={len(violations)}, first={violations[:1]}. "
        "The specified cumulative ratio has not been altered."
    )


def calibrate_rows(rows: list[dict[str, Any]], alpha: float = 0.10) -> dict[str, Any]:
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("alpha must be finite and in [0,1]")
    checked = validated_rows(rows)
    cal = [row for row in checked if row["split"] == "cal"]
    test = [row for row in checked if row["split"] == "test"]
    if not cal:
        raise ValueError("No calibration-split observations; refusing a guessed threshold")
    curve = threshold_curve(cal)
    valid = [point for point in curve if point["n_noop"] > 0 and point["noop_err"] <= alpha]
    chosen = max(valid, key=lambda point: (point["coverage"], point["tau"])) if valid else curve[0]
    return {"alpha": alpha, "tau": chosen["tau"], "coverage": chosen["coverage"],
            "noop_err": chosen["noop_err"], "n_cal": len(cal),
            "n_cal_baseline_wrong": sum(row["baseline_wrong"] for row in cal),
            "n_cal_noop": chosen["n_noop"], "degenerate_flag": chosen["tau"] == -math.inf,
            "test": threshold_metrics(test, chosen["tau"]),
            "monotonicity_violations": monotonicity_violations(cal),
            "n_estimator_failed": sum(row["failed"] for row in checked),
            "failure_override_note": "failed estimates bypass even tau=-inf; curve above is the exact risk<=tau formula",
            "guarantee_note": "Empirical cal-split selection per task book, not a distribution-free finite-sample conformal proof"}


def _label(row: dict[str, Any]) -> str:
    raw = str(row.get("judge_label") or row.get("label") or "").lower()
    return {"c": "correct", "h": "hallucination", "o": "omission"}.get(raw, raw)


def load_calibration_rows(pool: str, out_dir: Path = OUT_DIR,
                          generator: str = DEFAULT_MODEL,
                          samples: list[dict[str, Any]] | None = None,
                          baseline_source: str = "fresh_b0") -> list[dict[str, Any]]:
    samples = samples if samples is not None else read_jsonl(out_dir / "pools" / f"{pool}_pool.jsonl")
    if not samples:
        raise FileNotFoundError(f"Missing/nonempty calibration pool: {pool}")
    verdicts, generations = {}, {}
    if baseline_source == "fresh_b0":
        path = out_dir / "verdicts" / pool / f"B0__{generator}.jsonl"
        verdicts = {str(row["case_id"]): row for row in read_jsonl(path)
                    if row.get("ok", True) and not row.get("error")
                    and _label(row) in {"correct", "hallucination", "omission"}}
        generation_path = out_dir / "generations" / pool / f"B0__{generator}.jsonl"
        generations = {str(row["case_id"]): row for row in read_jsonl(generation_path)
                       if row.get("ok", True) and not row.get("error")}
    elif baseline_source != "archived_pilot":
        raise ValueError("baseline_source must be fresh_b0 or explicitly archived_pilot")
    rows, missing = [], []
    for sample in samples:
        cid = str(sample["case_id"])
        records = adapt(sample["raw_memories"], sample.get("system_kind", pool))
        estimate_path = estimate_cache_path(cid, pool, out_dir)
        if not estimate_path.exists():
            missing.append(f"{cid}:estimate")
            continue
        estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
        expected = estimate_cache_key(sample["question"], records, DEFAULT_MODEL)
        if estimate.get("input_hash") != expected:
            missing.append(f"{cid}:stale_estimate")
            continue
        if baseline_source == "archived_pilot":
            label = str(sample.get("baseline_label") or sample.get("baseline_verdict") or "").lower()
            outcome_hash = sha256_text(label)
        else:
            verdict = verdicts.get(cid)
            generation = generations.get(cid)
            if verdict is None or generation is None:
                missing.append(f"{cid}:fresh_B0_generation_or_verdict")
                continue
            if (generation.get("context_hash") != sha256_text(sample["context_str_full"])
                    or verdict.get("generation_cache_key", verdict.get("gen_cache_key")) != generation.get("cache_key")):
                missing.append(f"{cid}:stale_B0_generation_or_verdict")
                continue
            label = _label(verdict)
            outcome_hash = str(verdict.get("cache_key") or verdict.get("judge_cache_key") or sha256_text(json.dumps(verdict, sort_keys=True)))
        if label not in {"correct", "hallucination", "omission"}:
            missing.append(f"{cid}:invalid_outcome")
            continue
        rows.append({"case_id": cid, "risk": estimate["risk"], "failed": estimate["failed"],
                     "baseline_wrong": label != "correct", "estimate_input_hash": expected,
                     "outcome_hash": outcome_hash, "baseline_source": baseline_source})
    if missing:
        raise RuntimeError(f"Calibration incomplete/stale: {len(missing)} rows, examples={missing[:8]}")
    return rows


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        if value == -math.inf:
            return "-inf"
        raise ValueError("Refusing nonfinite numeric report value")
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def calibrate_pool(pool: str, out_dir: Path = OUT_DIR, alpha: float = 0.10,
                   rows: list[dict[str, Any]] | None = None, scope: str = "full") -> dict[str, Any]:
    print(f"Budget: calibration calls=0; pool={pool}, alpha={alpha}, scope={scope}", flush=True)
    rows = load_calibration_rows(pool, out_dir) if rows is None else rows
    checked = validated_rows(rows)
    payload = calibrate_rows(checked, alpha)
    identity = {"version": VERSION, "rows": sorted(checked, key=lambda r: r["case_id"]),
                "alpha": alpha, "scope": scope, "seed": SEED}
    payload.update({"pool": pool, "scope": scope, "version": VERSION, "seed": SEED,
                    "input_hash": sha256_text(json.dumps(identity, ensure_ascii=False, sort_keys=True)),
                    "baseline_sources": sorted({row.get("baseline_source", "caller_supplied") for row in checked}),
                    "n_total": len(checked)})
    write_json(out_dir / "calibration" / f"{pool}.json", json_safe(payload))
    alpha_rows = []
    for level in ALPHAS:
        result = calibrate_rows(checked, level)
        alpha_rows.append({"alpha": level, "tau": json_safe(result["tau"]),
                           "cal_coverage": result["coverage"], "cal_noop_err": result["noop_err"],
                           "test_coverage": result["test"]["coverage"], "test_noop_err": result["test"]["noop_err"],
                           "n_cal": result["n_cal"], "n_test": result["test"]["n"],
                           "degenerate_flag": result["degenerate_flag"], "scope": scope})
    write_csv(out_dir / "analysis" / f"{pool}_calibration_curve.csv", alpha_rows, list(alpha_rows[0]))
    write_json(out_dir / "analysis" / f"{pool}_calibration_monotonicity.json",
               json_safe({"required_invariant": 10, "passed": not payload["monotonicity_violations"],
                          "violations": payload["monotonicity_violations"], "scope": scope,
                          "formula_unchanged": True}))
    config_path = out_dir / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config.setdefault("seed", SEED)
    config.setdefault("calibration", {})[pool] = json_safe({key: payload[key] for key in
        ("alpha", "tau", "scope", "version", "input_hash", "n_total", "baseline_sources", "degenerate_flag")})
    write_json(config_path, config)
    print(json.dumps(json_safe(payload), ensure_ascii=False, indent=2), flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--rows", type=Path, help="explicit input-hashed rows for a disclosed pilot")
    parser.add_argument("--scope", default="full")
    parser.add_argument("--assert-monotonic", action="store_true")
    args = parser.parse_args()
    rows = read_jsonl(args.rows) if args.rows else load_calibration_rows(args.pool, args.out_dir)
    result = calibrate_pool(args.pool, args.out_dir, args.alpha, rows, args.scope)
    if args.assert_monotonic:
        assert_noop_error_monotonic([row for row in rows if calibration_split(row["case_id"]) == "cal"])
    if result["degenerate_flag"]:
        print("WARNING: gate degenerate to tau=-inf (failed-estimation safe bypass still applies)", flush=True)


if __name__ == "__main__":
    main()
