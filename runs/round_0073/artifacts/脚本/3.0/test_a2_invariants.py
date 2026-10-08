"""Task-book invariants, with honest synthetic versus full-pool status.

Run --offline for deterministic synthetic checks (zero external API calls).
Default execution also requires the COMPLETE new pool, real B0 replay verdicts,
and complete input-hashed Stage 1 caches. Missing work is pending, not green.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import math
import random
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

from a2_arms import MAIN_ARMS, B1_STATIC_INSTRUCTION, apply_ablation, b2_decisions
from a2_pipeline import run_pipeline_detailed
from a2_schema import (
    ACTIONS, RELATIONS, Action, DecisionRecord, DeploymentSample, EstimateResult,
    EvidenceRecord, MemoryEstimate, Relation, safe_estimate,
)
from a2_stage0_adapter import adapt, canonical_text
from a2_stage1_estimator import (
    _load_cached, estimate, estimate_cache_key, estimate_cache_path, estimate_cached,
    validate_estimate,
)
from a2_stage2_decision import COST_MATRIX, choose_action, decide, expected_costs, probe_groups
from a2_stage3_render import (
    LICENSE_TEMPLATES, INSUFFICIENT_NOTE, all_injection_templates,
    authorization_text, render_detailed,
)
from e1_memos_oracle_common import ROOT, SEED, read_jsonl, sha256_text, write_json

OUT_DIR = ROOT / "outputs" / "a2_mvp_v1"
BASE_DIR = Path(__file__).resolve().parent
FORBIDDEN_FIELDS = {"gold_memory_ids", "gold_evidence", "evidence", "question_type",
                    "baseline_label", "baseline_response", "has_answer", "answer_session_ids"}


class PendingCheck(RuntimeError):
    """Missing authoritative data cannot support a completion claim."""


class SpecWaiver(RuntimeError):
    """The task-book expressly allows this failure to be nonblocking."""


def load_numbered(name: str, filename: str) -> Any:
    path = BASE_DIR / filename
    if not path.is_file():
        raise PendingCheck(f"Required implementation is not yet present: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PendingCheck(f"Cannot load implementation: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def one_hot(relation: str) -> dict[str, float]:
    return {name: float(name == relation) for name in RELATIONS}


def synthetic_estimate(records: list[EvidenceRecord], relations: list[str], *,
                       risk: float = 0.9, sufficiency: float = 0.9) -> EstimateResult:
    assert len(records) == len(relations)
    return EstimateResult(False, sufficiency, risk, {
        record.id: MemoryEstimate(record.id, one_hot(relation))
        for record, relation in zip(records, relations)
    })


def deployment(raw: list[Any], question: str = "Where is the housing now?") -> DeploymentSample:
    # Deliberate whitespace makes accidental baseline rebuilding observable.
    return DeploymentSample(question, copy.deepcopy(raw), "memos", "u",
                            "  ARCHIVED BASELINE\n\nbytes \t\n", "saved preference note")


def test_01_adapter_complete() -> dict[str, Any]:
    raw = [{"memory_value": "v", "memory_key": "k", "create_time": "2023-01-01"}]
    record = adapt(raw, "memos")[0]
    assert "memory_value: v" in record.text and "memory_key: k" in record.text
    assert record.ingest_time == "2023-01-01" and record.time_is_proxy is True
    item = {"memory": "m", "memory_value": "v", "memory_key": "k",
            "memory_type": "fact", "tags": ["first", "second"],
            "preference": "p", "preference_type": "t", "reasoning": "r",
            "content": "c", "text": "x", "metadata": {"z": "last", "a": "first", "empty": "N/A"}}
    text = adapt([item], "memos")[0].text
    assert text.index("memory: m") < text.index("memory_value: v") < text.index("memory_key: k")
    for key, value in item.items():
        if key not in {"metadata", "tags"}:
            assert f"{key}: {value}" in text
    assert "tags: first,second" in text
    assert text.index("metadata.a: first") < text.index("metadata.z: last")
    assert "metadata.empty" not in text
    skipped = adapt([{}, {"text": "None"}, {"text": "N/A"}, {"text": "  "}, {"text": "real"}], "memos")
    assert len(skipped) == 1 and skipped[0].id == "m5" and skipped[0].raw_index == 4
    return {"complete_fact_fields": True, "empty_records_rejected": 4}


def test_02_time_exhaustive() -> dict[str, Any]:
    rng = random.Random(SEED)
    sources = set()
    for i in range(200):
        item: dict[str, Any] = {"text": f"record {i}"}
        choice = rng.randrange(4)
        if choice == 0:
            item.update(event_time="2022-01-01", create_time="2023-01-01")
        elif choice == 1:
            item["metadata"] = {"create_time": "2023-01-01"}
        elif choice == 2:
            item["text"] += " in May 2023"
        else:
            item["text"] += " last March"  # Unknown reference date is not fabricated.
        record = adapt([item], "memos")[0]
        assert record.time_source in {"meta_event", "meta_ingest", "text_cue", "none"}
        assert record.time_is_proxy == (record.time_source == "meta_ingest")
        assert (record.event_time is not None) if choice in {0, 2} else record.event_time is None
        if choice == 2:
            assert record.time_uncertainty == ("2023-05-01", "2023-05-31")
        sources.add(record.time_source)
    assert sources == {"meta_event", "meta_ingest", "text_cue", "none"}
    return {"random_records": 200, "observed_sources": sorted(sources)}


def test_03_cost_matrix() -> dict[str, Any]:
    literal = {
        Action.VOUCH: [(0.00, 0.00), (0.20, 0.50), (0.75, 0.00), (0.05, 0.02), (0.70, 0.05), (0.80, 0.02)],
        Action.KEEP: [(0.00, 0.00), (0.05, 0.50), (0.50, 0.05), (0.05, 0.05), (0.40, 0.10), (0.45, 0.05)],
        Action.DEMOTE: [(0.10, 0.25), (0.10, 0.45), (0.30, 0.10), (0.10, 0.15), (0.25, 0.15), (0.30, 0.10)],
        Action.QUALIFY: [(0.05, 0.15), (0.10, 0.35), (0.20, 0.10), (0.05, 0.10), (0.15, 0.25), (0.10, 0.10)],
        Action.REFUTE: [(0.25, 0.10), (0.05, 0.05), (0.15, 0.15), (0.15, 0.15), (0.25, 0.20), (0.20, 0.15)],
        Action.BLOCK: [(0.00, 0.95), (0.10, 0.90), (0.05, 0.05), (0.02, 0.85), (0.05, 0.15), (0.05, 0.05)],
    }
    assert COST_MATRIX == literal, "Task-book cost matrix values changed"
    expected = {"SUPPORT": Action.VOUCH, "REFUTE": Action.REFUTE,
                "SUPERSEDED": Action.BLOCK, "CURRENT": Action.VOUCH,
                "MISBIND": Action.BLOCK, "INSUFFICIENT": Action.BLOCK}
    actual = {relation: choose_action(one_hot(relation)) for relation in RELATIONS}
    assert actual == expected, (actual, expected)
    assert choose_action(one_hot("SUPPORT"), lambda_h=0, lambda_o=0) == Action.VOUCH
    return {"one_hot_actions": {key: value.value for key, value in actual.items()}}


def test_04_weighted_hedging() -> dict[str, Any]:
    posterior = {name: 0.5 if name in {"SUPPORT", "INSUFFICIENT"} else 0.0 for name in RELATIONS}
    action = choose_action(posterior)
    assert action == Action.QUALIFY, action
    assert math.isclose(expected_costs(posterior)[Action.QUALIFY], 0.2)
    return {"half_support_half_insufficient": action.value}


def test_05_exclusive_sets() -> dict[str, Any]:
    question = "Where is the housing now?"
    bare = [{"memory_value": "lived in Rome", "memory_key": "Housing"},
            {"memory_value": "lives in Paris", "memory_key": "Housing"}]
    records = adapt(bare, "memos")
    result = synthetic_estimate(records, ["SUPERSEDED", "CURRENT"])
    decisions = decide(question, records, result)
    assert [d.action for d in decisions] == [Action.QUALIFY, Action.QUALIFY]
    assert all(d.temporal == "UNKNOWN" for d in decisions)
    dated = [{**bare[0], "event_time": "2023-01-01"}, {**bare[1], "event_time": "2024-01-01"}]
    records = adapt(dated, "memos")
    decisions = decide(question, records, synthetic_estimate(records, ["SUPERSEDED", "CURRENT"]))
    assert [d.action for d in decisions] == [Action.DEMOTE, Action.VOUCH]
    proxy = [{**bare[0], "create_time": "2023-01-01"}, {**bare[1], "create_time": "2024-01-01"}]
    records = adapt(proxy, "memos")
    decisions = decide(question, records, synthetic_estimate(records, ["SUPERSEDED", "CURRENT"]))
    assert [d.action for d in decisions] == [Action.DEMOTE, Action.VOUCH]
    assert all("temporal_from_ingest_proxy" in d.decision_note for d in decisions)
    tied = [{**bare[0], "event_time": "2023-01-01"}, {**bare[1], "event_time": "2023-01-01"}]
    records = adapt(tied, "memos")
    decisions = decide(question, records, synthetic_estimate(records, ["SUPERSEDED", "CURRENT"]))
    assert all(d.action == Action.QUALIFY for d in decisions)
    return {"unknown_time": "all_QUALIFY", "dated": "DEMOTE_VOUCH",
            "ingest_proxy_warning": True, "tied_time": "all_QUALIFY"}


def test_06_aggregates_unchanged() -> dict[str, Any]:
    records = adapt([{"text": f"support {i}", "memory_key": "shared"} for i in range(3)], "memos")
    result = synthetic_estimate(records, ["SUPPORT", "CURRENT", "INSUFFICIENT"])
    decisions = decide("What support is shared?", records, result)
    expected = [choose_action(result.memories[r.id].relation_posterior) for r in records]
    assert [d.action for d in decisions] == expected
    assert not any("exclusive_set" in d.decision_note for d in decisions)
    return {"aggregate_actions_preserved": len(records)}


def test_07_authorization_lock() -> dict[str, Any]:
    for action in Action:
        use = "REFUTATIONAL" if action == Action.REFUTE else "QUALIFY" if action == Action.QUALIFY else "ASSERT"
        decision = DecisionRecord("m1", action, Relation.SUPPORT, use=use)
        assert (use == "ASSERT") == (authorization_text(decision) == "")
        if action != Action.BLOCK:
            context, annotations = render_detailed([EvidenceRecord("m1", "fact", raw_index=0)], [decision], "u")
            if use != "ASSERT":
                assert LICENSE_TEMPLATES[use] in context and LICENSE_TEMPLATES[use] in annotations
            else:
                assert all(value not in context for value in (LICENSE_TEMPLATES["QUALIFY"], LICENSE_TEMPLATES["REFUTATIONAL"]))
    return {"all_six_actions_checked": True, "salience_prefix_is_not_authorization": True}


def test_09_frozen_render() -> dict[str, Any]:
    raw = [{"text": f"unique frozen fact number {i}", "memory_key": f"topic{i}"} for i in range(6)]
    raw_before = json.dumps(raw, sort_keys=True)
    records = adapt(raw, "memos")
    actions = [Action.DEMOTE, Action.KEEP, Action.VOUCH, Action.REFUTE, Action.QUALIFY, Action.BLOCK]
    decisions = [DecisionRecord(r.id, a, Relation.SUPPORT,
                               use="REFUTATIONAL" if a == Action.REFUTE else "QUALIFY" if a == Action.QUALIFY else "ASSERT")
                 for r, a in zip(records, actions)]
    context, annotations = render_detailed(records, decisions, "u")
    ids = re.findall(r"\[(m\d+) \|", context)
    assert ids == ["m3", "m4", "m2", "m5", "m1"], ids
    mapping = {r.id: r for r in records}
    for identifier in ids:
        record = mapping[identifier]
        assert 0 <= record.raw_index < len(raw)
        assert sha256_text(record.text) == sha256_text(canonical_text(raw[record.raw_index], "memos"))
        assert record.text in context
    assert records[5].text not in context
    assert all(text in all_injection_templates() for text in annotations)
    assert json.dumps(raw, sort_keys=True) == raw_before
    return {"rendered_raw_indices": [mapping[value].raw_index for value in ids], "mutation": False}


def test_estimation_validation_and_safety() -> dict[str, Any]:
    records = adapt([{"text": "first"}, {"text": "second"}], "memos")
    payload = {"premise_conflict": "bad", "sufficiency": 4.0, "risk": -1.0,
               "memories": [{"id": "m1", "relation": {name: 2.0 for name in RELATIONS},
                             "condition_present": True, "condition_text": "if allowed",
                             "condition_satisfied": "invalid", "entity_match": "invalid"},
                            {"id": "outside", "relation": one_hot("SUPPORT")} ]}
    result = validate_estimate(payload, records)
    assert set(result.memories) == {"m1", "m2"}
    assert math.isclose(sum(result.memories["m1"].relation_posterior.values()), 1.0)
    assert result.memories["m1"].condition_satisfied == "UNKNOWN"
    assert result.memories["m1"].entity_match == "UNCLEAR"
    assert result.memories["m2"].relation_posterior == one_hot("INSUFFICIENT")
    assert result.risk == 0.0 and result.sufficiency == 1.0 and not result.premise_conflict
    bad_posterior = copy.deepcopy(payload)
    bad_posterior["memories"][0]["relation"] = {name: float("nan") for name in RELATIONS}
    assert validate_estimate(bad_posterior, records).memories["m1"].relation_posterior == one_hot("INSUFFICIENT")
    sample = deployment([{"text": "fact"}])
    baseline_bytes = sample.context_str_full.encode("utf-8")
    failed = safe_estimate(adapt(sample.raw_memories, "memos"))
    for arm in MAIN_ARMS:
        if arm in {"B0", "B1"}:
            continue
        output = run_pipeline_detailed(sample, arm, tau=-math.inf, estimate_result=failed)
        assert output.no_op and output.context.encode("utf-8") == baseline_bytes
    return {"missing_ids_repaired": True, "posterior_normalized": True,
            "invalid_posteriors_safe": True, "failed_estimation_noop_all_dynamic_arms": True}


def test_noop_bypass_and_ablation() -> dict[str, Any]:
    raw = [{"text": "a fact", "memory_key": "one"}, {"text": "unrelated", "memory_key": "two"}]
    sample = deployment(raw)
    records = adapt(raw, "memos")
    result = synthetic_estimate(records, ["SUPPORT", "INSUFFICIENT"], risk=0.2)
    noop = run_pipeline_detailed(sample, "A2", tau=0.2, estimate_result=result)
    assert noop.no_op and noop.context == sample.context_str_full
    assert run_pipeline_detailed(sample, "B0").context == sample.context_str_full
    assert run_pipeline_detailed(sample, "B1").context == sample.context_str_full + "\n\n" + B1_STATIC_INSTRUCTION
    all_block = synthetic_estimate(records, ["INSUFFICIENT", "INSUFFICIENT"])
    bypass = run_pipeline_detailed(sample, "A2", tau=-math.inf, estimate_result=all_block)
    assert bypass.no_op and bypass.bypass and bypass.context == sample.context_str_full
    empty = run_pipeline_detailed(deployment([{}]), "A2", tau=-math.inf)
    assert empty.no_op and empty.bypass
    no_gate = run_pipeline_detailed(sample, "A2-nogate", tau=0.9, estimate_result=result)
    assert not no_gate.no_op
    decisions = decide(sample.question, records, result)
    before = copy.deepcopy(decisions)
    assert all(d.use == "ASSERT" for d in apply_ablation(decisions, "A2-nolic"))
    assert all(d.action != Action.BLOCK for d in apply_ablation(decisions, "A2-noblock"))
    assert decisions == before, "ablation mutated shared decisions"
    assert run_pipeline_detailed(sample, "A2-nolic", tau=-math.inf, estimate_result=result).annotations == [LICENSE_TEMPLATES["VOUCH"]]
    assert not run_pipeline_detailed(sample, "A2-noblock", tau=-math.inf, estimate_result=all_block).bypass
    assert run_pipeline_detailed(sample, "A2-nosal", tau=-math.inf, estimate_result=result).annotations == []
    b2 = b2_decisions(records, result)
    assert [d.action for d in b2] == [Action.VOUCH, Action.BLOCK]
    mixed = copy.deepcopy(result)
    mixed.memories["m1"].relation_posterior = {name: 0.5 if name in {"SUPPORT", "INSUFFICIENT"} else 0.0 for name in RELATIONS}
    assert b2_decisions(records, mixed)[0].action == Action.VOUCH
    assert decide(sample.question, records, mixed)[0].action == Action.QUALIFY
    try:
        run_pipeline_detailed({"question": "q", "raw_memories": raw}, "B0")  # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("Pipeline accepted an unallowlisted dictionary")
    return {"byte_exact_noop": True, "all_block_bypass": True, "ablation_nonmutation": True}


def test_scope_constraints() -> dict[str, Any]:
    records = adapt([{"text": "If the permit is valid, access is allowed."}], "memos")
    result = synthetic_estimate(records, ["SUPPORT"])
    item = result.memories["m1"]
    item.condition_present, item.condition_text, item.condition_satisfied = True, "If the permit is valid", "UNKNOWN"
    qualified = decide("Is access allowed?", records, result)[0]
    assert qualified.scope == "CONDITIONAL" and qualified.action == Action.QUALIFY
    item.condition_text = "invented condition not in the record"
    assert decide("Is access allowed?", records, result)[0].scope == "UNCONDITIONAL"
    item.condition_text = "If the permit is valid"
    item.relation_posterior = one_hot("REFUTE")
    assert decide("Is access allowed?", records, result)[0].action == Action.REFUTE
    return {"condition_requires_record_substring": True, "refutation_priority": True}


def test_label_isolation() -> dict[str, Any]:
    assert list(inspect.signature(estimate).parameters) == ["question", "records"]
    assert not {field.name for field in fields(DeploymentSample)} & FORBIDDEN_FIELDS
    for filename in ("a2_schema.py", "a2_stage0_adapter.py", "a2_stage1_estimator.py",
                     "a2_stage2_decision.py", "a2_stage3_render.py", "a2_pipeline.py"):
        tree = ast.parse((BASE_DIR / filename).read_text(encoding="utf-8"))
        literals = {node.value for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        assert not literals & FORBIDDEN_FIELDS, (filename, literals & FORBIDDEN_FIELDS)
    longmemeval = load_numbered("a2_invariant_longmemeval", "25_build_longmemeval.py")
    source = {"question": "Where did I move?", "question_id": "question_abs",
              "question_type": "abstention", "question_date": "2024-01-01", "answer": "Paris",
              "answer_session_ids": ["answer_secret_abs"],
              "haystack_session_ids": ["answer_secret_abs", "other_abs"],
              "haystack_dates": ["2023-01-01", "2023-02-01"],
              "haystack_sessions": [[{"role": "user", "content": "I moved to Paris.", "has_answer": True}],
                                    [{"role": "assistant", "content": "Thanks.", "has_answer": False}]]}
    row = longmemeval.adapt_case(source, "longmemeval:0001")
    visible = json.dumps({"question": row["question"], "raw_memories": row["raw_memories"],
                          "context": row["context_str_full"]}, ensure_ascii=False)
    for forbidden in ("answer_secret_abs", "other_abs", "question_abs", "has_answer", "answer_session_ids", "abstention"):
        assert forbidden not in visible, forbidden
    assert "user:" in visible and "assistant:" in visible and "2023-01-01" in visible
    assert row["recall_at_20"] == 1.0
    return {"two_input_estimator": True, "deployment_schema_allowlisted": True,
            "gold_hint_session_ids_hidden": True}


class MockEstimatorClient:
    """The tests never construct a real client or touch credentials/network."""
    def __init__(self, content: str) -> None:
        self.content, self.calls = content, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **options: Any) -> "MockEstimatorClient":
        assert options.get("max_retries") == 0
        return self

    def create(self, **options: Any) -> Any:
        self.calls += 1
        assert options["temperature"] == 0
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))],
                               usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})


def test_estimator_cache_and_exception() -> dict[str, Any]:
    records = adapt([{"text": "Paris", "event_time": "2023-01-01", "confidence": 0.8}], "memos")
    content = json.dumps({"premise_conflict": False, "risk": 0.8, "sufficiency": 0.8,
                          "memories": [{"id": "m1", "relation": one_hot("SUPPORT"),
                                        "condition_present": False, "condition_text": "",
                                        "condition_satisfied": "UNKNOWN", "entity_match": "MATCH"}]})
    client = MockEstimatorClient(content)
    with tempfile.TemporaryDirectory(prefix="a2_invariant_cache_") as folder:
        first = estimate_cached("Where?", records, "neutral:1", "pool", folder, client=client)
        second = estimate_cached("Where?", records, "neutral:1", "pool", folder, client=client)
        assert client.calls == 1 and not first.telemetry["cache_hit"] and second.telemetry["cache_hit"]
        third = estimate_cached("Where now?", records, "neutral:1", "pool", folder, client=client)
        assert client.calls == 2 and not third.telemetry["cache_hit"]
        key = estimate_cache_key("Where?", records)
        assert key != estimate_cache_key("Where?", [replace(records[0], text="Rome")])
        assert key != estimate_cache_key("Where?", [replace(records[0], event_time="2024-01-01")])
        assert key != estimate_cache_key("Where?", [replace(records[0], retrieval_score=0.99)])
        assert key != estimate_cache_key("Where?", records, "different-model")
        parallel = MockEstimatorClient(content)
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = [executor.submit(estimate_cached, "same concurrent input", records,
                                       "neutral:shared", "pool", folder, client=parallel)
                       for _ in range(12)]
            concurrent_results = [future.result() for future in futures]
        assert parallel.calls == 1 and len(concurrent_results) == 12
        invalid = MockEstimatorClient("not json")
        from e1_memos_oracle_common import retry_call
        with patch("a2_stage1_estimator.retry_call", lambda label, fn, **kwargs: retry_call(label, fn, retries=3, sleep_base=0)):
            failed = estimate_cached("invalid", records, "neutral:failed", "pool", folder, client=invalid)
        assert invalid.calls == 3 and failed.failed and failed.risk == 0.0
    return {"identical_input_one_call": True, "changed_input_cache_miss": True,
            "invalid_json_three_mock_attempts_then_safe": True, "external_api_calls": 0}


def test_calibration_formula_and_conflict() -> dict[str, Any]:
    module = load_numbered("a2_invariant_calibration_synthetic", "a2_calibrate.py")
    rows = [{"case_id": "synthetic:a", "risk": 0.1, "baseline_wrong": True},
            {"case_id": "synthetic:b", "risk": 0.2, "baseline_wrong": False}]
    curve = module.threshold_curve(rows)
    assert [point["noop_err"] for point in curve] == [0.0, 1.0, 0.5]
    assert [point["coverage"] for point in curve] == [0.0, 0.5, 1.0]
    try:
        module.assert_noop_error_monotonic(rows)
    except AssertionError:
        pass
    else:
        raise AssertionError("Strict empirical-ratio test failed to expose the 1.0 -> 0.5 decrease")
    assert module.json_safe(-math.inf) == "-inf"
    identifiers: dict[str, list[str]] = {"cal": [], "test": []}
    index = 0
    while any(len(values) < 2 for values in identifiers.values()):
        cid = f"synthetic:split:{index}"
        identifiers[module.calibration_split(cid)].append(cid)
        index += 1
    split_rows = [{"case_id": cid, "risk": 0.1 if i == 0 else 0.2, "baseline_wrong": i != 0}
                  for group in identifiers.values() for i, cid in enumerate(group[:2])]
    result = module.calibrate_rows(split_rows, alpha=0.1)
    assert result["n_cal"] == 2 and result["tau"] == 0.1
    assert result["coverage"] == 0.5 and result["noop_err"] == 0.0
    assert result["test"]["coverage"] == 0.5 and result["test"]["noop_err"] == 0.0
    degenerate = module.calibrate_rows([{**row, "baseline_wrong": True} for row in split_rows], alpha=0.1)
    assert degenerate["degenerate_flag"] and degenerate["tau"] == -math.inf
    return {"exact_ratio_not_smoothed": True,
            "counterexample_to_universal_monotonicity": [0.0, 1.0, 0.5],
            "strict_guard_detects_counterexample": True, "does_not_verify_real_invariant_10": True,
            "sha_split_threshold_and_degeneracy_verified": True}


def get_leak_checker() -> Callable[..., list[str]]:
    module = load_numbered("a2_invariant_generation", "21_run_generation.py")
    checker = getattr(module, "check_all_template_leakage", None)
    if not callable(checker):
        raise PendingCheck("Runner's complete fixed-template/5-gram checker is not yet implemented")
    return checker


def test_leak_checker_boundary() -> dict[str, Any]:
    checker = get_leak_checker()
    import e1_memos_oracle_common as legacy
    old_templates = copy.deepcopy(legacy.LICENSE_TEMPLATES)
    clean = {"gold_answer": "unrelated sapphire glacier station", "gold_evidence": ["different lunar violet orchard"]}
    assert checker(clean) == []
    bad = {"gold_answer": LICENSE_TEMPLATES["VOUCH"], "gold_evidence": []}
    assert checker(bad), "Checker missed a complete fixed-template answer leak"
    invalid = checker(clean, ["a new invented license"])
    assert invalid, "Checker accepted a non-fixed injection"
    module = sys.modules["a2_invariant_generation"]
    tokenizer = module.TOKEN_RE.findall
    assert len(tokenizer("one two three four five")) == 5
    template_tokens = tokenizer(LICENSE_TEMPLATES["VOUCH"].lower())
    # Surround the shared subsequence with novel tokens so old whole-answer
    # equality cannot masquerade as the new >=5-token boundary check.
    five = "opaquezz " + " ".join(template_tokens[4:9]) + " suffixzz"
    four = "opaquezz " + " ".join(template_tokens[4:8]) + " suffixzz"
    five_answer = checker({"gold_answer": five, "gold_evidence": []}, [LICENSE_TEMPLATES["VOUCH"]])
    five_evidence = checker({"gold_answer": "unrelated", "gold_evidence": [five]}, [LICENSE_TEMPLATES["VOUCH"]])
    four_issues = checker({"gold_answer": four, "gold_evidence": []}, [LICENSE_TEMPLATES["VOUCH"]])
    assert "gold_answer_5gram_in_license" in five_answer
    assert "gold_evidence_5gram_in_license" in five_evidence
    assert not any("5gram" in issue for issue in four_issues)
    assert legacy.LICENSE_TEMPLATES == old_templates, "Boundary checker mutated legacy template globals"
    return {"all_fixed_templates_enumerated": len(all_injection_templates()) + 1,
            "unknown_injection_rejected": True, "five_token_answer_and_evidence_hits": True,
            "four_tokens_no_fivegram_hit": True, "legacy_globals_unchanged": True}


def test_generation_cache_all_factors() -> dict[str, Any]:
    module = load_numbered("a2_invariant_generation_cache", "21_run_generation.py")
    endpoint = {"generator": "fixture", "model": "fixture-model", "base_url": "https://fixture.invalid",
                "key_variable": "TEST_KEY_NAME", "url_variable": "TEST_URL_NAME"}
    meta = {"sample_input_hash": "s", "context_hash": "c", "controller_hashes": {"stage0": "v1"},
            "estimate_input_hash": "e", "tau": "0.1", "lambda_o": 1.0}
    key = module.generation_cache_key("neutral:1", "A2", "prompt", endpoint, meta)
    for arm in ("A2-nogate", "A2-nosal", "A2-nolic", "A2-noblock", "B2", "B1", "B0"):
        assert module.generation_cache_key("neutral:1", arm, "prompt", endpoint, meta) != key, arm
    for field, value in (("sample_input_hash", "changed"), ("context_hash", "changed"),
                         ("controller_hashes", {"stage0": "v2"}), ("estimate_input_hash", "changed"),
                         ("tau", "0.2"), ("lambda_o", 0.3)):
        assert module.generation_cache_key("neutral:1", "A2", "prompt", endpoint, {**meta, field: value}) != key, field
    assert module.generation_cache_key("neutral:1", "A2", "changed prompt", endpoint, meta) != key
    for field, value in (("model", "other"), ("base_url", "https://other.invalid")):
        assert module.generation_cache_key("neutral:1", "A2", "prompt", {**endpoint, field: value}, meta) != key
    sample = {"question": "q", "raw_memories": [{"text": "fact"}], "system_kind": "memos",
              "user_name": "u", "context_str_full": "archived", "pref_note": "", "gold_answer": "secret",
              "question_type": "forbidden", "baseline_label": "correct", "gold_memory_ids": ["m1"]}
    changed_analysis = {**sample, "gold_answer": "different", "baseline_label": "hallucination",
                        "question_type": "other", "gold_memory_ids": []}
    assert module.sample_input_hash(sample) == module.sample_input_hash(changed_analysis)
    assert not vars(module.deployment_view(sample)).keys() & FORBIDDEN_FIELDS
    return {"all_arm_tau_lambda_endpoint_prompt_controller_estimate_context_factors_keyed": True,
            "analysis_labels_do_not_change_deployment_identity": True}


def test_b0_artifact_linkage() -> dict[str, Any]:
    sample = {"case_id": "synthetic:linkage", "context_str_full": "the frozen baseline"}
    generation = {"case_id": sample["case_id"], "cache_key": "generation-key", "ok": True,
                  "context_hash": sha256_text(sample["context_str_full"])}
    verdict = {"case_id": sample["case_id"], "judge_label": "correct", "ok": True,
               "generation_cache_key": "generation-key"}
    with tempfile.TemporaryDirectory(prefix="a2_invariant_linkage_") as folder:
        out = Path(folder)
        gen_path = out / "generations" / "memos" / "B0__fixture.jsonl"
        verdict_path = out / "verdicts" / "memos" / "B0__fixture.jsonl"
        gen_path.parent.mkdir(parents=True)
        verdict_path.parent.mkdir(parents=True)
        gen_path.write_text(json.dumps(generation) + "\n", encoding="utf-8")
        verdict_path.write_text(json.dumps(verdict) + "\n", encoding="utf-8")
        assert actual_b0_verdicts(out, "fixture", [sample]) == {sample["case_id"]: "correct"}
        verdict_path.write_text(json.dumps({**verdict, "generation_cache_key": "stale"}) + "\n", encoding="utf-8")
        try:
            actual_b0_verdicts(out, "fixture", [sample])
        except PendingCheck:
            pass
        else:
            raise AssertionError("Stale judge/generation linkage was accepted")
    return {"fresh_context_and_generation_key_required": True, "synthetic_fixture_only": True}


def require_full_pool(out_dir: Path) -> list[dict[str, Any]]:
    path = out_dir / "pools" / "memos_pool.jsonl"
    summary_path = out_dir / "pools" / "memos_pool_summary.json"
    if not path.is_file() or not summary_path.is_file():
        raise PendingCheck(f"Complete new pool/summary missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("source_audit_complete"):
        raise PendingCheck("New pool source support audit is incomplete")
    rows = read_jsonl(path)
    if not rows or len(rows) != summary.get("pool_n"):
        raise PendingCheck("New pool length does not equal its complete-pool summary")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != summary.get("pool_sha256"):
        raise PendingCheck("New pool hash disagrees with its audited summary")
    assert len({r["case_id"] for r in rows}) == len(rows), "duplicate pool case IDs"
    assert all(r.get("serializer_ok") is True and r.get("gold_evidence")
               and r.get("retrieval_stratum") in {"strict_supported", "partial_supported"} for r in rows)
    assert any(r.get("baseline_label") == "correct" for r in rows), "do-no-harm source group absent"
    assert any(r.get("baseline_label") != "correct" for r in rows), "source wrong group absent"
    return rows


def actual_b0_verdicts(out_dir: Path, generator: str, pool: list[dict[str, Any]]) -> dict[str, str]:
    path = out_dir / "verdicts" / "memos" / f"B0__{generator}.jsonl"
    generation_path = out_dir / "generations" / "memos" / f"B0__{generator}.jsonl"
    if not path.is_file() or not generation_path.is_file():
        raise PendingCheck(f"Real B0 replay generations/verdicts are missing: {generation_path}, {path}")
    source = {str(row["case_id"]): row for row in pool}
    generations = {str(row["case_id"]): row for row in read_jsonl(generation_path)
                   if row.get("ok", True) and not row.get("error")}
    by_id: dict[str, str] = {}
    for row in read_jsonl(path):
        if not row.get("ok", True) or row.get("error") or row.get("leakage"):
            continue
        cid = str(row["case_id"])
        generation = generations.get(cid)
        sample = source.get(cid)
        if sample is None or generation is None:
            continue
        if (generation.get("context_hash") != sha256_text(sample["context_str_full"])
                or row.get("generation_cache_key", row.get("gen_cache_key")) != generation.get("cache_key")):
            continue
        label = row.get("judge_label", row.get("label", row.get("verdict")))
        label = {"C": "correct", "H": "hallucination", "O": "omission"}.get(label, label)
        if label in {"correct", "hallucination", "omission"}:
            by_id[cid] = str(label)
    missing = {r["case_id"] for r in pool} - set(by_id)
    if missing:
        raise PendingCheck(f"Real B0 replay verdicts incomplete: {len(missing)}/{len(pool)} absent")
    return by_id


def test_full_08_leakage(pool: list[dict[str, Any]]) -> dict[str, Any]:
    checker = get_leak_checker()
    hits = []
    for sample in pool:
        issues = checker(sample)
        if issues:
            hits.append({"case_id": sample["case_id"], "issues": issues})
    assert not hits, f"Full-pool fixed-template leakage found: {hits[:5]} (total={len(hits)})"
    return {"full_pool_cases": len(pool), "hits": 0, "fixed_templates": len(all_injection_templates()) + 1}


def test_full_10_noop_monotonic(pool: list[dict[str, Any]], out_dir: Path, generator: str) -> dict[str, Any]:
    module = load_numbered("a2_invariant_calibration", "a2_calibrate.py")
    verdicts = actual_b0_verdicts(out_dir, generator, pool)
    rows = []
    missing = []
    for sample in pool:
        path = estimate_cache_path(sample["case_id"], "memos", out_dir)
        if not path.is_file():
            missing.append(sample["case_id"])
            continue
        cache = json.loads(path.read_text(encoding="utf-8"))
        records = adapt(sample["raw_memories"], "memos")
        expected = estimate_cache_key(sample["question"], records, cache.get("model", generator))
        if cache.get("input_hash") != expected:
            missing.append(sample["case_id"])
            continue
        result = _load_cached(path, expected, records)
        if result is None:
            missing.append(sample["case_id"])
            continue
        assert 0 <= result.risk <= 1 and math.isfinite(result.risk)
        if module.calibration_split(sample["case_id"]) == "cal":
            rows.append({"case_id": sample["case_id"], "risk": result.risk,
                         "baseline_wrong": verdicts[sample["case_id"]] != "correct"})
    if missing:
        raise PendingCheck(f"Input-hashed Stage 1 cache incomplete: {len(missing)}/{len(pool)} absent/stale")
    if not rows:
        raise PendingCheck("Calibration split has no eligible full-pool rows")
    # This is the actual requested empirical ratio assertion. No isotonic
    # smoothing, replacement formula, synthetic curve, or test weakening.
    curve = module.threshold_curve(rows)
    write_json(out_dir / "analysis" / "invariant_10_actual_noop_curve.json",
               module.json_safe({"calibration_n": len(rows), "source": "fresh_B0_plus_input_hashed_full_pool_estimates",
                                 "curve": curve, "formula_unchanged": True}))
    module.assert_noop_error_monotonic(rows)
    return {"calibration_n": len(rows), "candidate_thresholds": len(curve),
            "formula": "sum(noop*baseline_wrong)/max(1,sum(noop))", "smoothed": False}


def test_full_11_pool_equivalence(pool: list[dict[str, Any]], out_dir: Path, generator: str) -> dict[str, Any]:
    verdicts = actual_b0_verdicts(out_dir, generator, pool)
    old_path = ROOT / "outputs" / "e1_memos_full_oracle_v2" / "samples_memos_full.jsonl"
    old_ids = {r["case_id"] for r in read_jsonl(old_path)}
    assert len(old_ids) == 1987, f"Original frozen comparison set changed: {len(old_ids)}"
    new_wrong = {r["case_id"] for r in pool if verdicts[r["case_id"]] != "correct"}
    result = {"equivalent": new_wrong == old_ids, "old_wrong_n": len(old_ids),
              "new_replayed_wrong_n": len(new_wrong), "missing_from_new": sorted(old_ids - new_wrong),
              "new_only": sorted(new_wrong - old_ids),
              "check_performed": True, "basis": "actual full-pool B0 replay verdicts"}
    write_json(out_dir / "analysis" / "invariant_11_pool_equivalence.json", result)
    try:
        assert new_wrong == old_ids, "New B0 wrong set differs from original 1987"
    except AssertionError:
        # §13 explicitly makes this difference nonblocking; it is NOT equality.
        raise SpecWaiver(json.dumps({**result, "waived_by_spec": "13: pool difference is nonblocking"}, ensure_ascii=False))
    return result


def test_full_12_nondegenerate_groups(pool: list[dict[str, Any]]) -> dict[str, Any]:
    result = probe_groups(pool)
    assert result["multi_record_group_count"] > 0, "Real full pool has zero groups of size >=2"
    return result


def run_check(identifier: str, function: Callable[[], Any]) -> dict[str, Any]:
    try:
        details = function()
        result = {"test": identifier, "status": "pass", "details": details}
    except PendingCheck as error:
        result = {"test": identifier, "status": "pending", "reason": str(error)}
    except SpecWaiver as error:
        result = {"test": identifier, "status": "waived_by_spec", "details": json.loads(str(error))}
    except Exception as error:
        result = {"test": identifier, "status": "fail", "reason": f"{type(error).__name__}: {error}"}
    print(f"{identifier}: {result['status']}" + (f" — {result['reason']}" if "reason" in result else ""), flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Synthetic checks only; never claims full-pool success")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--generator", default="deepseek-chat")
    args = parser.parse_args()
    print("Budget: 0 external LLM/API/download calls; synthetic client calls are mocked", flush=True)
    results = []
    synthetic = [
        ("01_adapter_complete", test_01_adapter_complete), ("02_time_exhaustive", test_02_time_exhaustive),
        ("03_cost_matrix", test_03_cost_matrix), ("04_weighted_hedging", test_04_weighted_hedging),
        ("05_exclusive_sets", test_05_exclusive_sets), ("06_aggregates_unchanged", test_06_aggregates_unchanged),
        ("07_authorization_lock", test_07_authorization_lock), ("09_frozen_render", test_09_frozen_render),
        ("extra_estimation_validation", test_estimation_validation_and_safety),
        ("extra_noop_bypass_ablation", test_noop_bypass_and_ablation),
        ("extra_scope_constraints", test_scope_constraints), ("extra_label_isolation", test_label_isolation),
        ("extra_estimator_cache_exception", test_estimator_cache_and_exception),
        ("extra_calibration_formula_conflict", test_calibration_formula_and_conflict),
        ("extra_leak_checker_boundary", test_leak_checker_boundary),
        ("extra_generation_cache_factors", test_generation_cache_all_factors),
        ("extra_b0_artifact_linkage", test_b0_artifact_linkage),
    ]
    for identifier, function in synthetic:
        results.append(run_check(identifier, function))
    full_identifiers = ("08_full_pool_leakage", "10_real_noop_monotonic", "11_real_pool_equivalence", "12_real_group_nondegeneration")
    if args.offline:
        results.extend({"test": identifier, "status": "not_run_offline",
                        "reason": "Synthetic-only mode does not establish the required full-pool invariant"}
                       for identifier in full_identifiers)
    else:
        pool_check = run_check("full_pool_complete", lambda: {"n": len(require_full_pool(args.out_dir))})
        results.append(pool_check)
        if pool_check["status"] == "pass":
            pool = require_full_pool(args.out_dir)
            functions = (
                lambda: test_full_08_leakage(pool),
                lambda: test_full_10_noop_monotonic(pool, args.out_dir, args.generator),
                lambda: test_full_11_pool_equivalence(pool, args.out_dir, args.generator),
                lambda: test_full_12_nondegenerate_groups(pool),
            )
            results.extend(run_check(identifier, function) for identifier, function in zip(full_identifiers, functions))
        else:
            results.extend({"test": identifier, "status": "pending", "reason": pool_check.get("reason", "pool check failed")}
                           for identifier in full_identifiers)
    failed = [r for r in results if r["status"] == "fail"]
    pending = [r for r in results if r["status"] == "pending"]
    waived = [r for r in results if r["status"] == "waived_by_spec"]
    full_verified = not args.offline and not failed and not pending
    report = {"mode": "offline_synthetic" if args.offline else "full_pool", "seed": SEED,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "external_api_calls": 0, "synthetic_checks": len(synthetic), "results": results,
              "failed": len(failed), "pending": len(pending), "waived_by_spec": len(waived),
              "full_pool_verified": full_verified, "all_assertions_passed": full_verified and not waived,
              "smoke_all_green_proven": False,
              "overall": "failed" if failed else "pending" if pending else "synthetic_pass" if args.offline else "full_verified"}
    output = args.out_dir / "analysis" / ("invariants_offline.json" if args.offline else "invariants_full.json")
    write_json(output, report)
    config_path = args.out_dir / "run_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config["invariants"] = {"mode": report["mode"], "seed": SEED, "estimated_calls": 0,
                            "script_sha256": report["script_sha256"],
                            "report": str(output), "overall": report["overall"]}
    write_json(config_path, config)
    print(json.dumps({key: report[key] for key in ("overall", "failed", "pending", "full_pool_verified", "smoke_all_green_proven")}, ensure_ascii=False), flush=True)
    return 1 if failed else 2 if pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
