"""Stage 2: the specified expected-cost decision plus mutually exclusive sets."""
from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from a2_schema import Action, DecisionRecord, EstimateResult, EvidenceRecord, MemoryEstimate, Relation, RELATIONS

# Exact task-book pairs (hallucination cost, omission cost), in RELATIONS order.
# VOUCH is high risk on obsolete, misbound and insufficient content; BLOCK on
# SUPPORT/CURRENT incurs catastrophic omission. REFUTE is safe only on a real
# refutation. KEEP makes inaction an explicit option rather than a hidden rule.
COST_MATRIX = {
    Action.VOUCH: [(0.00, 0.00), (0.20, 0.50), (0.75, 0.00), (0.05, 0.02), (0.70, 0.05), (0.80, 0.02)],
    Action.KEEP: [(0.00, 0.00), (0.05, 0.50), (0.50, 0.05), (0.05, 0.05), (0.40, 0.10), (0.45, 0.05)],
    Action.DEMOTE: [(0.10, 0.25), (0.10, 0.45), (0.30, 0.10), (0.10, 0.15), (0.25, 0.15), (0.30, 0.10)],
    Action.QUALIFY: [(0.05, 0.15), (0.10, 0.35), (0.20, 0.10), (0.05, 0.10), (0.15, 0.25), (0.10, 0.10)],
    Action.REFUTE: [(0.25, 0.10), (0.05, 0.05), (0.15, 0.15), (0.15, 0.15), (0.25, 0.20), (0.20, 0.15)],
    Action.BLOCK: [(0.00, 0.95), (0.10, 0.90), (0.05, 0.05), (0.02, 0.85), (0.05, 0.15), (0.05, 0.05)],
}
TIE_BREAK = (Action.VOUCH, Action.KEEP, Action.QUALIFY, Action.DEMOTE, Action.BLOCK, Action.REFUTE)
STOP_WORDS = frozenset("about after before being could does from have into just more most other over same some than that their them then there these they this those very what when where which while with would".split())


def relation_argmax(posterior: dict[str, float]) -> Relation:
    return Relation(max(RELATIONS, key=lambda name: posterior.get(name, 0.0)))


def expected_costs(posterior: dict[str, float], lambda_h: float = 1.0,
                   lambda_o: float = 1.0) -> dict[Action, float]:
    if not all(math.isfinite(x) and x >= 0 for x in (lambda_h, lambda_o)):
        raise ValueError("Cost weights must be finite and nonnegative")
    return {action: sum(posterior.get(name, 0.0) * (lambda_h * h + lambda_o * o)
                        for name, (h, o) in zip(RELATIONS, entries))
            for action, entries in COST_MATRIX.items()}


def choose_action(posterior: dict[str, float], lambda_h: float = 1.0,
                  lambda_o: float = 1.0) -> Action:
    costs = expected_costs(posterior, lambda_h, lambda_o)
    minimum = min(costs.values())
    return next(action for action in TIE_BREAK if costs[action] - minimum <= 1e-9)


def normalized(text: str) -> str:
    return "".join(text.lower().split())


def topic_tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z]+", text)
            if len(token) >= 4 and token.lower() not in STOP_WORDS}


def group_key(question: str, record: EvidenceRecord) -> str:
    if record.entity_anchors and normalized(record.entity_anchors[0]):
        return normalized(record.entity_anchors[0])
    # Normally the adapter already includes the field as its first anchor.
    match = re.search(r"(?:^| \| )memory_key: (.*?)(?: \| |$)", record.text)
    if match and normalized(match.group(1)):
        return normalized(match.group(1))
    shared = topic_tokens(question) & topic_tokens(record.text)
    return max(shared, key=lambda token: (len(token), token)) if shared else "none"


def grouped(question: str, records: list[EvidenceRecord]) -> dict[str, list[EvidenceRecord]]:
    groups: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        key = group_key(question, record)
        if key != "none":
            groups[key].append(record)
    return dict(groups)


def comparable_time(record: EvidenceRecord) -> float | None:
    value = (record.time_uncertainty[1] if record.time_uncertainty else record.event_time)
    value = value or record.ingest_time
    if not value:
        return None
    try:
        time = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if time.tzinfo is None:
            time = time.replace(tzinfo=timezone.utc)
        return time.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def note(decision: DecisionRecord, value: str) -> None:
    parts = decision.decision_note.split(";") if decision.decision_note else []
    if value not in parts:
        parts.append(value)
    decision.decision_note = ";".join(parts)


def refresh_use(decision: DecisionRecord) -> None:
    decision.use = ("REFUTATIONAL" if decision.action == Action.REFUTE else
                    "QUALIFY" if decision.action == Action.QUALIFY else "ASSERT")


