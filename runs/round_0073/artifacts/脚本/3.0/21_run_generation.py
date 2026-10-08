"""Budgeted, resumable generation for the fixed four-stage A2 experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any

from dotenv import dotenv_values
from openai import OpenAI

import e1_memos_oracle_common as common
from a2_arms import B1_STATIC_INSTRUCTION, MAIN_ARMS, get_arm
from a2_pipeline import run_pipeline_detailed
from a2_schema import Action, DeploymentSample, EstimateResult
from a2_stage0_adapter import adapt
from a2_stage1_estimator import estimate_cache_key, estimate_cache_path, estimate_cached
from a2_stage3_render import all_injection_templates

OUT_DIR = common.ROOT / "outputs" / "a2_mvp_v1"
SEED = common.SEED
VERSION = "a2-generation-v1"
MAX_WORKERS = 12
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u3400-\u9fff]")


def json_hash(value: Any) -> str:
    return common.sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                        separators=(",", ":"), allow_nan=False))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def merge_config(section: str, payload: dict[str, Any], out_dir: Path) -> None:
    path = out_dir / "run_config.json"
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current.setdefault("seed", SEED)
    current[section] = payload
    common.write_json(path, current)


def deployment_view(sample: dict[str, Any]) -> DeploymentSample:
    """Physically remove all answer and benchmark fields before deployment."""
    return DeploymentSample(
        question=str(sample["question"]), raw_memories=list(sample["raw_memories"]),
        system_kind=str(sample.get("system_kind") or sample.get("system") or "memos"),
        user_name=str(sample.get("user_name") or ""),
        context_str_full=str(sample["context_str_full"]),
        pref_note=str(sample.get("pref_note") or ""),
    )


def sample_input_hash(sample: dict[str, Any]) -> str:
    return json_hash(vars(deployment_view(sample)))


def fixed_injection_templates() -> tuple[str, ...]:
    return (*all_injection_templates(), B1_STATIC_INSTRUCTION)


def check_all_template_leakage(sample: dict[str, Any],
                               annotations: list[str] | None = None) -> list[str]:
    """Reuse the legacy checks without modifying its module/template globals.

    Its old-template membership predicate is replaced by the complete new fixed
    enumeration; its answer checks are retained. Five-token checks cover both
    the answer and supporting text, including Chinese character tokens.
    """
    labels = list(fixed_injection_templates()) if annotations is None else annotations
    values = sample.get("gold_evidence") or []
    values = values if isinstance(values, list) else [values]
    boundary = {"gold_answer": str(sample.get("gold_answer") or ""),
                "gold_evidence": [str(value) for value in values]}
    errors = [error for error in common.check_license_leakage(boundary, labels)
              if error != "license_text_not_fixed_template"]
    fixed = set(fixed_injection_templates())
    references = [("gold_answer", boundary["gold_answer"]),
                  *(("gold_evidence", value) for value in boundary["gold_evidence"])]
    for label in labels:
        if label not in fixed:
            errors.append("license_text_not_fixed_template")
        label_tokens = TOKEN_RE.findall(label.lower())
        windows = {tuple(label_tokens[i:i + 5]) for i in range(len(label_tokens) - 4)}
        for name, text in references:
            tokens = TOKEN_RE.findall(text.lower())
            if any(tuple(tokens[i:i + 5]) in windows for i in range(len(tokens) - 4)):
                errors.append(f"{name}_5gram_in_license")
    return sorted(set(errors))


def select_samples(samples: list[dict[str, Any]], limit: int = 0,
                   subset: int = 0) -> list[dict[str, Any]]:
    if limit < 0 or subset < 0 or (limit and subset):
        raise ValueError("Use one nonnegative --limit or --subset, not both")
    ordered = sorted(samples, key=lambda row: str(row["case_id"]))
    if len({str(row["case_id"]) for row in ordered}) != len(ordered):
        raise ValueError("Pool case ids are not unique")
    count = limit or subset
    if count:
        random.Random(SEED).shuffle(ordered)
        ordered = ordered[:count]
    if limit == 150:
        if len(ordered) != 150:
            raise ValueError("Stage A smoke requires exactly 150 samples")
        if all(deployment_view(row).system_kind == "memos" for row in ordered):
            labels = {str(row.get("baseline_verdict") or row.get("baseline_label") or "")
                      for row in ordered}
            if "correct" not in labels or not labels.intersection({"hallucination", "omission"}):
                raise ValueError("The seeded 150-case smoke must contain archived correct and wrong cases")
    return ordered


def selection_name(limit: int = 0, subset: int = 0) -> str:
    return f"limit{limit}" if limit else f"subset{subset}" if subset else "full"


def selection_path(pool: str, out_dir: Path, limit: int = 0, subset: int = 0) -> Path:
    return out_dir / "analysis" / f"{pool}_selection_{selection_name(limit, subset)}.json"


def artifact_arm(arm: str, lambda_o: float = 1.0) -> str:
    return arm if lambda_o == 1.0 else f"{arm}__lambda_o_{lambda_o:g}"


def generator_registry(out_dir: Path = OUT_DIR) -> dict[str, dict[str, Any]]:
    """Read only the endpoints actually recorded by the mandatory preflight."""
    path = out_dir / "preflight.json"
    if not path.exists():
        raise FileNotFoundError(f"Mandatory endpoint preflight is missing: {path}")
    preflight = json.loads(path.read_text(encoding="utf-8"))
    values = dotenv_values(common.ENV_PATH)
    registry = {}
    for endpoint in preflight.get("endpoints") or []:
        key_name, url_name = endpoint["key_variable"], endpoint["url_variable"]
        if not values.get(key_name) or not values.get(url_name):
            raise RuntimeError(f"Preflight endpoint variables are no longer present: {key_name}/{url_name}")
        url = str(values[url_name]).rstrip("/")
        if url != str(endpoint["base_url"]).rstrip("/"):
            raise RuntimeError(f"Endpoint changed after preflight: {url_name}")
        if key_name == "OPENAI_API_KEY":
            model = str(endpoint.get("model") or common.MODEL)
        else:
            model_variable = key_name.removesuffix("_API_KEY") + "_MODEL"
            model = str(endpoint.get("model") or values.get(model_variable) or "")
            if not model:
                raise RuntimeError(f"No declared model for observed endpoint {key_name}; do not invent one")
        identifier = str(endpoint.get("generator_id") or model)
        if identifier in registry:
            raise RuntimeError("Observed endpoints require distinct declared generator ids")
        registry[identifier] = {"generator": identifier, "model": model,
                                "base_url": url, "key_variable": key_name,
                                "url_variable": url_name}
    if not registry:
        raise RuntimeError("No real endpoint was found by preflight")
    return registry


def make_endpoint_client(endpoint: dict[str, Any]) -> Any:
    if endpoint["key_variable"] == "OPENAI_API_KEY":
        return common.make_client().with_options(max_retries=0)
    values = dotenv_values(common.ENV_PATH)
    return OpenAI(api_key=values[endpoint["key_variable"]],
                  base_url=endpoint["base_url"], max_retries=0)


class TrackingClient:
    """Reuse existing calls while recording every real response/retry usage."""
    def __init__(self, client: Any, model: str, max_attempts: int):
        self.client, self.model, self.max_attempts = client, model, max_attempts
        self.events: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs: Any) -> Any:
        if len(self.events) >= self.max_attempts:
            raise RuntimeError("Documented API retry budget exhausted")
        kwargs = {**kwargs, "model": self.model, "temperature": 0}
        event: dict[str, Any] = {"attempt": len(self.events) + 1,
                                 "model": self.model, "max_tokens": kwargs.get("max_tokens")}
        self.events.append(event)
        started = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**kwargs)
            usage = getattr(response, "usage", None)
            event["usage"] = (usage.model_dump() if hasattr(usage, "model_dump") else
                              usage if isinstance(usage, dict) else {})
            event["ok"] = True
            return response
        except Exception as error:
            event["ok"] = False
            event["error"] = type(error).__name__
            raise
        finally:
            event["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

    def usage(self) -> dict[str, int]:
        total: Counter[str] = Counter()
        for event in self.events:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                total[key] += int(event.get("usage", {}).get(key) or 0)
        return dict(total)


def controller_hashes() -> dict[str, str]:
    directory = Path(__file__).parent
    return {name: file_hash(directory / name) for name in (
        "a2_schema.py", "a2_stage0_adapter.py", "a2_stage1_estimator.py",
        "a2_stage2_decision.py", "a2_stage3_render.py", "a2_pipeline.py", "a2_arms.py")}


def json_number(value: float | None) -> float | str | None:
    return "-inf" if value == -math.inf else value


def generation_cache_key(case_id: str, arm: str, prompt: str,
                         endpoint: dict[str, Any], context_meta: dict[str, Any]) -> str:
    return json_hash({"version": VERSION, "case_id": case_id, "arm": arm,
                      "prompt_hash": common.sha256_text(prompt), "endpoint": endpoint,
                      "temperature": 0, "max_tokens": common.GEN_MAX_TOKENS,
                      "sample_input_hash": context_meta["sample_input_hash"],
                      "context_hash": context_meta["context_hash"],
                      "controller_hashes": context_meta["controller_hashes"],
                      "estimate_input_hash": context_meta["estimate_input_hash"],
                      "tau": context_meta["tau"], "lambda_o": context_meta["lambda_o"]})


def prepare_estimates(samples: list[dict[str, Any]], pool: str, out_dir: Path,
                      client: Any, model: str, workers: int) -> tuple[dict[str, EstimateResult], dict[str, int]]:
    estimates: dict[str, EstimateResult] = {}
    usage: Counter[str] = Counter()

    def run(row: dict[str, Any]) -> tuple[str, EstimateResult]:
        view = deployment_view(row)
        records = adapt(view.raw_memories, view.system_kind)
        return str(row["case_id"]), estimate_cached(
            view.question, records, str(row["case_id"]), pool, out_dir, model, client)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run, row) for row in samples]
        for index, future in enumerate(as_completed(futures), 1):
            case_id, result = future.result()
            estimates[case_id] = result
            if not result.telemetry.get("cache_hit"):
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    usage[key] += int(result.telemetry.get("usage", {}).get(key) or 0)
            if index % 25 == 0 or index == len(samples):
                print(f"estimates completed={index}/{len(samples)}", flush=True)
    return estimates, dict(usage)


def ensure_tau(args: argparse.Namespace, samples: list[dict[str, Any]],
               estimates: dict[str, EstimateResult], gated: bool) -> float | None:
    if not gated:
        return None
    if args.tau is not None:
        return args.tau
    from a2_calibrate import (VERSION as calibration_version, calibrate_pool,
                             load_calibration_rows, validated_rows)
    calibration_pool = "longmemeval" if args.pool == "longmemeval" else "memos"
    path = args.out_dir / "calibration" / f"{calibration_pool}.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def identity(rows: list[dict[str, Any]], scope: str) -> str:
        value = {"version": calibration_version,
                 "rows": sorted(validated_rows(rows), key=lambda row: row["case_id"]),
                 "alpha": args.alpha, "scope": scope, "seed": SEED}
        return common.sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True))

    if args.pool not in {"memos", "longmemeval"}:
        if not saved or saved.get("scope") != "full":
            raise FileNotFoundError("Stage E requires the unchanged saved full memos calibration")
        rows = load_calibration_rows("memos", args.out_dir)
        if (saved.get("alpha") != args.alpha or saved.get("input_hash") != identity(rows, "full")):
            raise ValueError("Stage E memos calibration identity changed; recalibrate memos first, not Stage E")
        return float(saved["tau"])
    if args.pool == "memos" and args.limit == 150 and saved.get("scope") != "full":
        rows = []
        for sample in samples:
            label = str(sample.get("baseline_verdict") or sample.get("baseline_label") or "")
            if label not in {"correct", "hallucination", "omission"}:
                raise ValueError("Pilot calibration requires archived C/H/O for every selected sample")
            result = estimates[str(sample["case_id"])]
            rows.append({"case_id": str(sample["case_id"]), "risk": result.risk,
                         "baseline_wrong": label != "correct", "failed": result.failed,
                         "estimate_input_hash": result.telemetry.get("input_hash"),
                         "outcome_hash": common.sha256_text(label), "baseline_source": "archived_pilot"})
        if saved.get("alpha") == args.alpha and saved.get("input_hash") == identity(rows, "pilot"):
            return float(saved["tau"])
        print("Pilot tau uses the fixed sha split and archived baseline labels, NOT fresh B0", flush=True)
        return float(calibrate_pool("memos", args.out_dir, args.alpha, rows, scope="pilot")["tau"])
    # This loader refuses missing fresh B0 verdicts or stale/missing estimates.
    rows = load_calibration_rows(calibration_pool, args.out_dir)
    if saved.get("alpha") == args.alpha and saved.get("input_hash") == identity(rows, "full"):
        return float(saved["tau"])
    return float(calibrate_pool(calibration_pool, args.out_dir, args.alpha, rows, scope="full")["tau"])


def build_context_row(sample: dict[str, Any], arm: str, estimate: EstimateResult | None,
                      tau: float | None, lambda_o: float, hashes: dict[str, str],
                      out_dir: Path) -> dict[str, Any]:
    estimate = estimate if arm not in {"B0", "B1"} else None
    tau = tau if get_arm(arm).gate_enabled else None
    result = run_pipeline_detailed(deployment_view(sample), arm, tau, estimate,
                                   lambda_o, out_dir=out_dir)
    # Full enumeration is checked even when a gate/no-op injects no text.
    errors = check_all_template_leakage(sample)
    errors.extend(check_all_template_leakage(sample, result.annotations))
    estimate_hash = estimate.telemetry.get("input_hash") if estimate is not None else None
    if estimate is not None and not estimate_hash:
        estimate_hash = estimate_cache_key(sample["question"], result.records,
                                           estimate.telemetry.get("model", common.MODEL))
    metadata = {
        "case_id": str(sample["case_id"]), "arm": arm, "artifact_arm": artifact_arm(arm, lambda_o),
        "sample_input_hash": sample_input_hash(sample), "context": result.context,
        "context_hash": common.sha256_text(result.context), "records": [r.to_dict() for r in result.records],
        "decisions": [d.to_dict() for d in result.decisions], "annotations": result.annotations,
        "no_op": result.no_op, "bypass": result.bypass, "decision_note": result.decision_note,
        "n_records": len(result.records), "n_blocked": sum(d.action == Action.BLOCK for d in result.decisions),
        "estimate_input_hash": estimate_hash, "tau": json_number(tau), "lambda_o": lambda_o,
        "controller_hashes": hashes, "leakage_errors": sorted(set(errors)),
    }
    metadata["cache_key"] = json_hash(metadata)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", default="memos")
    parser.add_argument("--arm", default=",".join(MAIN_ARMS))
    parser.add_argument("--generator", default=common.MODEL)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--subset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--lambda-o", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--tau", type=float)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= MAX_WORKERS:
        parser.error("workers must be within 1..12")
    if not math.isfinite(args.lambda_o) or args.lambda_o < 0:
        parser.error("lambda-o must be finite and nonnegative")
    if args.tau is not None and (math.isnan(args.tau) or args.tau == math.inf):
        parser.error("tau cannot be NaN or positive infinity")
    return args


def main() -> None:
    args = parse_args()
    arms = list(dict.fromkeys(value.strip() for value in args.arm.split(",") if value.strip()))
    for arm in arms:
        if get_arm(arm).reference_only:
            raise ValueError("ORACLE_REL is archived reference only; do not rerun historical UA3")
    registry = generator_registry(args.out_dir)
    names = list(registry) if args.generator == "all" else [x.strip() for x in args.generator.split(",") if x.strip()]
    if not names or any(name not in registry for name in names):
        raise ValueError(f"Requested generator is not in actual preflight registry: {names}")
    pool_path = args.out_dir / "pools" / f"{args.pool}_pool.jsonl"
    if not pool_path.exists():
        raise FileNotFoundError(f"Required mixed/retrieval-defined pool is missing: {pool_path}")
    requested_limit, requested_subset = args.limit, args.subset
    samples = select_samples(common.read_jsonl(pool_path), args.limit, args.subset)
    additional_baseline = False
    if args.pool == "longmemeval" and "B0" not in arms:
        arms = ["B0", *arms]
        additional_baseline = True
    requires_estimate = args.estimate_only or any(arm not in {"B0", "B1"} for arm in arms)
    def pipeline_calls(count: int) -> int:
        generations = 0 if args.estimate_only else count * len(arms) * len(names)
        judges = generations * (2 if args.pool == "longmemeval" else 1)
        return count * int(requires_estimate) + generations + judges

    calls = pipeline_calls(len(samples))
    fallback = calls > 30_000 and not args.limit and not args.subset
    if fallback:
        args.subset = 400
        samples = select_samples(common.read_jsonl(pool_path), subset=400)
        calls = pipeline_calls(len(samples))
        print("Pipeline budget exceeds 30,000: effective selection is --subset 400; judge with --subset 400", flush=True)
    estimate_calls = len(samples) * int(requires_estimate)
    generation_calls = 0 if args.estimate_only else len(samples) * len(arms) * len(names)
    budget = {
        "pool": args.pool, "n_samples": len(samples), "arms": arms,
        "actual_generators": [registry[name] for name in names],
        "controller_generator": next(iter(registry)), "temperature": 0,
        "max_workers": args.workers, "estimated_calls_upper_bound": calls,
        "estimated_current_script_calls": estimate_calls + generation_calls,
        "estimated_estimator_calls": estimate_calls, "estimated_generation_calls": generation_calls,
        "estimated_attempts_upper_bound": estimate_calls * 3 + generation_calls * (12 if args.pool == "longmemeval" else 9),
        "estimated_judge_calls": generation_calls * (2 if args.pool == "longmemeval" else 1),
        "additional_longmemeval_B0": additional_baseline,
        "additional_B0_generation_calls": len(samples) * len(names) if additional_baseline else 0,
        "additional_B0_judge_calls": len(samples) * len(names) if additional_baseline else 0,
        "budget_fallback_400": fallback, "requested_limit": requested_limit, "requested_subset": requested_subset,
        "effective_selection": selection_name(args.limit, args.subset),
        "pool_sha256": file_hash(pool_path), "lambda_o": args.lambda_o, "alpha": args.alpha,
        "tau_explicit": json_number(args.tau), "estimate_only": args.estimate_only,
        "cache_policy": "all prompt-visible inputs, endpoint, configuration, controller hashes",
    }
    print(json.dumps({"Budget": budget}, ensure_ascii=False, indent=2), flush=True)
    merge_config(f"generation_{args.pool}_{selection_name(args.limit, args.subset)}", budget, args.out_dir)
    if args.dry_run:
        return
    if not args.yes:
        raise RuntimeError("Pass --yes after reviewing the printed API budget")

    manifest_path = selection_path(args.pool, args.out_dir, args.limit, args.subset)
    previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    selected_ids = [str(row["case_id"]) for row in samples]
    previous_context_keys = (previous_manifest.get("context_keys", {})
                             if previous_manifest.get("case_ids") == selected_ids
                             and previous_manifest.get("pool_sha256") == file_hash(pool_path) else {})
    manifest = {"pool": args.pool, "case_ids": selected_ids,
                "seed": SEED, "pool_sha256": file_hash(pool_path), "requested_limit": requested_limit,
                "requested_subset": requested_subset, "effective_count": len(samples),
                "effective_selection": selection_name(args.limit, args.subset),
                "budget_fallback_400": fallback, "arms": arms, "generators": names,
                "context_keys": previous_context_keys,
                "archived_baseline_distribution": dict(Counter(str(row.get("baseline_verdict") or
                                                                   row.get("baseline_label") or "") for row in samples))}
    common.write_json(selection_path(args.pool, args.out_dir, args.limit, args.subset), manifest)
    if args.limit == 150:
        common.write_json(args.out_dir / "analysis" / f"{args.pool}_smoke_manifest.json", manifest)
    estimates, estimation_usage = {}, {}
    controller_endpoint = registry[next(iter(registry))]
    if requires_estimate:
        estimates, estimation_usage = prepare_estimates(
            samples, args.pool, args.out_dir, make_endpoint_client(controller_endpoint),
            controller_endpoint["model"], args.workers)
    if args.estimate_only:
        common.write_json(args.out_dir / "analysis" / f"{args.pool}_estimate_run_summary.json",
                          {"scheduled": len(samples), "usage_this_run": estimation_usage,
                           "failed": sum(result.failed for result in estimates.values()), "manifest": manifest})
        return
    gated = any(get_arm(arm).gate_enabled for arm in arms)
    try:
        tau = ensure_tau(args, samples, estimates, gated)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        if args.pool != "longmemeval":
            raise
        # LongMemEval has no archived baseline. First produce/judge B0, then
        # calibrate from its fresh values and rerun the requested A2 arm.
        print(f"LongMemEval gated arms deferred until fresh B0 calibration: {type(error).__name__}", flush=True)
        arms = [arm for arm in arms if not get_arm(arm).gate_enabled]
        tau = None
        budget["deferred_gated_arms"] = True
        merge_config(f"generation_{args.pool}_{selection_name(args.limit, args.subset)}", budget, args.out_dir)
    hashes = controller_hashes()
    lock = Lock()
    tasks = []
    context_rows = []
    leakage = []
    for arm in arms:
        tag = artifact_arm(arm, args.lambda_o)
        manifest["context_keys"][tag] = {}
        context_path = args.out_dir / "contexts" / args.pool / f"{tag}.jsonl"
        decision_path = args.out_dir / "decisions" / args.pool / f"{tag}.jsonl"
        existing_contexts = {row.get("cache_key") for row in common.read_jsonl(context_path)}
        existing_decisions = {row.get("cache_key") for row in common.read_jsonl(decision_path)}
        existing_generations = {
            name: common.completed_by_cache(args.out_dir / "generations" / args.pool / f"{tag}__{name}.jsonl")
            for name in names
        }
        for sample in samples:
            context_meta = build_context_row(sample, arm, estimates.get(str(sample["case_id"])),
                                             tau, args.lambda_o, hashes, args.out_dir)
            context_meta["pool"] = args.pool
            manifest["context_keys"][tag][str(sample["case_id"])] = context_meta["cache_key"]
            context_rows.append(context_meta)
            if context_meta["cache_key"] not in existing_contexts:
                common.append_jsonl(context_path, context_meta, lock)
            if context_meta["cache_key"] not in existing_decisions:
                common.append_jsonl(decision_path, {key: value for key, value in context_meta.items()
                                                     if key != "context"}, lock)
            if context_meta["leakage_errors"]:
                row = {"case_id": sample["case_id"], "pool": args.pool, "arm": arm,
                       "context_hash": context_meta["context_hash"], "error_type": "leakage",
                       "errors": context_meta["leakage_errors"]}
                leakage.append(row)
                common.append_jsonl(args.out_dir / "leakage_failures.jsonl", row, lock)
                continue
            prompt = common.build_answer_prompt(context_meta["context"], sample["question"])
            for name in names:
                endpoint = registry[name]
                key = generation_cache_key(str(sample["case_id"]), arm, prompt, endpoint, context_meta)
                path = args.out_dir / "generations" / args.pool / f"{tag}__{name}.jsonl"
                if key not in existing_generations[name]:
                    tasks.append({"case_id": str(sample["case_id"]), "pool": args.pool, "arm": arm,
                                  "artifact_arm": tag, "generator": name, "endpoint": endpoint,
                                  "cache_key": key, "prompt": prompt, "context_meta": context_meta,
                                  "question": sample["question"], "path": path})
    common.write_json(manifest_path, manifest)
    if args.limit == 150:
        common.write_json(args.out_dir / "analysis" / f"{args.pool}_smoke_manifest.json", manifest)
    leakage_path = args.out_dir / "leakage_failures.jsonl"
    leakage_path.parent.mkdir(parents=True, exist_ok=True)
    leakage_path.touch(exist_ok=True)
    clients = {name: make_endpoint_client(registry[name]) for name in names}

    def run(task: dict[str, Any]) -> dict[str, Any]:
        tracked = TrackingClient(clients[task["generator"]], task["endpoint"]["model"], 3)
        meta = task["context_meta"]
        row = {key: task[key] for key in ("case_id", "pool", "arm", "artifact_arm", "generator", "cache_key")}
        row.update({"input_hash": task["cache_key"], "sample_input_hash": meta["sample_input_hash"],
                    "question": task["question"], "model": task["endpoint"]["model"],
                    "base_url": task["endpoint"]["base_url"], "temperature": 0,
                    "max_tokens": common.GEN_MAX_TOKENS, "context_hash": meta["context_hash"],
                    "prompt_hash": common.sha256_text(task["prompt"]), "prompt": task["prompt"],
                    "context_cache_key": meta["cache_key"], "estimate_input_hash": meta["estimate_input_hash"],
                    "no_op": meta["no_op"], "bypass": meta["bypass"], "decision_note": meta["decision_note"],
                    "tau": meta["tau"], "lambda_o": args.lambda_o, "controller_hashes": hashes})
        try:
            answer, api_meta = common.call_chat(tracked, task["prompt"])
            row.update({"ok": True, "model_answer": answer, "latency_ms": api_meta["latency_ms"]})
        except Exception as error:
            row.update({"ok": False, "error": type(error).__name__})
        row.update({"usage": tracked.usage(), "usage_by_attempt": tracked.events,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        common.append_jsonl(task["path"], row, lock)
        common.append_jsonl(args.out_dir / "analysis" / f"{args.pool}_generation_attempts.jsonl",
                            {key: row[key] for key in ("case_id", "arm", "generator", "cache_key", "ok",
                                                       "usage", "usage_by_attempt", "created_at")}, lock)
        return row

    generated_usage: Counter[str] = Counter()
    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run, task) for task in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            errors += int(not row["ok"])
            generated_usage.update(row["usage"])
            if index % 25 == 0 or index == len(tasks):
                print(f"generation completed={index}/{len(tasks)} failures={errors}", flush=True)
    summary = {"scheduled_generation_calls": len(tasks), "failed": errors,
               "leakage_failed_contexts": len(leakage), "tau": json_number(tau),
               "usage_generation_this_run": dict(generated_usage), "usage_estimation_this_run": estimation_usage,
               "manifest": manifest, "budget": budget,
               "no_op_contexts": sum(row["no_op"] for row in context_rows),
               "deferred_gated_arms": budget.get("deferred_gated_arms", False)}
    common.write_json(args.out_dir / "analysis" / f"{args.pool}_generation_run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
