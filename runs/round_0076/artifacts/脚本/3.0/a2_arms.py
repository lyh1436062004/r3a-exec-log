"""Task-book experiment arms; no task-type routing or extra actions."""
from __future__ import annotations

from dataclasses import dataclass, replace

from a2_schema import Action, DecisionRecord, EstimateResult, EvidenceRecord, Relation


B1_STATIC_INSTRUCTION = """请严格按以下规则使用上面的记忆:
1. 先逐条核对每条记忆的时间。若同一事项存在新旧不同说法,以时间最新的一条为准。
2. 核对记忆中的实体与问题所问的人/物是否一致;若记忆讲的是别人别的事,
   不要用它回答。
3. 若记忆中某条与问题中的某个前提直接矛盾,请直接指出该前提有误,
   不要回答"不知道"。
4. 若某条记忆只在特定条件下成立,回答时必须显式说明该条件,
   不得直接当作已经发生的事实。
5. 若记忆只是话题相关但不包含所问事实,不要推断,
   明确说明缺少什么信息。
作答前先逐条评估,再给出最终答案。"""


@dataclass(frozen=True)
class ArmSpec:
    name: str
    gate_enabled: bool = True
    salience_enabled: bool = True
    license_enabled: bool = True
    block_enabled: bool = True
    reference_only: bool = False


ARMS = {
    "B0": ArmSpec("B0", gate_enabled=False),
    "B1": ArmSpec("B1", gate_enabled=False),
    "B2": ArmSpec("B2", gate_enabled=False),
    "A2": ArmSpec("A2"),
    "A2-nogate": ArmSpec("A2-nogate", gate_enabled=False),
    "A2-nosal": ArmSpec("A2-nosal", salience_enabled=False),
    "A2-nolic": ArmSpec("A2-nolic", license_enabled=False),
    "A2-noblock": ArmSpec("A2-noblock", block_enabled=False),
    "ORACLE_REL": ArmSpec("ORACLE_REL", reference_only=True),
}
MAIN_ARMS = tuple(name for name, spec in ARMS.items() if not spec.reference_only)
REFERENCE_ARMS = tuple(name for name, spec in ARMS.items() if spec.reference_only)
B2_RELATION_ACTION = {
    Relation.SUPPORT: Action.VOUCH,
    Relation.CURRENT: Action.VOUCH,
    Relation.REFUTE: Action.REFUTE,
    Relation.SUPERSEDED: Action.BLOCK,
    Relation.MISBIND: Action.BLOCK,
    Relation.INSUFFICIENT: Action.BLOCK,
}


def get_arm(name: str) -> ArmSpec:
    try:
        return ARMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown arm: {name}") from exc


def b2_decisions(records: list[EvidenceRecord], estimate: EstimateResult) -> list[DecisionRecord]:
    """Argmax only: no posterior costs, group correction, or scope downgrade."""
    decisions: list[DecisionRecord] = []
    for record in records:
        posterior = estimate.memories[record.id].relation_posterior
        relation = max(Relation, key=lambda item: posterior[item.value])
        action = B2_RELATION_ACTION[relation]
        decisions.append(DecisionRecord(
            id=record.id, action=action, relation_argmax=relation,
            temporal=("CURRENT" if relation == Relation.CURRENT else
                      "HISTORICAL" if relation == Relation.SUPERSEDED else "UNKNOWN"),
            use="REFUTATIONAL" if action == Action.REFUTE else "ASSERT",
            decision_note="b2_argmax_fixed_mapping",
        ))
    return decisions


def apply_ablation(decisions: list[DecisionRecord], arm: str) -> list[DecisionRecord]:
    """Change only the declared factor and preserve the unmodified decisions."""
    spec = get_arm(arm)
    result: list[DecisionRecord] = []
    for decision in decisions:
        action = decision.action
        use = decision.use
        note = decision.decision_note
        if not spec.block_enabled and action == Action.BLOCK:
            action, use = Action.DEMOTE, "ASSERT"
            note = ";".join(text for text in (note, "ablation_block_to_demote") if text)
        if not spec.license_enabled:
            use = "ASSERT"
        result.append(replace(decision, action=action, use=use, decision_note=note))
    return result