def decide(question: str, records: list[EvidenceRecord], estimate: EstimateResult,
           lambda_h: float = 1.0, lambda_o: float = 1.0) -> list[DecisionRecord]:
    """A single decision stage, never a question-category router."""
    output: list[DecisionRecord] = []
    for record in records:
        item: MemoryEstimate = estimate.memories[record.id]
        relation = relation_argmax(item.relation_posterior)
        has_condition = (item.condition_present and bool(item.condition_text) and
                         item.condition_text in record.text)
        decision = DecisionRecord(
            id=record.id,
            action=choose_action(item.relation_posterior, lambda_h, lambda_o),
            relation_argmax=relation,
            scope="CONDITIONAL" if has_condition else "UNCONDITIONAL",
            temporal=("CURRENT" if relation == Relation.CURRENT else
                      "HISTORICAL" if relation == Relation.SUPERSEDED else "UNKNOWN"),
        )
        if item.condition_present and not has_condition:
            note(decision, "condition_text_not_in_record")
        output.append(decision)
    by_id = {decision.id: decision for decision in output}
    for members in grouped(question, records).values():
        if len(members) < 2:
            continue
        relations = {by_id[record.id].relation_argmax for record in members}
        conflict = (any(estimate.memories[r.id].relation_posterior.get(Relation.SUPERSEDED.value, 0) > 0.4
                        for r in members) or
                    {Relation.CURRENT, Relation.SUPERSEDED}.issubset(relations))
        if not conflict:
            continue
        times = {r.id: comparable_time(r) for r in members}
        available = {key: value for key, value in times.items() if value is not None}
        winners: list[str] = []
        if available:
            latest = max(available.values())
            winners = [key for key, value in available.items() if value == latest]
        if len(winners) == 1:
            winner = winners[0]
            uses_proxy = any(r.time_is_proxy and times[r.id] is not None for r in members)
            for r in members:
                decision = by_id[r.id]
                decision.action = Action.VOUCH if r.id == winner else Action.DEMOTE
                decision.temporal = "CURRENT" if r.id == winner else "HISTORICAL"
                note(decision, "exclusive_set_temporal")
                if uses_proxy:
                    note(decision, "temporal_from_ingest_proxy")
        else:
            for r in members:
                decision = by_id[r.id]
                decision.action = Action.QUALIFY
                decision.temporal = "UNKNOWN"
                note(decision, "exclusive_set_no_unique_time")
        assert sum(by_id[r.id].action == Action.VOUCH for r in members) <= 1
        if not available:
            assert all(by_id[r.id].action != Action.VOUCH for r in members)
    for decision in output:
        item = estimate.memories[decision.id]
        if (decision.scope == "CONDITIONAL" and item.condition_satisfied in {"FALSE", "UNKNOWN"}
                and decision.relation_argmax not in {Relation.REFUTE, Relation.SUPERSEDED}):
            if decision.action in {Action.VOUCH, Action.KEEP}:
                decision.action = Action.QUALIFY
                note(decision, "conditional_rule_not_as_event")
        refresh_use(decision)
    return output


def probe_groups(samples: list[dict[str, Any]]) -> dict[str, Any]:
    from a2_stage0_adapter import adapt, capability_summary
    raw_count = key_count = 0
    all_records: list[EvidenceRecord] = []
    distribution: Counter[int] = Counter()
    for sample in samples:
        items = sample["raw_memories"]
        raw_count += len(items)
        key_count += sum(bool(str(item.get("memory_key") or "").strip())
                         for item in items if isinstance(item, dict))
        records = adapt(items, sample.get("system_kind", "memos"))
        all_records.extend(records)
        distribution.update(len(group) for group in grouped(sample["question"], records).values())
    return {
        "n_cases": len(samples), "n_raw": raw_count,
        "memory_key_rate": key_count / max(1, raw_count),
        "entity_anchors_rate": sum(bool(r.entity_anchors) for r in all_records) / max(1, len(all_records)),
        "multi_record_group_count": sum(count for size, count in distribution.items() if size >= 2),
        "group_size_distribution": dict(sorted(distribution.items())),
        "adapter": capability_summary(all_records),
    }


def main() -> None:
    from e1_memos_oracle_common import ROOT, read_jsonl, write_json
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-groups", action="store_true", required=True)
    parser.add_argument("--pool", default="memos")
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    out = ROOT / "outputs" / "a2_mvp_v1"
    path = args.source or out / "pools" / f"{args.pool}_pool.jsonl"
    print("Budget: 0 LLM calls (offline grouping probe)")
    rows = read_jsonl(path)
    if not rows:
        raise SystemExit(f"No pool at {path}")
    statistics = probe_groups(rows)
    statistics["source"] = str(path)
    write_json(out / "analysis" / f"{args.pool}_group_probe.json", statistics)
    config = read_json_config(out / "run_config.json")
    config["group_probe"] = {"pool": args.pool, "source": str(path), "estimated_calls": 0}
    write_json(out / "run_config.json", config)
    import json
    print(json.dumps(statistics, ensure_ascii=False))


def read_json_config(path: Path) -> dict[str, Any]:
    import json
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


if __name__ == "__main__":
    main()
