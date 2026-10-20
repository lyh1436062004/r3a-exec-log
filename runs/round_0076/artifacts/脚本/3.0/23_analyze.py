"""Analyze real A2 caches; zero LLM calls, no imputation of missing outcomes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import importlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from a2_schema import ACTIONS

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "a2_mvp_v1"
OLD_DIR = ROOT / "outputs" / "e1_memos_full_oracle_v2"
LABELS = ("correct", "hallucination", "omission")
MAIN_ARMS = ("B0", "B1", "B2", "A2", "A2-nogate", "A2-nosal", "A2-nolic", "A2-noblock")
SEED = 20260709
_EXACT_FN: Any = None


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return "-inf" if value < 0 else "inf" if value > 0 else "NaN"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(_json_safe(value), ensure_ascii=False, indent=2,
                                allow_nan=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import io
    fields = list(dict.fromkeys(key for row in rows for key in row))
    stream = io.StringIO(newline="")
    if fields:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: _json_safe(value) for key, value in row.items()} for row in rows)
    write_text(path, stream.getvalue())


def merge_config(section: str, value: dict[str, Any], out_dir: Path) -> None:
    path = out_dir / "run_config.json"
    config = read_json(path, {})
    config.setdefault("seed", SEED)
    config[section] = value
    write_json(path, config)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if not n:
        return None, None
    if not 0 <= k <= n:
        raise ValueError("Wilson expects 0 <= successes <= trials")
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar_p(b: int, c: int) -> float:
    """Reuse the existing exact test; no discordance gives the null p=1."""
    if b + c == 0:
        return 1.0
    global _EXACT_FN
    if _EXACT_FN is None:
        spec = importlib.util.spec_from_file_location("a2_legacy_stats", Path(__file__).with_name("04_analyze_memos_full.py"))
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load the required existing exact McNemar helper")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _EXACT_FN = module.exact_mcnemar_p
    try:
        return float(_EXACT_FN(b, c))
    except OverflowError:
        # The existing no-scipy branch converts a huge integer before scaling.
        # Preserve its exact binomial tail in log-space when that overflows.
        n, tail = b + c, min(b, c)
        logs = [math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                - n * math.log(2) for k in range(tail + 1)]
        maximum = max(logs)
        return min(1.0, 2 * math.exp(maximum) * sum(math.exp(v - maximum) for v in logs))


def paired_delta(gained: int, lost: int, n: int) -> dict[str, Any]:
    if not n:
        return {"delta_pp": None, "ci95_low_pp": None, "ci95_high_pp": None}
    # A signed paired change is NOT binomial. Two 97.5% Wilson intervals for
    # discordant gains/losses give a conservative 95% Bonferroni difference CI.
    gain_lo, gain_hi = wilson(gained, n, 2.241402727604947)
    loss_lo, loss_hi = wilson(lost, n, 2.241402727604947)
    return {"delta_pp": 100 * (gained - lost) / n,
            "ci95_low_pp": 100 * (gain_lo - loss_hi),
            "ci95_high_pp": 100 * (gain_hi - loss_lo),
            "ci_method": "paired discordance; Bonferroni difference of 97.5% Wilson intervals"}


def label(row: dict[str, Any] | None) -> str | None:
    if not row or row.get("ok") is False or row.get("error"):
        return None
    value = row.get("judge_label", row.get("label"))
    if value is None and isinstance(row.get("verdict"), dict):
        value = row["verdict"].get("label")
    return value if value in LABELS else None


def latest_rows(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in read_jsonl(path) if "case_id" in row}


def sample_input_hash(sample: dict[str, Any]) -> str:
    return importlib.import_module("21_run_generation").sample_input_hash(sample)


def load_arm_cache(out_dir: Path, pool: str, arm: str, generator: str,
                   selection: dict[str, Any] | None = None
                   ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    context_rows = latest_rows(out_dir / "contexts" / pool / f"{arm}.jsonl")
    explicit_keys = (selection or {}).get("context_keys", {}).get(arm)
    keys = explicit_keys if explicit_keys is not None else {
        cid: row.get("cache_key") for cid, row in context_rows.items()}
    generations = read_jsonl(out_dir / "generations" / pool / f"{arm}__{generator}.jsonl")
    gens = {str(row["case_id"]): row for row in generations if row.get("case_id") is not None
            and keys.get(str(row["case_id"]))
            and row.get("context_cache_key") == keys[str(row["case_id"])]}
    judgments_by_generation = {row.get("generation_cache_key", row.get("gen_cache_key")): row
                               for row in read_jsonl(out_dir / "verdicts" / pool / f"{arm}__{generator}.jsonl")}
    judgments = {cid: judgments_by_generation.get(row.get("cache_key", row.get("input_hash")))
                 for cid, row in gens.items()}
    valid, rejected = {}, []
    for cid, row in judgments.items():
        generation = gens.get(cid)
        if (generation is None or generation.get("ok") is False or generation.get("error")
                or label(row) is None):
            rejected.append(cid)
            continue
        expected_key = generation.get("cache_key", generation.get("input_hash"))
        verdict_key = row.get("generation_cache_key", row.get("generation_input_hash"))
        if not expected_key or verdict_key != expected_key:
            rejected.append(cid)
            continue
        valid[cid] = row
    return valid, gens, rejected


def discover_generators(out_dir: Path, pool: str) -> list[str]:
    names = set()
    for folder in ("generations", "verdicts"):
        for path in (out_dir / folder / pool).glob("*__*.jsonl"):
            names.add(path.stem.rsplit("__", 1)[1])
    return sorted(names)


def rates_and_pairs(samples: dict[str, Any], verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = set(samples)
    archived_wrong_only = bool(samples) and all(
        row.get("evaluation_scope", "").startswith("archived_wrong_only")
        for row in samples.values())
    archived_wrong_ids = {cid for cid, row in samples.items()
                          if row.get("baseline_label", row.get("baseline_verdict"))
                          in ("hallucination", "omission")}
    if archived_wrong_only and archived_wrong_ids != ids:
        raise ValueError("Stage E pool contains unknown/non-wrong archived baseline labels")
    rates, deltas, pairs, transitions, flips, harm, reference_deltas = [], [], [], [], [], [], []
    b0 = {cid: label(row) for cid, row in verdicts.get("B0", {}).items() if cid in ids}
    stable = {cid for cid in ids if b0.get(cid) in ("hallucination", "omission")
              and samples[cid].get("baseline_label", samples[cid].get("baseline_verdict"))
              in ("hallucination", "omission")}
    b0_wrong = {cid for cid in ids if b0.get(cid) in ("hallucination", "omission")}
    strict_wrong = {cid for cid in b0_wrong if samples[cid].get("retrieval_stratum") == "strict_supported"}
    for arm, cache in verdicts.items():
        current = {cid: label(row) for cid, row in cache.items() if cid in ids and label(row)}
        counts = Counter(current.values())
        for outcome in LABELS:
            low, high = wilson(counts[outcome], len(current))
            rates.append({"arm": arm, "label": outcome, "count": counts[outcome],
                          "n_evaluated": len(current), "n_pool": len(ids),
                          "missing": len(ids) - len(current), "complete": len(current) == len(ids) and bool(ids),
                          "rate_evaluated": counts[outcome] / len(current) if current else None,
                          "wilson95_low": low, "wilson95_high": high,
                          "observed_share_of_pool": counts[outcome] / len(ids) if ids else None})
        matched = set(b0) & set(current)
        for outcome in LABELS:
            gained = sum(b0[cid] != outcome and current[cid] == outcome for cid in matched)
            lost = sum(b0[cid] == outcome and current[cid] != outcome for cid in matched)
            deltas.append({"arm": arm, "reference": "B0", "label": outcome,
                           "n_paired": len(matched), "gained": gained, "lost": lost,
                           **paired_delta(gained, lost, len(matched))})
        matrix = Counter((b0[cid], current[cid]) for cid in matched)
        for src in LABELS:
            denominator = sum(matrix[(src, dst)] for dst in LABELS)
            for dst in LABELS:
                transitions.append({"arm": arm, "from": src, "to": dst,
                                    "count": matrix[(src, dst)], "row_n": denominator,
                                    "row_rate": matrix[(src, dst)] / denominator if denominator else None,
                                    "n_paired": len(matched)})
        harm.append({"arm": arm, "baseline_correct_total": sum(v == "correct" for v in b0.values()),
                     "baseline_correct_paired": sum(b0[cid] == "correct" for cid in matched),
                     "C_to_H": matrix[("correct", "hallucination")] if matched else None,
                     "C_to_O": matrix[("correct", "omission")] if matched else None,
                     "O_to_H": matrix[("omission", "hallucination")] if matched else None})
        flip_subsets = (("archived_wrong_stage_E", archived_wrong_ids),) if archived_wrong_only else (
            ("stable_wrong", stable), ("B0_wrong", b0_wrong), ("B0_wrong_strict_supported", strict_wrong))
        for name, subset in flip_subsets:
            joined = subset & set(current)
            rescued = sum(current[cid] == "correct" for cid in joined)
            low, high = wilson(rescued, len(joined))
            flips.append({"arm": arm, "subset": name, "expected_n": len(subset),
                          "n_paired": len(joined), "missing": len(subset) - len(joined),
                          "rescued": rescued, "flip_rate": rescued / len(joined) if joined else None,
                          "wilson95_low": low, "wilson95_high": high})
        references = ("B0", "B1", "B2") + (("A2",) if arm.startswith("A2-") else ())
        for reference in references:
            if arm == reference:
                continue
            baseline = verdicts.get(reference, {})
            comparable = set(current) & set(baseline) & ids
            gained = sum(label(baseline[cid]) != "correct" and current[cid] == "correct"
                         for cid in comparable)
            lost = sum(label(baseline[cid]) == "correct" and current[cid] != "correct"
                       for cid in comparable)
            pairs.append({"arm": arm, "reference": reference, "n_paired": len(comparable),
                          "gained_correct": gained, "lost_correct": lost,
                          "p_exact_mcnemar": exact_mcnemar_p(gained, lost) if comparable else None,
                          **paired_delta(gained, lost, len(comparable))})
            for outcome in LABELS:
                increased = sum(label(baseline[cid]) != outcome and current[cid] == outcome for cid in comparable)
                decreased = sum(label(baseline[cid]) == outcome and current[cid] != outcome for cid in comparable)
                reference_deltas.append({"arm": arm, "reference": reference, "label": outcome,
                                         "n_paired": len(comparable), "gained": increased, "lost": decreased,
                                         **paired_delta(increased, decreased, len(comparable))})
    return {"rates": rates, "deltas": deltas, "mcnemar": pairs, "transitions": transitions,
            "flips": flips, "harm": harm, "reference_deltas": reference_deltas,
            "stable_wrong_n": len(stable), "B0_wrong_n": len(b0_wrong),
            "flip_reference": "archived baseline wrong-only; no fresh B0 or correct-subpool claim" if archived_wrong_only else "fresh B0",
            "stable_wrong_definition": "archived wrong AND fresh B0 replay wrong; two observations, not three-repeat stability"}


def controller_metrics(out_dir: Path, pool: str, arm: str, ids: set[str],
                       sample_hashes: dict[str, str] | None = None,
                       selection: dict[str, Any] | None = None) -> dict[str, Any]:
    desired = (selection or {}).get("context_keys", {}).get(arm)
    def chosen_rows(path: Path) -> dict[str, Any]:
        return {str(row["case_id"]): row for row in read_jsonl(path)
                if row.get("case_id") is not None and (desired is None or
                   row.get("cache_key") == desired.get(str(row["case_id"])))}
    contexts = chosen_rows(out_dir / "contexts" / pool / f"{arm}.jsonl")
    decisions = chosen_rows(out_dir / "decisions" / pool / f"{arm}.jsonl")
    actions = Counter({action: 0 for action in ACTIONS})
    block_shares, noops, bypass, n_available, proxy_notes = [], 0, 0, 0, 0
    for cid in sorted(ids):
        context = contexts.get(cid)
        decision = decisions.get(cid)
        if context is None and decision is None:
            continue
        value = {**(decision or {}), **(context or {})}
        if value.get("ok") is False or value.get("error"):
            continue
        if sample_hashes is not None and value.get("sample_input_hash") != sample_hashes.get(cid):
            continue
        n_available += 1
        noops += bool(value.get("no_op", value.get("noop", False)))
        bypass += bool(value.get("bypass", False))
        memory_decisions = (decision or {}).get("decisions", value.get("decisions", []))
        if not isinstance(memory_decisions, list):
            memory_decisions = []
        case_counts = Counter(item.get("action") for item in memory_decisions if isinstance(item, dict))
        actions.update({action: case_counts[action] for action in ACTIONS})
        proxy_notes += sum("temporal_from_ingest_proxy" in str(item.get("decision_note", ""))
                           for item in memory_decisions if isinstance(item, dict))
        denominator = value.get("n_records", value.get("record_count", len(memory_decisions)))
        if isinstance(denominator, int) and denominator > 0:
            block_shares.append(case_counts["BLOCK"] / denominator)
    ordered = sorted(block_shares)
    return {"arm": arm, "cases_available": n_available, "missing": len(ids) - n_available,
            "no_op_count": noops, "no_op_rate": noops / n_available if n_available else None,
            "bypass_count": bypass, "actions": dict(actions),
            "dominant_action_share": max(actions.values()) / sum(actions.values()) if sum(actions.values()) else None,
            "block_share_mean": sum(ordered) / len(ordered) if ordered else None,
            "block_share_min": min(ordered) if ordered else None,
            "block_share_max": max(ordered) if ordered else None,
            "block_share_median": (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) / 2 if ordered else None,
            "block_share_distribution": dict(Counter(str(round(v, 4)) for v in ordered)),
            "temporal_proxy_decision_count": proxy_notes}


def gate_outcome_diagnostic(out_dir: Path, ids: set[str], verdicts: dict[str, dict[str, Any]],
                            selection: dict[str, Any] | None) -> list[dict[str, Any]]:
    expected = (selection or {}).get("context_keys", {}).get("A2")
    contexts = {str(row["case_id"]): row for row in read_jsonl(out_dir / "contexts" / "memos" / "A2.jsonl")
                if expected is None or row.get("cache_key") == expected.get(str(row["case_id"]))}
    counts: dict[str, Counter] = {}
    for cid in sorted(ids & set(verdicts.get("B0", {})) & set(verdicts.get("A2", {}))):
        if cid not in contexts:
            continue
        before, after = label(verdicts["B0"][cid]), label(verdicts["A2"][cid])
        if before is None or after is None:
            continue
        meta = contexts[cid]
        group = "safe_bypass" if meta.get("bypass") else "gated_noop" if meta.get("no_op") else "intervened"
        row = counts.setdefault(group, Counter())
        row["n_paired"] += 1
        row["B0_correct"] += before == "correct"
        row["A2_correct"] += after == "correct"
        row["C_to_H"] += before == "correct" and after == "hallucination"
        row["C_to_O"] += before == "correct" and after == "omission"
        row["wrong_to_C"] += before != "correct" and after == "correct"
    return [{"branch": key, **dict(value)} for key, value in sorted(counts.items())]


def error_decomposition(samples: dict[str, Any], verdicts: dict[str, dict[str, Any]],
                        visibility: dict[str, Any]) -> dict[str, Any]:
    raw_counts, exclusive = Counter(), Counter()
    overlaps, rows = 0, []
    for cid, sample in samples.items():
        gold = sample.get("gold_memory_ids")
        valid_ids = {f"m{i}" for i in range(1, len(sample.get("raw_memories") or []) + 1)}
        retrieval = (any(mid not in valid_ids for mid in gold) if gold else
                     True if sample.get("retrieval_stratum") == "no_gold_retrieved" else None)
        vis = visibility.get(cid, sample)
        visible_ids = vis.get("gold_visible_ids")
        visible = bool(visible_ids) if visible_ids is not None and gold else None
        if gold and visible is None and "visible_memory_ids" in vis:
            visible = bool(set(gold) & set(vis["visible_memory_ids"]))
        serialized_loss = (not visible) if retrieval is False and visible is not None else None
        baseline = label(verdicts.get("B0", {}).get(cid))
        after = label(verdicts.get("A2", {}).get(cid))
        used_wrong = (baseline != "correct") if visible and baseline is not None else False if visible is False else None
        generation_wrong = (after != "correct") if visible and after is not None else False if visible is False else None
        predicates = {"retrieval_failure": retrieval, "serialization_loss": serialized_loss,
                      "admission_usage_failure": used_wrong, "generation_failure": generation_wrong}
        for name, value in predicates.items():
            raw_counts[name] += value is True
            raw_counts[f"{name}_unknown"] += value is None
        overlaps += sum(value is True for value in predicates.values()) > 1
        if baseline == "correct":
            bucket = "baseline_correct_residual"
        elif retrieval is True:
            bucket = "retrieval_failure"
        elif serialized_loss is True:
            bucket = "serialization_loss"
        elif used_wrong and generation_wrong:
            bucket = "generation_failure_after_A2"
        elif used_wrong and after == "correct":
            bucket = "admission_usage_failure_recovered_by_A2"
        else:
            bucket = "unresolved_or_missing_evidence"
        exclusive[bucket] += 1
        rows.append({"case_id": cid, **predicates, "B0_label": baseline,
                     "A2_label": after, "exclusive_bucket": bucket})
    return {"scope_n": len(samples), "raw_predicates": dict(raw_counts), "overlapping_cases": overlaps,
            "exclusive_counts": dict(exclusive), "exclusive_total": sum(exclusive.values()), "rows": rows,
            "specification_conflict": "Section 10.3's usage/generation predicates overlap and omit correct cases; four raw counts cannot honestly sum to 100%. Exclusive hierarchy includes correct and unresolved residuals.",
            "visibility_semantics": "At least one strict gold-memory position is visible, matching the existing visibility audit; not proof of complete answer sufficiency. Partial-only rows without strict positions remain unknown."}


def equivalence(samples: dict[str, Any], b0: dict[str, Any]) -> dict[str, Any]:
    legacy = {str(row["case_id"]) for row in read_jsonl(OLD_DIR / "samples_memos_full.jsonl")}
    observed = {cid for cid, row in b0.items() if cid in samples and label(row) in ("hallucination", "omission")}
    complete = bool(samples) and set(samples) <= set(b0)
    return {"legacy_wrong_n": len(legacy), "fresh_B0_wrong_n": len(observed),
            "complete_B0_replay": complete, "equal": observed == legacy if complete else None,
            "missing_from_new_wrong": sorted(legacy - observed), "added_to_new_wrong": sorted(observed - legacy),
            "warning": "Without complete current B0 judgments this is incomplete, not an equivalence proof; legacy flip rates remain reference-only."}


def historical_join(samples: dict[str, Any], verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    old_samples = latest_rows(OLD_DIR / "samples_memos_full.jsonl")
    a0 = latest_rows(OLD_DIR / "verdicts" / "A0.jsonl")
    result = {"historical_reference_percent": {"A3": 46.13, "UA3": 53.29},
              "ORACLE_REL_current_result": None,
              "warning": "UA3 used oracle hard-map decisions, not current real Stage 2; no learned Stage-1-only causal loss is identifiable."}
    joined = []
    for prior in ("A3", "UA3"):
        cache = latest_rows(OLD_DIR / "verdicts" / f"{prior}.jsonl")
        for current in ("B2", "A2"):
            ids = []
            for cid, sample in samples.items():
                old = old_samples.get(cid)
                if (not old or cid not in cache or cid not in verdicts.get(current, {})
                        or label(a0.get(cid)) not in ("hallucination", "omission")
                        or label(verdicts.get("B0", {}).get(cid)) not in ("hallucination", "omission")
                        or sample.get("retrieval_stratum") != "strict_supported"):
                    continue
                if all(sample.get(key) == old.get(key) for key in
                       ("question", "gold_answer", "raw_memories", "context_str_full")):
                    if label(cache[cid]) is not None:
                        ids.append(cid)
            before = sum(label(cache[cid]) == "correct" for cid in ids)
            after = sum(label(verdicts[current][cid]) == "correct" for cid in ids)
            joined.append({"historical_arm": prior, "current_arm": current, "n_same_input_ids": len(ids),
                           "case_ids_sha256": json_hash(sorted(ids)),
                           "historical_flip_rate": before / len(ids) if ids else None,
                           "current_flip_rate": after / len(ids) if ids else None,
                           "descriptive_loss_pp": 100 * (before - after) / len(ids) if ids else None,
                           "stage_specific_causal_loss": None})
    result["same_input_join"] = joined
    return result


def _manifest_ids(out_dir: Path, pool: str) -> list[str] | None:
    for path in (out_dir / "analysis" / f"{pool}_smoke_manifest.json",
                 out_dir / "pools" / f"{pool}_smoke_manifest.json"):
        value = read_json(path)
        if isinstance(value, dict) and isinstance(value.get("case_ids"), list):
            pool_path = out_dir / "pools" / f"{pool}_pool.jsonl"
            if not pool_path.exists() or value.get("pool_sha256") != file_hash(pool_path):
                return None
            return [str(cid) for cid in value["case_ids"]]
    return None


def smoke_audit(out_dir: Path, pool: str, samples: dict[str, Any], metrics: dict[str, Any],
                verdicts: dict[str, Any], generations: dict[str, Any],
                controllers: list[dict[str, Any]], manifest_present: bool) -> dict[str, Any]:
    ids = set(samples)
    a2 = next((row for row in controllers if row["arm"] == "A2"), {})
    leakage_path = out_dir / "leakage_failures.jsonl"
    leakage = [row for row in read_jsonl(leakage_path) if str(row.get("case_id")) in ids]
    group = read_json(out_dir / "analysis" / f"{pool}_group_probe.json", {})
    invariant_paths = (out_dir / "analysis" / "invariants_full.json",
                       out_dir / "analysis" / "invariants.json", out_dir / "analysis" / "invariant_tests.json")
    invariant = next((read_json(path) for path in invariant_paths if path.exists()), None)
    monotonicity = read_json(out_dir / "analysis" / f"{pool}_calibration_monotonicity.json")
    real_monotonic = next((row for row in (invariant or {}).get("results", [])
                           if row.get("test") == "10_real_noop_monotonic"), {})
    invariants_ready = (isinstance(invariant, dict) and invariant.get("mode") == "full_pool"
                        and invariant.get("full_pool_verified") is True
                        and invariant.get("failed") == 0 and invariant.get("pending") == 0
                        and real_monotonic.get("status") == "pass"
                        and (monotonicity is None or monotonicity.get("passed") is True))
    test_path = Path(__file__).with_name("test_a2_invariants.py")
    invariants_ready = invariants_ready and invariant.get("script_sha256") == file_hash(test_path)
    both = (any(label(row) == "correct" for row in verdicts.get("B0", {}).values())
            and any(label(row) in ("hallucination", "omission") for row in verdicts.get("B0", {}).values()))
    outputs = all(ids <= set(verdicts.get(arm, {})) and ids <= set(generations.get(arm, {}))
                  for arm in ("B0", "B1", "B2", "A2"))
    noop = a2.get("no_op_rate")
    dominant = a2.get("dominant_action_share")
    group_source = str(group.get("source", "")).replace("\\", "/")
    group_is_pool = group_source.endswith(f"pools/{pool}_pool.jsonl")
    checks = {
        "four_arms_complete_no_leakage_no_crashes": outputs and leakage_path.exists() and not leakage,
        "A2_noop_strictly_between_zero_and_one": noop is not None and 0 < noop < 1,
        "A2_actions_non_degenerate": dominant is not None and dominant < .95,
        "current_pool_multirecord_groups_exist": group_is_pool and group.get("multi_record_group_count", 0) > 0,
        "invariants_mandatory_checks_satisfied": invariants_ready,
        "exactly_150_manifest_cases": manifest_present and len(ids) == 150,
        "B0_has_correct_and_wrong": both,
    }
    return {"passed": all(checks.values()), "checks": checks, "n_cases": len(ids),
            "leakage_count": len(leakage), "group_probe": group, "invariant_evidence": invariant,
            "monotonicity_evidence": monotonicity,
            "all_assertions_passed": (invariant or {}).get("all_assertions_passed"),
            "waived_by_spec": (invariant or {}).get("waived_by_spec", 0)}


def analyze_pool(pool: str, out_dir: Path = OUT_DIR, generator: str | None = None,
                 smoke: bool = False, subset: int | None = None,
                 limit: int | None = None) -> list[dict[str, Any]]:
    path = out_dir / "pools" / f"{pool}_pool.jsonl"
    full_samples = latest_rows(path)
    sample_hashes = {cid: sample_input_hash(sample) for cid, sample in full_samples.items()}
    samples = dict(full_samples)
    manifest = _manifest_ids(out_dir, pool) if smoke else None
    selection = None
    if smoke:
        selection = read_json(out_dir / "analysis" / f"{pool}_smoke_manifest.json", {})
        samples = {cid: samples[cid] for cid in (manifest or []) if cid in samples}
    elif subset is not None or limit is not None:
        tag = f"subset{subset}" if subset is not None else f"limit{limit}"
        selection = read_json(out_dir / "analysis" / f"{pool}_selection_{tag}.json", {})
        selected_ids = selection.get("case_ids", [])
        if selection.get("pool_sha256") != file_hash(path):
            raise ValueError("Selection manifest is missing or does not match the frozen pool")
        samples = {str(cid): samples[str(cid)] for cid in selected_ids if str(cid) in samples}
        if len(samples) != selection.get("effective_count"):
            raise ValueError("Selection manifest includes absent or duplicate case IDs")
    else:
        selection = read_json(out_dir / "analysis" / f"{pool}_selection_full.json", {})
    generators = [generator] if generator else discover_generators(out_dir, pool) or ["deepseek-chat"]
    results = []
    for name in generators:
        arms = list(MAIN_ARMS)
        for cache in (out_dir / "verdicts" / pool).glob(f"*__{name}.jsonl"):
            arm = cache.stem.rsplit("__", 1)[0]
            if arm not in arms:
                arms.append(arm)
        verdicts, generations, rejections, full_verdicts = {}, {}, {}, {}
        for arm in arms:
            verdicts[arm], generations[arm], rejections[arm] = load_arm_cache(out_dir, pool, arm, name, selection)
            stale = [cid for cid, row in verdicts[arm].items() if cid in full_samples and
                     (row.get("sample_input_hash") != sample_hashes[cid] or
                      generations[arm][cid].get("sample_input_hash") != sample_hashes[cid])]
            for cid in stale:
                verdicts[arm].pop(cid)
            rejections[arm].extend(stale)
            full_verdicts[arm] = {cid: row for cid, row in verdicts[arm].items() if cid in full_samples}
            verdicts[arm] = {cid: row for cid, row in verdicts[arm].items() if cid in samples}
            generations[arm] = {cid: row for cid, row in generations[arm].items() if cid in samples}
        metrics = rates_and_pairs(samples, verdicts)
        whole_b0, whole_gens, _ = load_arm_cache(out_dir, pool, "B0", name)
        full_verdicts["B0"] = {cid: row for cid, row in whole_b0.items() if cid in full_samples and
                               row.get("sample_input_hash") == sample_hashes[cid] and
                               whole_gens[cid].get("sample_input_hash") == sample_hashes[cid]}
        controllers = [controller_metrics(out_dir, pool, arm, set(samples), sample_hashes, selection) for arm in arms]
        visibility = latest_rows(out_dir / "pools" / f"{pool}_visibility.jsonl")
        decomposition_verdicts = {**full_verdicts, "A2": verdicts.get("A2", {})}
        decomposition = error_decomposition(full_samples, decomposition_verdicts, visibility) if pool == "memos" else None
        source_paths = [path]
        source_paths.append(out_dir / "pools" / f"{pool}_visibility.jsonl")
        source_paths.extend([out_dir / "analysis" / f"{pool}_group_probe.json",
                             out_dir / "analysis" / f"{pool}_calibration_monotonicity.json",
                             out_dir / "analysis" / "invariants.json",
                             out_dir / "analysis" / "invariants_full.json",
                             out_dir / "analysis" / "invariant_tests.json",
                             out_dir / "leakage_failures.jsonl"])
        for folder in ("generations", "verdicts", "contexts", "decisions"):
            source_paths.extend((out_dir / folder / pool).glob("*.jsonl"))
        source_paths.extend((out_dir / "calibration").glob(f"{pool}*.json"))
        hashes = {str(file.relative_to(out_dir)): file_hash(file) for file in source_paths if file.exists()}
        hashes["selection_manifest_snapshot"] = json_hash(selection)
        if pool == "memos":
            for historical_path in (OLD_DIR / "samples_memos_full.jsonl",
                                    *(OLD_DIR / "verdicts" / f"{arm}.jsonl" for arm in ("A0", "A3", "UA3"))):
                if historical_path.exists():
                    hashes["external:" + str(historical_path)] = file_hash(historical_path)
        scope = "smoke" if smoke else f"subset{subset}" if subset is not None else f"limit{limit}" if limit is not None else "full_pool_requested"
        summary = {"pool": pool, "generator": name, "scope": scope,
                   "n_pool": len(samples), "full_pool_n": len(full_samples),
                   "selected_case_ids": sorted(samples), "pool_present": path.exists(), "input_hashes": hashes,
                   "selection_manifest": selection,
                   "input_hash": json_hash(hashes), "metrics": metrics, "controllers": controllers,
                   "rejected_or_stale_judgment_ids": rejections,
                   "error_decomposition": decomposition,
                   "equivalence": equivalence(full_samples, full_verdicts.get("B0", {})) if pool == "memos" else None,
                   "oracle_learned": historical_join(samples, verdicts) if pool == "memos" else None,
                   "evaluation_scope": next((row.get("evaluation_scope") for row in samples.values()
                                             if row.get("evaluation_scope")), "mixed_correctness_full_pool"),
                   "script_sha256": file_hash(Path(__file__)), "estimated_calls": 0}
        summary["judge_models"] = sorted({str(row.get("model")) for cache in verdicts.values()
                                          for row in cache.values() if row.get("model")})
        if pool == "memos":
            summary["gate_outcome_diagnostic"] = gate_outcome_diagnostic(out_dir, set(samples), verdicts, selection)
        main_complete = all(r["complete"] for r in metrics["rates"] if r["arm"] in MAIN_ARMS)
        if pool == "memos" and scope == "full_pool_requested" and main_complete:
            from a2_calibrate import calibration_split
            summary["fixed_split_diagnostic"] = {}
            for split in ("cal", "test"):
                members = {cid: sample for cid, sample in samples.items() if calibration_split(cid) == split}
                split_verdicts = {arm: {cid: row for cid, row in verdicts[arm].items() if cid in members}
                                  for arm in MAIN_ARMS}
                summary["fixed_split_diagnostic"][split] = {"n": len(members), "metrics": rates_and_pairs(members, split_verdicts)}
        if smoke:
            summary["smoke"] = smoke_audit(out_dir, pool, samples, metrics, verdicts, generations,
                                            controllers, manifest is not None)
        prefix = f"{pool}__{name}" + ("__smoke" if smoke else f"__subset{subset}" if subset is not None else f"__limit{limit}" if limit is not None else "")
        for key in ("rates", "deltas", "reference_deltas", "mcnemar", "transitions", "flips", "harm"):
            write_csv(out_dir / "analysis" / f"{prefix}_{key}.csv", metrics[key])
        write_csv(out_dir / "analysis" / f"{prefix}_actions.csv", [
            {"arm": row["arm"], "action": action, "count": count}
            for row in controllers for action, count in row["actions"].items()])
        if decomposition:
            write_csv(out_dir / "analysis" / f"{prefix}_decomposition_cases.csv", decomposition["rows"])
        write_json(out_dir / "analysis" / f"{prefix}_summary.json", summary)
        merge_config(f"analysis_{prefix}", {"estimated_calls": 0, "input_hashes": hashes,
                                              "script_sha256": summary["script_sha256"],
                                              "scope": summary["scope"]}, out_dir)
        results.append(summary)
    return results


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if value is None:
            return "未得/不可计算"
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |",
                      *("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)])


def _metric_table(summary: dict[str, Any], include_arms: tuple[str, ...] | None = None) -> str:
    metrics = summary["metrics"]
    rows = []
    for arm in dict.fromkeys(row["arm"] for row in metrics["rates"]):
        if include_arms is not None and arm not in include_arms:
            continue
        values = {row["label"]: row for row in metrics["rates"] if row["arm"] == arm}
        deltas = {row["label"]: row for row in metrics["deltas"] if row["arm"] == arm}
        base = values["correct"]
        rows.append([arm, base["n_evaluated"], base["n_pool"], base["missing"],
                     *(f"{values[cat]['count']} / {100*values[cat]['rate_evaluated']:.2f}%"
                       f" [{100*values[cat]['wilson95_low']:.2f},{100*values[cat]['wilson95_high']:.2f}]"
                       if values[cat]["rate_evaluated"] is not None else "未执行"
                       for cat in LABELS),
                     *(f"{deltas[cat]['delta_pp']:.2f} [{deltas[cat]['ci95_low_pp']:.2f},{deltas[cat]['ci95_high_pp']:.2f}]"
                       if deltas[cat]["delta_pp"] is not None else "未得" for cat in LABELS)])
    return markdown_table(["臂", "已判定", "目标子集", "缺失", "C数量/率[Wilson95%]",
                           "H数量/率[Wilson95%]", "O数量/率[Wilson95%]",
                           "ΔC pp[配对95%]", "ΔH pp[配对95%]", "ΔO pp[配对95%]"], rows)


def _selected_summaries(out_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows = [read_json(path) for path in (out_dir / "analysis").glob("*summary.json")]
    all_rows = [row for row in all_rows if isinstance(row, dict) and "metrics" in row]
    smoke = [row for row in all_rows if row.get("scope") == "smoke"]
    main: dict[tuple[str, str], dict[str, Any]] = {}
    for row in all_rows:
        if row.get("scope") == "smoke":
            continue
        key = row["pool"], row["generator"]
        previous = main.get(key)
        def rank(value: dict[str, Any]) -> tuple[bool, bool, int]:
            required = MAIN_ARMS if value.get("pool") == "memos" else ("B1", "A2")
            relevant = [r for r in value["metrics"]["rates"] if r["arm"] in required]
            completed_full = value.get("scope") == "full_pool_requested" and bool(relevant) and all(r["complete"] for r in relevant)
            return completed_full, value.get("scope", "").startswith("subset"), value.get("n_pool", 0)
        if previous is None or rank(row) > rank(previous):
            main[key] = row
    return list(main.values()), smoke


def cache_usage(out_dir: Path) -> dict[str, Any]:
    totals: dict[str, Counter[str]] = {}
    for kind in ("generations", "verdicts", "estimates"):
        seen: set[str] = set()
        usage = Counter()
        paths = (out_dir / kind).glob("**/*.json" if kind == "estimates" else "**/*.jsonl")
        for path in paths:
            values = [read_json(path)] if kind == "estimates" else read_jsonl(path)
            for value in values:
                key = value.get("input_hash", value.get("cache_key"))
                if kind == "estimates" and key:
                    key = str(path.relative_to(out_dir)) + ":" + key
                if not key or key in seen:
                    continue
                seen.add(key)
                measured = value.get("usage", value.get("telemetry", {}).get("usage", {})) or {}
                for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    usage[field] += int(measured.get(field) or 0)
        totals[kind] = usage
        if kind != "estimates":
            ledger_suffix = "generation" if kind == "generations" else "judge"
            ledgers = list((out_dir / "analysis").glob(f"*_{ledger_suffix}_attempts.jsonl"))
            if ledgers:
                actual = Counter()
                for ledger in ledgers:
                    for event in read_jsonl(ledger):
                        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                            actual[field] += int(event.get("usage", {}).get(field) or 0)
                totals[kind] = actual
    # Recovery moves the old failed estimate out of the active cache. Include
    # its recorded usage once, even if its journal entry was replayed twice.
    recovered_seen: set[str] = set()
    for ledger in (out_dir / "analysis").glob("*_estimate_retry_history.jsonl"):
        for event in read_jsonl(ledger):
            history_id = event.get("archive_path")
            if not history_id or str(history_id) in recovered_seen:
                continue
            recovered_seen.add(str(history_id))
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                totals["estimates"][field] += int(event.get("old_usage", {}).get(field) or 0)
    support = Counter()
    support_execution = read_json(out_dir / "support_audit" / "last_execution.json", {})
    if support_execution.get("completed") is not None and isinstance(support_execution.get("usage"), dict):
        support.update(support_execution["usage"])
    else:
        for row in read_jsonl(out_dir / "support_audit" / "attempts.jsonl"):
            for usage in row.get("usage_by_attempt", []):
                for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    support[field] += int(usage.get(field) or 0)
    totals["pool_support_audit"] = support
    return {"measured_usage": {kind: dict(usage) for kind, usage in totals.items()},
            "scope": "Provider-reported generation/judge attempt ledgers when present, otherwise unique retained caches; per-case estimate caches plus unique failed-cache recovery journals; support last_execution once (attempt-ledger fallback). No cache+ledger double counting. Histories lost before recovery journals were available may be incomplete; this is not a billing statement. No usage returned by transport failures is unknown, not asserted zero."}


def failure_examples(out_dir: Path, summary: dict[str, Any], maximum: int = 5) -> list[dict[str, Any]]:
    samples = latest_rows(out_dir / "pools" / f"{summary['pool']}_pool.jsonl")
    selected = set(summary.get("selected_case_ids", []))
    selection = summary.get("selection_manifest")
    verdicts = {arm: load_arm_cache(out_dir, summary["pool"], arm, summary["generator"], selection)[0]
                for arm in ("B0", "B1", "A2", "A2-nolic")}
    expected_contexts = (selection or {}).get("context_keys", {}).get("A2")
    contexts = {str(row["case_id"]): row for row in read_jsonl(out_dir / "contexts" / summary["pool"] / "A2.jsonl")
                if expected_contexts is None or row.get("cache_key") == expected_contexts.get(str(row["case_id"]))}
    candidates = []
    for cid in sorted(selected):
        sample = samples.get(cid)
        b0, a2 = verdicts["B0"].get(cid), verdicts["A2"].get(cid)
        if not sample or not b0 or not a2:
            continue
        if any(row.get("sample_input_hash") != sample_input_hash(sample) for row in (b0, a2)):
            continue
        baseline, after = label(b0), label(a2)
        category = ("C→H/O回归" if baseline == "correct" and after != "correct" else
                    "错→对救回" if baseline != "correct" and after == "correct" else
                    "仍未修复" if after != "correct" else "保持正确")
        nolic = label(verdicts["A2-nolic"].get(cid))
        candidates.append({"case_id": cid, "question": sample.get("question"), "category": category,
                           "B0_label": baseline, "A2_label": after, "B1_label": label(verdicts["B1"].get(cid)),
                           "B0_answer": b0.get("model_answer"), "A2_answer": a2.get("model_answer"),
                           "A2_nolic_label": nolic, "license_associated_regression": after != "correct" and nolic == "correct",
                           "decision_note": contexts.get(cid, {}).get("decision_note"),
                           "actions": dict(Counter(item.get("action") for item in contexts.get(cid, {}).get("decisions", [])))})
    candidates.sort(key=lambda row: (not row["license_associated_regression"], row["case_id"]))
    chosen = []
    for category in ("C→H/O回归", "错→对救回", "C→H/O回归", "错→对救回", "仍未修复"):
        match = next((row for row in candidates if row["category"] == category and row not in chosen), None)
        if match is not None and len(chosen) < maximum:
            chosen.append(match)
    chosen.extend(row for row in candidates if row not in chosen)
    return chosen[:maximum]


def build_report(out_dir: Path = OUT_DIR) -> str:
    config = read_json(out_dir / "run_config.json", {})
    preflight = read_json(out_dir / "preflight.json", {})
    main, smoke = _selected_summaries(out_dir)
    memos = next((row for row in main if row["pool"] == "memos"), None)
    if memos:
        # lambda arms belong to the same-400 sensitivity table, not the full-pool main table.
        for key in ("rates", "deltas", "reference_deltas", "mcnemar", "transitions", "flips", "harm"):
            memos["metrics"][key] = [row for row in memos["metrics"][key] if row["arm"] in MAIN_ARMS]
        memos["controllers"] = [row for row in memos["controllers"] if row["arm"] in MAIN_ARMS]
    external_blockers = []
    for blocker_path in out_dir.glob("*blocker*.json"):
        if blocker_path.name == "longmemeval_blocker.json":
            continue
        value = read_json(blocker_path, {})
        if isinstance(value, dict):
            if value.get("status") in {"resolved", "historical_blocker_resolved"}:
                continue
            # Deliberately exclude credentials and detailed account balances.
            safe_fields = {key: value[key] for key in ("reason", "status_code", "http_status", "is_available", "error_type", "stopped")
                           if key in value}
            external_blockers.append({"artifact": str(blocker_path), **safe_fields})
    actual_generation_models = sorted({str(value["model"]) for path in (out_dir / "generations").glob("**/*.jsonl")
                                       for value in read_jsonl(path) if value.get("model")})
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, timeout=10, check=False)
    sections: list[str] = ["# A2 MVP 结果报告", "数字只来自已存在且输入身份可对齐的缓存；缺失不填零、不代填O。",
                          "执行CODEX_TASK_A2_MVP_AMENDMENT_01.md：主α=0.20、memos校准τ=0.15；只断言coverage/累计错误数单调，比例下降保留为非阻断诊断。核心控制器冻结于round_0073。"]
    sections.extend(["## 0. 环境与配置", f"预检日期：{preflight.get('date', '缺失')}；Python：{preflight.get('python', '缺失')}。",
                     "可用端点（仅名称与地址）：" + json.dumps(preflight.get("endpoints", []), ensure_ascii=False),
                     "依赖 import 实测：" + json.dumps(preflight.get("dependencies", {}), ensure_ascii=False),
                     "缺包回退：" + json.dumps(preflight.get("fallbacks", {}), ensure_ascii=False),
                     "serializer 实测：" + json.dumps(preflight.get("serializer_check", {}), ensure_ascii=False),
                     "实际调用缓存中的生成器模型：" + (", ".join(actual_generation_models) or "尚无调用缓存"),
                     "实际有有效判定缓存的生成器：" + (", ".join(sorted({row["generator"] for row in main
                                                                            if any(r["n_evaluated"] for r in row["metrics"]["rates"])})) or "未运行"),
                     "缓存记录中的judge模型：" + json.dumps(sorted({model for row in main for model in row.get("judge_models", [])}), ensure_ascii=False),
                     f"配置：`{out_dir / 'run_config.json'}`；git基础提交：`{commit.stdout.strip() or '不可用'}`；未提交脚本以SHA256为准；23版本SHA256：`{file_hash(Path(__file__))}`。",
                     "实际token可测用量：" + json.dumps(cache_usage(out_dir), ensure_ascii=False)])
    sections.append("## 0.5 池定义与等价性校验")
    pool_meta = read_json(out_dir / "pools" / "memos_pool_summary.json", {})
    sections.append("新池按检索支持条件（strict/partial、非空事实证据、serializer_ok）构造，不按baseline对错过滤。")
    sections.append("修订案确认4062条池的范围：排除no_gold_retrieved；原错题池与本池不等价是非阻断发现。全轮对比统一使用fresh B0，归档判定仅作历史参考。")
    compact_pool_meta = {key: value for key, value in pool_meta.items() if key != "equivalence"}
    sections.append("池统计：" + json.dumps(compact_pool_meta or config.get("memos_pool_preparation", {}), ensure_ascii=False))
    serializer = read_json(out_dir / "analysis" / "full_source_serializer_verify.json", {})
    if serializer:
        sections.append(f"本轮源记录离线复验：{serializer['byte_exact']}/{serializer['source_n']}逐字节一致，失败{serializer['failed']}，额外API调用0；源文件SHA256保存在analysis/full_source_serializer_verify.json。")
    sections.append(f"完整差集/ID证据：`{out_dir / 'pools' / 'memos_pool_equivalence.json'}`与analysis/*_summary.json；正文只报告计数。")
    group = read_json(out_dir / "analysis" / "memos_group_probe.json", {})
    sections.append("真实分组与时间代理统计（保留source，旧池探针不能冒充新池）：" + json.dumps(group, ensure_ascii=False))
    if memos:
        eq = memos["equivalence"]
        sections.append(f"Fresh B0等价性：完整={eq['complete_B0_replay']}；旧wrong={eq['legacy_wrong_n']}，"
                        f"新fresh wrong={eq['fresh_B0_wrong_n']}，相等={eq['equal']}；"
                        f"差集旧中缺少{len(eq['missing_from_new_wrong'])}，新增{len(eq['added_to_new_wrong'])}。未完整重放时不可宣称已验证。")
    else:
        sections.append("Fresh B0完整重放等价性未取得；archived labels的池差集不是重放验证。")
    sections.append("## 1. 阶段 A 冒烟结果（150条）")
    if not smoke:
        sections.append("未取得冒烟统计与完整验收证据，不能跨越阶段A验收。")
    for row in smoke:
        sections.append(f"{row['pool']} / {row['generator']} / {row['n_pool']}条")
        sections.append(_metric_table(row, ("B0", "B1", "B2", "A2")))
        sections.append(markdown_table(["验收项", "通过"], [[name, passed] for name, passed in row.get("smoke", {}).get("checks", {}).items()]))
        sections.append(f"总体通过：{row.get('smoke', {}).get('passed', False)}。")
        sections.append(f"原始全部断言通过={row.get('smoke', {}).get('all_assertions_passed')}；明确按规范豁免={row.get('smoke', {}).get('waived_by_spec', 0)}。11差集按§13可豁免；必检项按修订案10a/10b真实通过，不要求10c比例单调。")
    sections.append("## 2. memos 主实验")
    if memos:
        sections.append(f"全池={memos['full_pool_n']}；实际分析目标={memos['n_pool']}（{memos['scope']}）。"
                        "预算先行子集不得冒充全量。各臂缺失独立列出；不完整时率/CI仅针对已判定案例。")
        if memos["n_pool"] < memos["full_pool_n"]:
            sections.append("§9.4规定先400并报告，不是永久缩小目标；原完整全池八臂仍待按每批≤3臂、预算≤30000逐批补齐，须先真实通过所有gate。")
        sections.append(_metric_table(memos))
        sections.append("CHO比例用Wilson95%；Δ是同ID配对变化，其CI是discordant增/损的97.5% Wilson区间之Bonferroni差，不把有符号差值当二项比例。")
        a2_comparisons = [r for r in memos["metrics"].get("reference_deltas", [])
                          if r["arm"] == "A2" and r["reference"] in ("B0", "B1", "B2")]
        sections.append("### A2 对三种参照的同ID配对变化")
        sections.append(markdown_table(["参照", "指标", "配对n", "Δ pp", "配对95% CI"],
                                      [[r["reference"], r["label"], r["n_paired"], r["delta_pp"],
                                        f"{r['ci95_low_pp']},{r['ci95_high_pp']}"] for r in a2_comparisons]))
        sections.append("主表全池包括cal与test；固定hash划分不改变，test未参与τ求解，但α由观察此前风险诊断后的修订案指定，不能称为全新未查看的确认性测试。")
        split_rows = []
        for split, value in memos.get("fixed_split_diagnostic", {}).items():
            split_rows.extend([split, r["reference"], r["n_paired"], r["delta_pp"],
                               f"{r['ci95_low_pp']},{r['ci95_high_pp']}", r["p_exact_mcnemar"]]
                              for r in value["metrics"]["mcnemar"] if r["arm"] == "A2" and r["reference"] in ("B0", "B1", "B2"))
        if split_rows:
            sections.append(markdown_table(["固定划分", "参照", "配对n", "A2 ΔC pp", "配对95% CI", "McNemar p"], split_rows))
        sections.append(markdown_table(["臂", "参照", "同ID n", "错→对", "对→错", "精确McNemar p"],
                                      [[r["arm"], r["reference"], r["n_paired"], r["gained_correct"], r["lost_correct"], r["p_exact_mcnemar"]] for r in memos["metrics"]["mcnemar"]]))
        sections.append("McNemar将C视为成功、H/O视为失败；列出的多项检验p未经多重比较校正，不能只挑显著项。")
        sections.append("### B0→各臂转移矩阵（行内比例）")
        sections.append(markdown_table(["臂", "从", "到", "数量", "行分母", "行内比例"],
                                      [[r["arm"], r["from"], r["to"], r["count"], r["row_n"], r["row_rate"]] for r in memos["metrics"]["transitions"]]))
        sections.append("### Do-no-harm 与最坏转移 O→H")
        sections.append(markdown_table(["臂", "B0正确已配对", "C→H", "C→O", "O→H"],
                                      [[r["arm"], r["baseline_correct_paired"], r["C_to_H"], r["C_to_O"], r["O_to_H"]] for r in memos["metrics"]["harm"]]))
        gate_outcomes = memos.get("gate_outcome_diagnostic", [])
        if gate_outcomes:
            sections.append(markdown_table(["A2实际分支", "配对n", "B0正确", "A2正确", "C→H", "C→O", "错→对"],
                                          [[r["branch"], r["n_paired"], r["B0_correct"], r["A2_correct"], r["C_to_H"], r["C_to_O"], r["wrong_to_C"]] for r in gate_outcomes]))
            sections.append("no-op/bypass保存上下文字节，不保证远端再次生成相同答案。分支表是观测分解；no-op的标签变化属于重放漂移，不能归为准入动作的单独因果效果；干预分支也未随机分配。")
        sections.append("### Flip rate 与动作分布")
        sections.append("stable_wrong定义：" + memos["metrics"]["stable_wrong_definition"])
        sections.append(markdown_table(["臂", "子池", "配对/预期", "救回", "flip rate", "Wilson95%"],
                                      [[r["arm"], r["subset"], f"{r['n_paired']}/{r['expected_n']}", r["rescued"], r["flip_rate"],
                                        f"{r['wilson95_low']}, {r['wilson95_high']}"] for r in memos["metrics"]["flips"]]))
        sections.append(markdown_table(["臂", *ACTIONS, "no-op率", "BLOCK占比均值/范围", "代理时序裁决"],
                                      [[r["arm"], *(r["actions"][action] for action in ACTIONS), r["no_op_rate"],
                                        f"{r['block_share_mean']} / [{r['block_share_min']},{r['block_share_max']}]", r["temporal_proxy_decision_count"]]
                                       for r in memos["controllers"]]))
        sections.append("实际no-op率包含空证据/估计失败等安全bypass；校准coverage只按risk≤τ计数，两者不能直接等同。no-op也不等于答对，且其生成仍可能有重放波动。")
    else:
        sections.append("未取得真实生成/judge分析缓存。")
    sections.append("## 3. 错误分解协议")
    sections.append("规范矛盾：§10.3的‘准入/使用失败’和‘生成失败’重叠，且四类不覆盖baseline正确样本，因此四个原始谓词不能诚实加总为100%。分别输出原始谓词与明确互斥层级＋正确/未知残余。")
    decomposition = memos.get("error_decomposition") if memos else None
    if decomposition:
        n = decomposition["scope_n"]
        sections.append(f"请求范围为memos全池{n}条；A2只在实际子集有观测，未运行部分保持unknown。")
        sections.append(markdown_table(["原始谓词", "命中", "未知", "占全池"], [[key, decomposition["raw_predicates"].get(key, 0),
                                      decomposition["raw_predicates"].get(key + "_unknown", 0),
                                      decomposition["raw_predicates"].get(key, 0) / n if n else None]
                                      for key in ("retrieval_failure", "serialization_loss", "admission_usage_failure", "generation_failure")]))
        sections.append(markdown_table(["互斥层级/残余", "数量", "占全池"], [[key, value, value / n if n else None]
                                      for key, value in decomposition["exclusive_counts"].items()]))
        sections.append(f"原始多谓词重叠{decomposition['overlapping_cases']}条；互斥合计{decomposition['exclusive_total']}。可见性语义：{decomposition['visibility_semantics']}")
    else:
        sections.append("尚无足够真实B0/A2判定；未报告虚构分解比例。")
    sections.append("## 4. oracle–learned 归因分解")
    sections.append(markdown_table(["配置", "Stage0", "Stage1", "Stage2", "Stage3", "flip"], [
        ["B0", "—", "—", "—", "—", "0（定义）"], ["A3历史", "baseline", "oracle", "hard map", "真实", "46.13%：历史参照"],
        ["UA3历史", "canonical", "oracle", "hard map", "真实", "53.29%：历史参照"],
        ["B2本次", "真实", "真实", "argmax固定映射", "真实", "见真实strict子池flip表" if memos else None],
        ["A2本次", "真实", "真实", "真实", "真实", "见真实strict子池flip表" if memos else None],
        ["ORACLE_REL", "真实", "oracle", "真实", "真实", "未重跑，无该配置分数"]]))
    sections.append("UA3不能冒充‘oracle关系＋真实Stage2’。仅在case_id与question/gold/raw/context均相等、两次B0均错的共同ID集合重算描述性差值；它不是单阶段因果损耗。历史两百分比也不保证同分母。")
    sections.append("修订案可选ORACLE_REL400未执行：冻结核心将该臂标为历史参考，且当前只有两类粗代理目标，缺少六类真实关系神谕标签；不能用粗代理冒充真实oracle或改变冻结核心来补分数。此项不影响必做主线与阶段E。")
    if memos:
        sections.append(markdown_table(["历史→当前", "同输入ID n", "历史flip", "当前flip", "描述性损耗pp"],
                                      [[f"{r['historical_arm']}→{r['current_arm']}", r["n_same_input_ids"], r["historical_flip_rate"],
                                        r["current_flip_rate"], r["descriptive_loss_pp"]] for r in memos["oracle_learned"]["same_input_join"]]))
    sections.append("## 5. 校准")
    sections.append("case_id SHA256前8位mod2固定cal/test；只用cal求阈值。该算法是经验风险门控，不能未经证明声称严格conformal有限样本保证；经验noop_err也不必随阈值单调。")
    found_calibration = False
    for pool in ("memos", "longmemeval", "mem0", "memobase", "supermemory"):
        cal = read_json(out_dir / "calibration" / f"{pool}.json")
        if cal is None:
            continue
        found_calibration = True
        compact_cal = {key: value for key, value in cal.items() if key not in ("rows", "cal_rows", "test_rows", "candidates", "threshold_curve", "case_ids", "input_hashes")}
        for key, value in list(compact_cal.items()):
            if isinstance(value, list) and len(value) > 4:
                compact_cal[key] = {"count": len(value), "first": value[0],
                                    "detail_file": str(out_dir / "calibration" / f"{pool}.json")}
        sections.append(f"{pool}校准实测（pilot/full范围不可混用）：" + json.dumps(_json_safe(compact_cal), ensure_ascii=False))
        if cal.get("degenerate_flag"):
            sections.append("门控退化为全程干预：degenerate_flag=true。")
        curve = out_dir / "analysis" / f"{pool}_calibration_curve.csv"
        if curve.exists():
            with curve.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            if rows:
                keys = list(rows[0])
                sections.append(markdown_table(keys, [[row.get(key) for key in keys] for row in rows]))
    if not found_calibration:
        sections.append("未取得校准文件与cal/test曲线。")
    sections.append("## 6. 消融")
    ablations = [r for r in (memos or {}).get("metrics", {}).get("deltas", []) if r["arm"].startswith("A2-")]
    sections.append(markdown_table(["臂", "指标", "配对n", "相对B0 Δ pp", "95% CI"],
                                  [[r["arm"], r["label"], r["n_paired"], r["delta_pp"], f"{r['ci95_low_pp']},{r['ci95_high_pp']}"] for r in ablations]) if ablations else "未执行四个消融，不能补写效果。")
    paired_ablations = [r for r in (memos or {}).get("metrics", {}).get("reference_deltas", [])
                        if r["reference"] == "A2" and r["arm"].startswith("A2-")]
    if paired_ablations:
        sections.append("同ID消融相对A2主臂（C增加为好、H/O减少为好；固定主阈值，不据此改设定）：")
        sections.append(markdown_table(["消融", "指标", "配对n", "相对A2 Δ pp", "配对95% CI"],
                                      [[r["arm"], r["label"], r["n_paired"], r["delta_pp"], f"{r['ci95_low_pp']},{r['ci95_high_pp']}"] for r in paired_ablations]))
    sections.append("## 7. λ_O 敏感性")
    sensitivity_source = read_json(out_dir / "analysis" / "memos__deepseek-chat__subset400_summary.json", memos or {})
    sensitivity = [r for r in sensitivity_source.get("metrics", {}).get("deltas", [])
                   if ("__lambda_o_" in r["arm"] or r["arm"] == "A2") and r["label"] != "correct" and r["n_paired"]]
    sections.append(markdown_table(["配置", "指标", "实际配对n", "Δ pp"], [[r["arm"], r["label"], r["n_paired"], r["delta_pp"]] for r in sensitivity]) if sensitivity else "尚无{0.3,0.6,1.0,2.0}四档同400案例缓存。λ_O=1主配置在主实验表，其他档不得推测。")
    sections.append("## 8. 估计器内在评估")
    sections.append("关系accuracy/macro-F1仅为粗代理，不作为估计器质量结论；当前目标集中缺少四个关系类的独立标注。risk AUC与oracle修复关联也是事后诊断，不证明框架成立或方法因果收益。")
    intrinsic = list((out_dir / "analysis").glob("*_intrinsic.json"))
    if intrinsic:
        for path in intrinsic:
            intrinsic_value = read_json(path)
            compact_intrinsic = {key: value for key, value in intrinsic_value.items()
                                 if key not in ("input_hashes", "missing_estimate_ids", "stale_estimate_ids", "rejected_stale_B0_judgments")}
            compact_intrinsic["missing_estimate_n"] = len(intrinsic_value.get("missing_estimate_ids", []))
            compact_intrinsic["stale_estimate_n"] = len(intrinsic_value.get("stale_estimate_ids", []))
            compact_intrinsic["rejected_stale_B0_n"] = len(intrinsic_value.get("rejected_stale_B0_judgments", []))
            sections.append("`" + str(path) + "`：" + json.dumps(compact_intrinsic, ensure_ascii=False))
    else:
        sections.append("未取得24_intrinsic_eval.py真实结果；不凭预测标签自证oracle关系。")
    sections.append("## 9. 跨生成器（或跨记忆系统）")
    if preflight.get("endpoint_count") == 1:
        sections.append("仅1个生成器端点可用，阶段D按任务书跳过；换同端点别名不是跨家族验证。")
    else:
        sections.append("跨生成器是否完成须以真实缓存为准，控制器必须固定。")
    for row in main:
        if row["pool"] == "memos" and row is memos:
            continue
        sections.append(f"{row['pool']} / {row['generator']}：全池{row['full_pool_n']}，分析目标{row['n_pool']}，scope={row['scope']}。")
        if row.get("evaluation_scope", "").startswith("archived_wrong_only"):
            sections.append("阶段E旧错题池：只报flip rate，不报noop_err或do-no-harm。")
            sections.append("分母是归档baseline错题，不是新的fresh B0错题；未重跑fresh B0，故救回率不单独构成因果机制收益。B1与A2仍为同ID、同输入的当轮对照。")
            sections.append(markdown_table(["臂", "子池", "配对n", "救回", "flip", "Wilson95%"], [[r["arm"], r["subset"], r["n_paired"], r["rescued"], r["flip_rate"],
                                          f"{r['wilson95_low']},{r['wilson95_high']}"]
                                          for r in row["metrics"]["flips"] if r["arm"] in ("B1", "A2")]))
        else:
            sections.append(_metric_table(row, ("B0", "B1", "A2") if row["pool"] == "longmemeval" else None))
            paired = [r for r in row["metrics"].get("reference_deltas", []) if r["arm"] == "A2" and r["reference"] == "B1"]
            sections.append("B1 vs A2同IDΔC/ΔH/ΔO：" + json.dumps(paired, ensure_ascii=False))
        sections.append("Capability：" + json.dumps(read_json(out_dir / "analysis" / f"{row['pool']}_group_probe.json", {}), ensure_ascii=False))
    sections.append("## 10. LongMemEval（或阻断＋阶段E）")
    blocker = read_json(out_dir / "longmemeval_blocker.json")
    if isinstance(blocker, dict) and blocker.get("status") == "resolved":
        blocker = None
    if blocker:
        sections.append("LongMemEval获取状态（修订案最多3种策略尝试；失败后继续阶段E，不阻断主线）：" + json.dumps(blocker, ensure_ascii=False))
        for pool in ("mem0", "memobase", "supermemory"):
            observed = next((row for row in main if row["pool"] == pool), None)
            complete = bool(observed) and all(r["complete"] for r in observed["metrics"]["rates"] if r["arm"] in ("B1", "A2"))
            sections.append(f"阶段E {pool}替代：目标池存在={(out_dir / 'pools' / f'{pool}_pool.jsonl').exists()}，B1/A2实际目标集判定完整={complete}。未完成则任务仍有待办。")
    elif not any(row["pool"] == "longmemeval" for row in main):
        sections.append("尚无LongMemEval分数或单次下载阻断证据，不能声称阶段C/E完成。")
    sections.append("修订案阶段E无论LongMemEval是否可得都必做；三个历史错题池不能评价baseline-correct安全性或noop_err。")
    sections.append("不得把oracle retrieval reading failure说成首次发现；LME更新题允许包含旧信息，正确拒答算C不算O；数据修订/文件hash与recall@20见pool/config实测。")
    sections.append("## 11. 意外发现与失败案例")
    examples = failure_examples(out_dir, memos) if memos else []
    if examples:
        sections.append("案例是目的性诊断展示：优先两条回归、两条救回、一条仍未修复；类内先列license关联候选，再按case_id。类别不足时补齐，不代表总体频率或因果效应。")
        sections.append(markdown_table(["case_id", "问题", "B0→A2", "实际回答B0 / A2", "动作与诊断", "nolic正确关联"],
                                      [[r["case_id"], r["question"], f"{r['B0_label']}→{r['A2_label']}",
                                        f"{r['B0_answer']} / {r['A2_answer']}", f"{r['actions']} {r['decision_note']}", r["license_associated_regression"]] for r in examples]))
        write_json(out_dir / "analysis" / "memos_failure_examples.json", examples)
    if len(examples) < 5:
        sections.append(f"只取得{len(examples)}条可对齐真实案例；不足5条明确列为未完成，不编造。")
    sections.append("A2错而nolic对仅是license关联回归候选，不足以证明单独license因果；模板授权可能放大错误后验，代理写入时间也可能误当事件时间。")
    sections.append("## 12. 结论与下一步")
    comparison = [r for r in (memos or {}).get("metrics", {}).get("mcnemar", []) if r["arm"] == "A2" and r["reference"] == "B1"]
    if comparison and comparison[0]["n_paired"]:
        row = comparison[0]
        sections.append(f"Stage1/2真实实现后，A2相对B1在{row['n_paired']}个同ID案例的ΔC={row['delta_pp']:.3f}pp，精确McNemar p={row['p_exact_mcnemar']:.6g}。")
        if row["delta_pp"] < 3:
            sections.append("相对强B1增益小于3pp，未达到任务书所述差距；不得弱化B1制造收益。")
        tradeoffs = {r["label"]: r for r in memos["metrics"]["reference_deltas"] if r["arm"] == "A2" and r["reference"] == "B1"}
        if all(tradeoffs.get(key, {}).get("delta_pp") is not None for key in ("hallucination", "omission")):
            sections.append(f"同一对照下ΔH={tradeoffs['hallucination']['delta_pp']:+.3f}pp、ΔO={tradeoffs['omission']['delta_pp']:+.3f}pp；正确率提升与H/O权衡须一起解释，不能只报C。")
        b2_comparison = next((r for r in memos["metrics"]["mcnemar"] if r["arm"] == "A2" and r["reference"] == "B2" and r["n_paired"]), None)
        if b2_comparison:
            sections.append(f"A2相对真实B2的ΔC={b2_comparison['delta_pp']:+.3f}pp（未校正McNemar p={b2_comparison['p_exact_mcnemar']:.6g}）；相对B1为正不等于优于B2或全面有效。")
        nogate = next((r for r in memos["metrics"]["mcnemar"] if r["arm"] == "A2-nogate" and r["reference"] == "A2" and r["n_paired"]), None)
        if nogate:
            sections.append(f"去门控相对主臂ΔC={nogate['delta_pp']:+.3f}pp（未校正McNemar p={nogate['p_exact_mcnemar']:.6g}）。若去门控更好，门控效用本轮不获支持；校准稳定只说明经验门控行为，不能代替效用证据。")
    else:
        sections.append("尚无可验证A2 vs B1真实同ID收益数字，不能宣布方法有效或完整交付。")
    sections.append("不是标签拟合的证据应来自物理隔离输入、真实Stage1/2、强B1/真实B2对照与同ID结果；历史神谕分数不构成当前方法收益。短板及下一步以实际错误与缺失分析为准。")
    sections.append("主α=0.20由修订案在观察round_0074结果后指定；阈值仍只在cal求解，但这不是新的、未查看的独立确认性test。cal/test接近仅作观测，不据此证明无过拟合。")
    sections.append("完善阶段清单（本轮不执行）：1.结构化二阶风险分数增强；2.记忆正文事件时间来源增强；3.100–200条真实关系人工标注；4.补入no_gold_retrieved测量完整检索失败；5.获得其他家族端点后跨生成器。")
    sections.append("## 13. 阻断、规范矛盾与未完成项")
    if external_blockers:
        sections.append("外部API/账户阻断证据（不输出凭据或资金明细）：" + json.dumps(external_blockers, ensure_ascii=False))
        sections.append("失败回退只是安全no-op，不是实验成绩；没有成功judge的生成不计入C/H/O，不能将API失败伪装成omission。")
    pending = []
    if not smoke or any(not row.get("smoke", {}).get("passed") for row in smoke):
        pending.append("阶段A完整验收未通过/未证实，按任务书不得越过gate。")
    if memos and not memos["equivalence"]["complete_B0_replay"]:
        pending.append("Fresh B0全池重放等价性未完整验证。")
    if not main or any(not r["complete"] for row in main for r in row["metrics"]["rates"] if r["arm"] in ("B1", "A2")):
        pending.append("一个或多个实际目标集的B1/A2生成判定仍缺失；子集预算降级范围与完整目标不得混用。")
    if memos and (memos["n_pool"] < memos["full_pool_n"] or any(not r["complete"] for r in memos["metrics"]["rates"] if r["arm"] in MAIN_ARMS)):
        pending.append("memos原始全池八臂范围尚未完成；400条仅先行报告，不能替代完整目标。")
    if len(examples) < 5:
        pending.append("五条真实案例交付未满足。")
    if blocker:
        attempts = read_json(out_dir / "analysis" / "longmemeval_acquisition_attempts.json", {}).get("attempts", [])
        if len(attempts) == 3 and all(row.get("status") == "failed" for row in attempts):
            pending.append("可接受的不可得记录：LongMemEval累计3种策略均失败，限次获取已履行，停止重试；这不是主线失败或仍需第4次尝试。阶段E完整性另逐池核验。")
        else:
            pending.append("LongMemEval修订案限次获取尚未完成；最多累计3种策略，随后不再重试。阶段E本轮必做。")
    for pool in ("mem0", "memobase", "supermemory"):
        observed = next((row for row in main if row["pool"] == pool), None)
        required_rates = [r for r in (observed or {}).get("metrics", {}).get("rates", []) if r["arm"] in ("B1", "A2")]
        complete = (bool(observed) and observed["scope"] == "full_pool_requested"
                    and {r["arm"] for r in required_rates} == {"B1", "A2"}
                    and all(r["complete"] for r in required_rates))
        if not complete:
            pending.append(f"必做阶段E {pool}全池B1/A2尚未完整生成判定。")
    pending.append("已知非阻断发现：memos为100%写入代理时间、risk分辨率有限、粗代理目标不完整、池范围差异、部分α退化。比例下降已由修订案废除为断言；原公式与完整诊断保留，完善项本轮不执行。其他系统的现有text_cue触发情况见能力探针，不等于本轮新增时间增强。")
    sections.extend("- " + item for item in pending)
    text = "\n\n".join(sections) + "\n"
    write_text(out_dir / "RESULTS.md", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool")
    parser.add_argument("--generator")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--subset", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--yes", action="store_true", help="Accepted; analysis itself always costs zero calls")
    args = parser.parse_args()
    if args.smoke and (args.subset is not None or args.limit is not None):
        parser.error("--smoke uses the fixed150 manifest, not a separate subset/limit")
    print("Budget: analysis/report LLM calls=0; read existing caches only", flush=True)
    summaries = []
    if args.pool or not args.report:
        summaries = analyze_pool(args.pool or "memos", args.out_dir, args.generator,
                                 args.smoke, args.subset, args.limit)
    report = build_report(args.out_dir)
    report_sources = [args.out_dir / "preflight.json", args.out_dir / "pools" / "memos_pool_summary.json",
                      *(args.out_dir / "analysis").glob("*summary.json"),
                      *(args.out_dir / "analysis").glob("*_intrinsic.json"),
                      *args.out_dir.glob("*blocker*.json")]
    merge_config("report", {"estimated_calls": 0, "script_sha256": file_hash(Path(__file__)),
                            "input_hashes": {str(path.relative_to(args.out_dir)): file_hash(path) for path in report_sources if path.exists()},
                            "report_sha256": hashlib.sha256(report.encode("utf-8")).hexdigest()}, args.out_dir)
    print(json.dumps({"report": str(args.out_dir / "RESULTS.md"), "analysis_scopes":
                      [{"pool": r["pool"], "scope": r["scope"], "n": r["n_pool"]} for r in summaries]}, ensure_ascii=False), flush=True)
    if args.smoke and any(not row["smoke"]["passed"] for row in summaries):
        raise SystemExit("Stage A smoke gate not passed; inspect analysis/*__smoke_summary.json and RESULTS.md")


if __name__ == "__main__":
    main()
