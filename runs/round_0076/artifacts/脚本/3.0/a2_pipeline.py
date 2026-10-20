"""A single label-isolated Stage 0 -> 1 -> 2 -> 3 orchestrator."""
from __future__ import annotations

import json
import math
from pathlib import Path

from a2_arms import B1_STATIC_INSTRUCTION, apply_ablation, b2_decisions, get_arm
from a2_schema import Action, DeploymentSample, EstimateResult, PipelineResult
from a2_stage0_adapter import adapt
from a2_stage3_render import render_detailed


DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "outputs" / "a2_mvp_v1"


def _threshold(sample: DeploymentSample, tau: float | None,
               out_dir: str | Path | None) -> float:
    if tau is None:
        pool = "longmemeval" if sample.system_kind == "longmemeval" else "memos"
        path = Path(out_dir or DEFAULT_OUTPUT) / "calibration" / f"{pool}.json"
        if not path.is_file():
            raise ValueError(f"A2 requires an explicit calibrated tau or calibration file: {path}")
        with path.open(encoding="utf-8") as handle:
            calibration = json.load(handle)
        if "tau" not in calibration:
            raise ValueError(f"Calibration file has no tau: {path}")
        tau = calibration["tau"]
    try:
        threshold = float(tau)
    except (TypeError, ValueError) as exc:
        raise ValueError("Calibrated tau must be numeric, including -inf") from exc
    if math.isnan(threshold) or threshold == math.inf:
        raise ValueError("Calibrated tau cannot be NaN or positive infinity")
    return threshold


def run_pipeline_detailed(
    sample: DeploymentSample,
    arm: str = "A2",
    tau: float | None = None,
    estimate_result: EstimateResult | None = None,
    lambda_o: float = 1.0,
    *,
    lambda_h: float = 1.0,
    out_dir: str | Path | None = None,
) -> PipelineResult:
    if not isinstance(sample, DeploymentSample):
        raise TypeError("The pipeline only accepts an allowlisted DeploymentSample")
    spec = get_arm(arm)
    if spec.reference_only:
        raise ValueError("ORACLE_REL is an archived reference, not a deployment arm")
    if arm == "B0":
        return PipelineResult(sample.context_str_full, [], None, [], no_op=True,
                              decision_note="baseline_replay")
    if arm == "B1":
        return PipelineResult(
            sample.context_str_full + "\n\n" + B1_STATIC_INSTRUCTION,
            [], None, [], annotations=[B1_STATIC_INSTRUCTION],
            decision_note="single_static_instruction",
        )

    records = adapt(sample.raw_memories, sample.system_kind)
    if not records:
        return PipelineResult(sample.context_str_full, records, estimate_result, [],
                              no_op=True, bypass=True, decision_note="no_strict_evidence")
    result = estimate_result
    if result is None:
        from a2_stage1_estimator import estimate
        result = estimate(sample.question, records)
    # Failed estimation must stay a no-op even when tau is -inf.
    if result.failed:
        return PipelineResult(sample.context_str_full, records, result, [], no_op=True,
                              decision_note="estimation_failed_noop")
    if spec.gate_enabled:
        threshold = _threshold(sample, tau, out_dir)
        if result.risk <= threshold:
            return PipelineResult(sample.context_str_full, records, result, [], no_op=True,
                                  decision_note="risk_gate_noop")
    if arm == "B2":
        decisions = b2_decisions(records, result)
    else:
        from a2_stage2_decision import decide
        decisions = decide(sample.question, records, result,
                           lambda_h=lambda_h, lambda_o=lambda_o)
    decisions = apply_ablation(decisions, arm)
    if not decisions or all(decision.action == Action.BLOCK for decision in decisions):
        return PipelineResult(sample.context_str_full, records, result, decisions,
                              no_op=True, bypass=True, decision_note="no_strict_evidence")
    context, annotations = render_detailed(
        records, decisions, sample.user_name, sample.pref_note, result.sufficiency,
        salience_enabled=spec.salience_enabled,
        license_enabled=spec.license_enabled,
    )
    return PipelineResult(context, records, result, decisions, annotations=annotations)


def run_pipeline(sample: DeploymentSample) -> str:
    """Deploy with the already-saved calibration; never invent a working point."""
    return run_pipeline_detailed(sample).context
