"""Label-free records for the task-book's four-stage A2 pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Relation(str, Enum):
    SUPPORT = "SUPPORT"
    REFUTE = "REFUTE"
    SUPERSEDED = "SUPERSEDED"
    CURRENT = "CURRENT"
    MISBIND = "MISBIND"
    INSUFFICIENT = "INSUFFICIENT"


class Action(str, Enum):
    VOUCH = "VOUCH"
    KEEP = "KEEP"
    DEMOTE = "DEMOTE"
    QUALIFY = "QUALIFY"
    REFUTE = "REFUTE"
    BLOCK = "BLOCK"


RELATIONS = tuple(r.value for r in Relation)
ACTIONS = tuple(a.value for a in Action)


@dataclass
class CapabilityMask:
    text: bool = False
    event_time: bool = False
    ingest_time: bool = False
    entity_anchors: bool = False
    source_session: bool = False
    retrieval_score: bool = False
    confidence: bool = False


@dataclass
class EvidenceRecord:
    id: str
    text: str
    event_time: str | None = None
    ingest_time: str | None = None
    time_source: str = "none"
    time_is_proxy: bool = False
    time_uncertainty: tuple[str, str] | None = None
    entity_anchors: list[str] = field(default_factory=list)
    source_session: str | None = None
    raw_index: int = 0
    retrieval_score: float | None = None
    confidence: float | None = None
    memory_type: str | None = None
    tags: list[str] = field(default_factory=list)
    mask: CapabilityMask = field(default_factory=CapabilityMask)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryEstimate:
    id: str
    relation_posterior: dict[str, float]
    condition_present: bool = False
    condition_text: str = ""
    condition_satisfied: str = "UNKNOWN"
    entity_match: str = "UNCLEAR"


@dataclass
class EstimateResult:
    premise_conflict: bool
    sufficiency: float
    risk: float
    memories: dict[str, MemoryEstimate]
    failed: bool = False
    validation_warnings: list[str] = field(default_factory=list)
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EstimateResult":
        data = dict(value)
        data["memories"] = {
            key: MemoryEstimate(**item) for key, item in data["memories"].items()
        }
        return cls(**data)


@dataclass
class DecisionRecord:
    id: str
    action: Action
    relation_argmax: Relation
    scope: str = "UNCONDITIONAL"
    temporal: str = "UNKNOWN"
    use: str = "ASSERT"
    decision_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeploymentSample:
    """The runner constructs this allowlisted view before entering the pipeline."""
    question: str
    raw_memories: list[Any]
    system_kind: str
    user_name: str
    context_str_full: str
    pref_note: str = ""


@dataclass
class PipelineResult:
    context: str
    records: list[EvidenceRecord]
    estimate: EstimateResult | None
    decisions: list[DecisionRecord]
    annotations: list[str] = field(default_factory=list)
    no_op: bool = False
    bypass: bool = False
    decision_note: str = ""


def safe_estimate(records: list[EvidenceRecord], failed: bool = True) -> EstimateResult:
    return EstimateResult(
        premise_conflict=False, sufficiency=0.0, risk=0.0, failed=failed,
        memories={r.id: MemoryEstimate(r.id, {k: float(k == Relation.INSUFFICIENT.value)
                                           for k in RELATIONS}) for r in records},
    )
