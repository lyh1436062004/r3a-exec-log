"""Stage 3: fixed annotation templates and frozen-record rendering."""
from __future__ import annotations

from a2_schema import Action, DecisionRecord, EvidenceRecord


LICENSE_TEMPLATES = {
    "VOUCH": "[关键证据] 该记忆包含回答当前问题所需的关键信息，请优先依据它作答。",
    "REFUTATIONAL": "[证据说明] 该记忆与问题中的某个前提直接矛盾。你被允许且应当依据该记忆指出前提错误，而不是回答“不知道”。",
    "QUALIFY": "[使用范围] 该记忆仅在其所述条件成立时适用。若问题所述情形无法确认满足该条件，不要把它当作已经发生的事实，必须在回答中说明该条件。",
    "DEMOTE_PREFIX": "[次要信息] ",
}

INSUFFICIENT_NOTE = (
    "[证据不足] 现有记忆不足以支持对所问事实作出确定断言。"
    "请明确说明缺少什么信息，不要依据常识或推测作答。"
)


def all_injection_templates() -> tuple[str, ...]:
    """The outer experiment runner checks this complete fixed-template set."""
    return (*LICENSE_TEMPLATES.values(), INSUFFICIENT_NOTE)


def authorization_text(decision: DecisionRecord) -> str:
    """Salience prefixes are not permission to assert or refute."""
    if decision.use == "ASSERT":
        text = ""
    elif decision.use in ("QUALIFY", "REFUTATIONAL"):
        text = LICENSE_TEMPLATES[decision.use]
    else:
        raise ValueError(f"Unknown use for {decision.id}: {decision.use}")
    assert (decision.use == "ASSERT") == (text == ""), "use/template lock violated"
    return text


def salience_prefix(decision: DecisionRecord) -> str:
    if decision.action == Action.VOUCH:
        return LICENSE_TEMPLATES["VOUCH"]
    if decision.action == Action.DEMOTE:
        return LICENSE_TEMPLATES["DEMOTE_PREFIX"]
    return ""


def _salience_rank(action: Action) -> int:
    if action in (Action.VOUCH, Action.REFUTE):
        return 0
    if action in (Action.KEEP, Action.QUALIFY):
        return 1
    if action == Action.DEMOTE:
        return 2
    raise ValueError(f"Cannot render action: {action}")


def render_detailed(
    records: list[EvidenceRecord],
    decisions: list[DecisionRecord],
    user_name: str,
    pref_note: str = "",
    sufficiency: float = 1.0,
    *,
    salience_enabled: bool = True,
    license_enabled: bool = True,
) -> tuple[str, list[str]]:
    """Return context and the exact injected strings for boundary checks.

    No-op and all-BLOCK bypass belong to the orchestrator; this function never
    synthesizes a baseline context or emits an empty memory context.
    """
    record_map = {record.id: record for record in records}
    decision_map = {decision.id: decision for decision in decisions}
    if len(record_map) != len(records) or len(decision_map) != len(decisions):
        raise ValueError("Record and decision ids must be unique")
    if set(record_map) != set(decision_map):
        raise ValueError("Decision ids must equal the adapted frozen collection")
    for decision in decisions:
        if decision.action not in tuple(Action):
            raise ValueError(f"Unknown action for {decision.id}: {decision.action}")
        authorization_text(decision)
        if not license_enabled and decision.use != "ASSERT":
            raise AssertionError("License ablation must set every use to ASSERT")

    admitted = [record for record in records
                if decision_map[record.id].action != Action.BLOCK]
    if not admitted:
        raise ValueError("Empty rendering is forbidden; use the baseline bypass")
    admitted.sort(key=lambda record: (
        _salience_rank(decision_map[record.id].action) if salience_enabled else 0,
        record.raw_index,
    ))

    lines: list[str] = []
    annotations: list[str] = []
    for record in admitted:
        decision = decision_map[record.id]
        if not record.text.strip():
            raise ValueError(f"Empty adapted record: {record.id}")
        salience = salience_prefix(decision) if salience_enabled else ""
        authorization = authorization_text(decision)
        prefixes = [text for text in (salience, authorization) if text]
        annotations.extend(prefixes)
        time = record.event_time[:10] if record.event_time else "?"
        anchor = record.entity_anchors[0] if record.entity_anchors else "-"
        prefix = " ".join(prefixes)
        lines.append(f"[{record.id} | {time} | {anchor}] {prefix}\n{record.text}")

    if (license_enabled and sufficiency < 0.35
            and not any(decision.action == Action.VOUCH for decision in decisions)):
        lines.append(INSUFFICIENT_NOTE)
        annotations.append(INSUFFICIENT_NOTE)
    if pref_note:
        lines.append(pref_note)
    assert all(text in all_injection_templates() for text in annotations)
    context = f"Memories for user {user_name}:\n\n    " + "\n".join(lines)
    return context, annotations


def render(
    records: list[EvidenceRecord],
    decisions: list[DecisionRecord],
    user_name: str,
    pref_note: str = "",
    sufficiency: float = 1.0,
    *,
    salience_enabled: bool = True,
    license_enabled: bool = True,
) -> str:
    return render_detailed(
        records, decisions, user_name, pref_note, sufficiency,
        salience_enabled=salience_enabled, license_enabled=license_enabled,
    )[0]
