from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "am",
    "did", "do", "does", "has", "have", "had", "can", "could", "will", "would", "should",
    "what", "when", "where", "why", "how", "which", "whether", "who", "whom",
    "user", "his", "her", "hers", "him", "he", "she", "they", "them", "their", "its",
    "this", "that", "these", "those", "with", "from", "into", "onto", "for", "and",
    "or", "but", "because", "about", "after", "before", "during", "on", "in", "at",
    "by", "to", "of", "as", "than", "then", "also", "only", "just", "very", "really",
    "question", "answer", "memory", "mention", "mentioned", "express", "expressed",
    "due", "low", "high",
}

GENERIC_TOKENS = {
    "martin", "mark", "johnson", "joseph", "user", "thing", "things", "activity", "activities",
    "interest", "interested", "preference", "preferences", "status", "state", "states",
}

TOPIC_TERMS = {
    "health", "mental", "physical", "work", "job", "career", "role", "director", "consulting",
    "huaxin", "retire", "retired", "retirement", "sport", "sports", "boxing", "wrestling",
    "golf", "snake", "snakes", "reptile", "pet", "pets", "cat", "cats", "dog", "dogs",
    "music", "rap", "jazz", "ambient", "rock", "movie", "movies", "documentaries", "films",
    "game", "games", "gaming", "travel", "tour", "tours", "clothing", "wear", "tea",
    "hotel", "hospitality", "guests", "income", "salary", "partner", "family", "relationship",
    "study", "learning", "seminar", "festival", "current", "currently", "still",
}

NEGATION_OR_CONTRAST_PATTERNS = [
    "not", "no", "never", "without", "stopped", "quit", "left", "changed", "switched",
    "instead", "rather than", "dislikes", "disliked", "dislike", "avoids", "avoided",
    "avoid", "opposes", "opposed", "no longer", "different", "transitioned", "retired",
    "unemployed", "employed", "declined", "did not", "does not", "do not", "cannot",
    "can't", "gave up", "abandoned", "cancelled", "canceled", "lost interest",
]

TEMPORAL_PATTERNS = [
    "after", "before", "current", "currently", "now", "still", "as of",
    "changed", "switched", "transitioned", "no longer", "later", "recently", "remained",
    "continue", "continued", "begin", "began", "started", "stopped",
]

PREF_POS = [
    "like", "likes", "liked", "love", "loves", "enjoy", "enjoys", "prefer", "prefers",
    "preferred", "interest", "interested", "appreciation", "favorite", "favourite",
]
PREF_NEG = [
    "dislike", "dislikes", "disliked", "hate", "hates", "avoid", "avoids", "avoided",
    "disinterest", "uninterested", "skeptical", "skepticism", "negative", "opposes",
]

EVENT_VERBS = [
    "establish", "established", "launch", "launched", "begin", "began", "started", "start",
    "retire", "retired", "employed", "unemployed", "work", "worked", "host", "hosted",
    "increase", "increased", "decrease", "decreased", "decide", "decided", "choose", "chose",
]
PLAN_OR_NOT_DONE = [
    "aims to", "plans to", "intends to", "hopes to", "wants to", "considered", "considering",
    "goal is", "primary life goal", "not yet", "has not", "did not", "does not", "decided not",
    "chose not", "instead", "rather than", "transitioned to", "switched to",
]


def load_selector(selector_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("r3a_v2_selector", selector_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load selector from {selector_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def raw_memory_text(raw: Any) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("memory", "memory_content", "text", "content", "value"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return str(raw)


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall((text or "").lower()):
        if len(token) < 3 or token in STOPWORDS:
            continue
        out.append(stem(token))
    return out


def stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def named_tokens(text: str) -> set[str]:
    names: set[str] = set()
    for name in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text or ""):
        for token in tokens(name):
            names.add(token)
    return names


def contains_any(text: str, patterns: list[str]) -> list[str]:
    lower = (text or "").lower()
    found = []
    for pattern in patterns:
        escaped = re.escape(pattern.lower()).replace(r"\ ", r"\s+")
        if re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", lower):
            found.append(pattern)
    return found


def preference_polarity(text: str) -> str | None:
    lower = (text or "").lower()
    pos = any(re.search(rf"\b{re.escape(p)}\b", lower) for p in PREF_POS)
    neg = any(re.search(rf"\b{re.escape(p)}\b", lower) for p in PREF_NEG)
    if pos and neg:
        return "mixed"
    if pos:
        return "positive"
    if neg:
        return "negative"
    return None


def score_candidate(question: str, memory_text: str) -> dict[str, Any]:
    q_tokens = set(tokens(question))
    m_tokens = set(tokens(memory_text))
    q_core = q_tokens - STOPWORDS - GENERIC_TOKENS
    m_core = m_tokens - STOPWORDS - GENERIC_TOKENS
    shared_core = (q_core & m_core) | ((q_tokens & TOPIC_TERMS) & (m_tokens & TOPIC_TERMS))
    shared_names = named_tokens(question) & (named_tokens(memory_text) | {"user"})

    topic_overlap_score = min(6, len(shared_core))
    if shared_names:
        topic_overlap_score = min(8, topic_overlap_score + 2)

    neg_hits = contains_any(memory_text, NEGATION_OR_CONTRAST_PATTERNS)
    negation_or_contrast_score = min(5, len(set(neg_hits)))
    if "rather than" in neg_hits or "instead" in neg_hits or "no longer" in neg_hits:
        negation_or_contrast_score = min(5, negation_or_contrast_score + 1)

    q_temporal = bool(contains_any(question, TEMPORAL_PATTERNS) or DATE_RE.search(question))
    m_temporal = bool(contains_any(memory_text, TEMPORAL_PATTERNS) or DATE_RE.search(memory_text))
    temporal_conflict_score = 0
    if q_temporal and m_temporal:
        temporal_conflict_score = 2
    if q_temporal and contains_any(memory_text, ["changed", "switched", "transitioned", "no longer", "later", "currently", "now"]):
        temporal_conflict_score = max(temporal_conflict_score, 3)
    if DATE_RE.search(question) and DATE_RE.search(memory_text):
        temporal_conflict_score = max(temporal_conflict_score, 2)

    q_pref = preference_polarity(question)
    m_pref = preference_polarity(memory_text)
    preference_reversal_score = 0
    if topic_overlap_score > 0 and q_pref and m_pref:
        if {q_pref, m_pref} == {"positive", "negative"}:
            preference_reversal_score = 5
        elif "mixed" in {q_pref, m_pref}:
            preference_reversal_score = 2
    if " over " in question.lower() and (" over " in memory_text.lower() or any(p in memory_text.lower() for p in PREF_NEG + PREF_POS)):
        preference_reversal_score = max(preference_reversal_score, 2)

    q_event = contains_any(question, EVENT_VERBS)
    m_plan = contains_any(memory_text, PLAN_OR_NOT_DONE)
    event_denial_score = 0
    has_specific_overlap = len(shared_core) >= 2 or (len(shared_core) >= 1 and bool(shared_names))
    if q_event and m_plan and has_specific_overlap:
        event_denial_score = 4
    if q_event and contains_any(memory_text, ["transitioned to", "switched to", "instead", "rather than"]) and has_specific_overlap:
        event_denial_score = max(event_denial_score, 3)

    non_topic_signal = (
        negation_or_contrast_score
        + temporal_conflict_score
        + preference_reversal_score
        + event_denial_score
    )
    total = topic_overlap_score + non_topic_signal
    reasons: list[str] = []
    if shared_core:
        reasons.append("shared topic/object tokens: " + ", ".join(sorted(list(shared_core))[:8]))
    if shared_names:
        reasons.append("shared entity/name anchor")
    if neg_hits:
        reasons.append("negation/contrast cues: " + ", ".join(sorted(set(neg_hits))[:8]))
    if temporal_conflict_score:
        reasons.append("temporal/update cues overlap with question timing")
    if preference_reversal_score >= 4:
        reasons.append("possible preference polarity reversal")
    elif preference_reversal_score:
        reasons.append("weak preference contrast")
    if event_denial_score:
        reasons.append("possible event completion vs plan/alternative contrast")

    needs_manual = topic_overlap_score >= 1 and total >= 4 and non_topic_signal >= 2
    return {
        "topic_overlap_score": topic_overlap_score,
        "negation_or_contrast_score": negation_or_contrast_score,
        "temporal_conflict_score": temporal_conflict_score,
        "preference_reversal_score": preference_reversal_score,
        "event_denial_score": event_denial_score,
        "total_suspicion_score": total,
        "suspected_reason": "; ".join(reasons) if reasons else "",
        "needs_manual_audit": needs_manual,
        "non_topic_signal_score": non_topic_signal,
    }


def simplify_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in evidence or []:
        out.append(
            {
                "rank": ev.get("rank"),
                "memory_id": ev.get("memory_id"),
                "memory_ref": ev.get("memory_ref"),
                "memory_text": ev.get("memory_text"),
                "confidence": ev.get("confidence"),
                "relation": ev.get("relation"),
                "rationale": ev.get("rationale"),
            }
        )
    return out


def rejected_reason_map(result: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for rejected in result.get("rejected") or []:
        rank = rejected.get("rank")
        if isinstance(rank, int):
            out[rank] = rejected.get("reject_reason") or ""
    return out


def make_priority_group(sample: dict[str, Any], has_suspected: bool) -> str | None:
    qt = sample.get("question_type")
    label = sample.get("baseline_label")
    triggered = bool(sample.get("r3a_triggered"))
    if qt == "Memory Conflict" and not triggered and has_suspected:
        if label == "omission":
            return "P1_memory_conflict_omission_untriggered_suspected"
        if label == "hallucination":
            return "P2_memory_conflict_hallucination_untriggered_suspected"
        if label == "correct":
            return "P3_memory_conflict_correct_untriggered_suspected"
        return "P3_memory_conflict_other_untriggered_suspected"
    if qt == "Memory Conflict" and triggered:
        return "P4_memory_conflict_r3a_triggered"
    if qt != "Memory Conflict" and has_suspected:
        return "P5_non_memory_conflict_high_suspicion"
    return None


def priority_rank(group: str) -> int:
    if group.startswith("P1"):
        return 1
    if group.startswith("P2"):
        return 2
    if group.startswith("P3"):
        return 3
    if group.startswith("P4"):
        return 4
    if group.startswith("P5"):
        return 5
    return 99


def baseline_rank(label: str | None) -> int:
    return {"omission": 0, "hallucination": 1, "correct": 2}.get(str(label), 3)


def pct(n: int, d: int) -> float:
    return n / d if d else 0.0


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--selector", default=None)
    parser.add_argument("--max-suspects-per-sample", type=int, default=5)
    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    selector_path = Path(args.selector) if args.selector else Path(__file__).with_name("r3a_v2_selector.py")
    selector = load_selector(selector_path)

    qa_rows = load_jsonl(input_path)
    sample_level_path = outdir / "full_sample_level_census.jsonl"
    sample_rows: list[dict[str, Any]] = []
    memory_conflict_rows: list[dict[str, Any]] = []
    triggered_rows: list[dict[str, Any]] = []
    untriggered_suspected_rows: list[dict[str, Any]] = []
    all_candidate_rows: list[dict[str, Any]] = []

    for idx, qa in enumerate(qa_rows):
        question = qa.get("question") or ""
        raw_memories = qa.get("raw_memories") or []
        result = selector.select_counterevidence_v2(question, raw_memories)
        r3a_triggered = bool(result.get("triggered"))
        selected_evidence = simplify_evidence(result.get("evidence") or [])
        reason_by_rank = rejected_reason_map(result)
        selected_ranks = {ev.get("rank") for ev in selected_evidence if ev.get("rank") is not None}

        candidates: list[dict[str, Any]] = []
        for rank, raw in enumerate(raw_memories, start=1):
            memory_text = raw_memory_text(raw)
            scores = score_candidate(question, memory_text)
            is_selected = rank in selected_ranks
            if is_selected:
                scores["needs_manual_audit"] = True
                scores["suspected_reason"] = (scores["suspected_reason"] + "; " if scores["suspected_reason"] else "") + "selected_by_r3a"
            if scores["needs_manual_audit"]:
                candidates.append(
                    {
                        "memory_index": rank,
                        "memory_text": memory_text,
                        "topic_overlap_score": scores["topic_overlap_score"],
                        "negation_or_contrast_score": scores["negation_or_contrast_score"],
                        "temporal_conflict_score": scores["temporal_conflict_score"],
                        "preference_reversal_score": scores["preference_reversal_score"],
                        "event_denial_score": scores["event_denial_score"],
                        "total_suspicion_score": scores["total_suspicion_score"],
                        "suspected_reason": scores["suspected_reason"],
                        "r3a_rejected_reason_if_available": reason_by_rank.get(rank, ""),
                        "needs_manual_audit": True,
                        "selected_by_r3a": is_selected,
                    }
                )
        candidates.sort(
            key=lambda c: (
                bool(c.get("selected_by_r3a")),
                c["total_suspicion_score"],
                c["preference_reversal_score"],
                c["event_denial_score"],
                c["temporal_conflict_score"],
            ),
            reverse=True,
        )
        top_suspects = candidates[: args.max_suspects_per_sample]

        posthoc_group = {
            "is_memory_conflict": qa.get("question_type") == "Memory Conflict",
            "is_r0_omission": qa.get("baseline_label") == "omission",
            "is_r0_hallucination": qa.get("baseline_label") == "hallucination",
            "is_r0_correct": qa.get("baseline_label") == "correct",
        }
        sample = {
            "idx": idx,
            "qa_key": qa.get("qa_key") or f"idx:{idx}",
            "question": question,
            "question_type": qa.get("question_type"),
            "baseline_label": qa.get("baseline_label"),
            "raw_memory_count": len(raw_memories),
            "r3a_triggered": r3a_triggered,
            "r3a_selected_evidence_count": len(selected_evidence),
            "r3a_selected_evidence": selected_evidence,
            "r3a_relation": selected_evidence[0].get("relation") if selected_evidence else None,
            "suspected_counterevidence_count": len(candidates),
            "top_suspected_candidates": top_suspects,
            "has_suspected_counterevidence": bool(candidates),
            "posthoc_group": posthoc_group,
            "census_notes": (
                "Suspicious candidates are high-recall audit leads only; they are not true counterevidence labels."
            ),
        }
        sample_rows.append(sample)

        if r3a_triggered:
            triggered_rows.append(
                {
                    "idx": idx,
                    "qa_key": sample["qa_key"],
                    "question": question,
                    "question_type": qa.get("question_type"),
                    "baseline_label": qa.get("baseline_label"),
                    "selected_evidence_count": len(selected_evidence),
                    "selected_evidence_preview": " || ".join((ev.get("memory_text") or "")[:240] for ev in selected_evidence),
                }
            )
        if qa.get("question_type") == "Memory Conflict":
            memory_conflict_rows.append(
                {
                    "idx": idx,
                    "qa_key": sample["qa_key"],
                    "question": question,
                    "baseline_label": qa.get("baseline_label"),
                    "r3a_triggered": r3a_triggered,
                    "raw_memory_count": len(raw_memories),
                    "suspected_counterevidence_count": len(candidates),
                    "has_suspected_counterevidence": bool(candidates),
                    "top_suspicion_score": top_suspects[0]["total_suspicion_score"] if top_suspects else 0,
                    "top_suspected_reason": top_suspects[0]["suspected_reason"] if top_suspects else "",
                }
            )
        if (not r3a_triggered) and candidates:
            untriggered_suspected_rows.append(
                {
                    "idx": idx,
                    "qa_key": sample["qa_key"],
                    "question": question,
                    "question_type": qa.get("question_type"),
                    "baseline_label": qa.get("baseline_label"),
                    "raw_memory_count": len(raw_memories),
                    "suspected_counterevidence_count": len(candidates),
                    "top_suspicion_score": top_suspects[0]["total_suspicion_score"] if top_suspects else 0,
                    "top_suspected_reason": top_suspects[0]["suspected_reason"] if top_suspects else "",
                }
            )

        priority = make_priority_group(sample, bool(candidates))
        candidate_source = top_suspects[:3]
        if priority:
            for cand in candidate_source:
                all_candidate_rows.append(
                    {
                        "idx": idx,
                        "qa_key": sample["qa_key"],
                        "question": question,
                        "question_type": qa.get("question_type"),
                        "baseline_label": qa.get("baseline_label"),
                        "r3a_triggered": r3a_triggered,
                        "memory_index": cand["memory_index"],
                        "memory_text": cand["memory_text"],
                        "topic_overlap_score": cand["topic_overlap_score"],
                        "negation_or_contrast_score": cand["negation_or_contrast_score"],
                        "temporal_conflict_score": cand["temporal_conflict_score"],
                        "preference_reversal_score": cand["preference_reversal_score"],
                        "event_denial_score": cand["event_denial_score"],
                        "total_suspicion_score": cand["total_suspicion_score"],
                        "suspected_reason": cand["suspected_reason"],
                        "r3a_rejected_reason_if_available": cand["r3a_rejected_reason_if_available"],
                        "priority_group": priority,
                        "manual_has_retrieved_counterevidence": "",
                        "manual_counterevidence_label": "",
                        "manual_should_r3a_trigger": "",
                        "manual_failure_source": "",
                        "manual_notes": "",
                    }
                )

    with sample_level_path.open("w", encoding="utf-8") as f:
        for sample in sample_rows:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    manual_caps = {
        "P1_memory_conflict_omission_untriggered_suspected": 120,
        "P2_memory_conflict_hallucination_untriggered_suspected": 80,
        "P3_memory_conflict_correct_untriggered_suspected": 50,
        "P3_memory_conflict_other_untriggered_suspected": 50,
        "P4_memory_conflict_r3a_triggered": 80,
        "P5_non_memory_conflict_high_suspicion": 50,
    }
    all_candidate_rows.sort(
        key=lambda r: (
            priority_rank(r["priority_group"]),
            -int(r["total_suspicion_score"]),
            baseline_rank(r.get("baseline_label")),
            int(r["idx"]),
            int(r["memory_index"]),
        )
    )
    selected_manual_rows: list[dict[str, Any]] = []
    cap_counts: Counter[str] = Counter()
    for row in all_candidate_rows:
        group = row["priority_group"]
        if cap_counts[group] >= manual_caps.get(group, 0):
            continue
        selected_manual_rows.append(row)
        cap_counts[group] += 1

    sample_fields = [
        "idx", "qa_key", "question", "baseline_label", "r3a_triggered", "raw_memory_count",
        "suspected_counterevidence_count", "has_suspected_counterevidence", "top_suspicion_score",
        "top_suspected_reason",
    ]
    write_csv(
        outdir / "memory_conflict_candidate_samples.csv",
        memory_conflict_rows,
        ["idx", "qa_key", "question", "baseline_label", "r3a_triggered", "raw_memory_count",
         "suspected_counterevidence_count", "has_suspected_counterevidence", "top_suspicion_score",
         "top_suspected_reason"],
    )
    write_csv(
        outdir / "r3a_triggered_samples.csv",
        triggered_rows,
        ["idx", "qa_key", "question", "question_type", "baseline_label", "selected_evidence_count",
         "selected_evidence_preview"],
    )
    write_csv(
        outdir / "r3a_untriggered_suspected_counterevidence.csv",
        untriggered_suspected_rows,
        ["idx", "qa_key", "question", "question_type", "baseline_label", "raw_memory_count",
         "suspected_counterevidence_count", "top_suspicion_score", "top_suspected_reason"],
    )
    manual_fields = [
        "idx", "qa_key", "question", "question_type", "baseline_label", "r3a_triggered",
        "memory_index", "memory_text", "topic_overlap_score", "negation_or_contrast_score",
        "temporal_conflict_score", "preference_reversal_score", "event_denial_score",
        "total_suspicion_score", "suspected_reason", "r3a_rejected_reason_if_available",
        "priority_group", "manual_has_retrieved_counterevidence", "manual_counterevidence_label",
        "manual_should_r3a_trigger", "manual_failure_source", "manual_notes",
    ]
    write_csv(outdir / "manual_audit_candidates.csv", selected_manual_rows, manual_fields)

    total = len(sample_rows)
    question_type_counts = Counter(s["question_type"] for s in sample_rows)
    question_type_rates = {k: pct(v, total) for k, v in question_type_counts.items()}
    triggered_count = sum(1 for s in sample_rows if s["r3a_triggered"])
    mc_samples = [s for s in sample_rows if s["question_type"] == "Memory Conflict"]
    mc_count = len(mc_samples)
    mc_triggered = [s for s in mc_samples if s["r3a_triggered"]]
    mc_untriggered = [s for s in mc_samples if not s["r3a_triggered"]]
    mc_untriggered_suspected = [s for s in mc_untriggered if s["has_suspected_counterevidence"]]
    mc_suspected = [s for s in mc_samples if s["has_suspected_counterevidence"]]
    mc_r0_omission_suspected = [
        s for s in mc_samples
        if s["baseline_label"] == "omission" and (not s["r3a_triggered"]) and s["has_suspected_counterevidence"]
    ]
    mc_r0_hallu_suspected = [
        s for s in mc_samples
        if s["baseline_label"] == "hallucination" and (not s["r3a_triggered"]) and s["has_suspected_counterevidence"]
    ]
    mc_r0_correct_suspected = [
        s for s in mc_samples
        if s["baseline_label"] == "correct" and (not s["r3a_triggered"]) and s["has_suspected_counterevidence"]
    ]
    triggered_label_dist = Counter(s["baseline_label"] for s in sample_rows if s["r3a_triggered"])
    untriggered_suspected_label_dist = Counter(
        s["baseline_label"] for s in sample_rows if (not s["r3a_triggered"]) and s["has_suspected_counterevidence"]
    )
    mc_suspected_dist = Counter(str(s["suspected_counterevidence_count"]) for s in mc_samples)
    signal_sums = Counter()
    for row in selected_manual_rows:
        signal_sums["topic_overlap_score"] += int(row["topic_overlap_score"])
        signal_sums["negation_or_contrast_score"] += int(row["negation_or_contrast_score"])
        signal_sums["temporal_conflict_score"] += int(row["temporal_conflict_score"])
        signal_sums["preference_reversal_score"] += int(row["preference_reversal_score"])
        signal_sums["event_denial_score"] += int(row["event_denial_score"])

    if len(mc_r0_omission_suspected) > 20:
        recommendation = "audit_first_priority_candidates_before_any_selector_change"
    elif mc_count and len(mc_suspected) / mc_count < 0.10:
        recommendation = "few_suspects_consider_opportunity_enhancement_or_cross_system_replication"
    elif signal_sums["temporal_conflict_score"] > max(signal_sums["preference_reversal_score"], signal_sums["event_denial_score"]):
        recommendation = "many_suspects_are_temporal_update_like_consider_r3b_not_r3a"
    else:
        recommendation = "audit_manual_candidates_and_estimate_false_positive_rate"

    summary = {
        "round": "0014",
        "task": "r3a_v2_2_full_offline_opportunity_census",
        "input_round": "round_0013",
        "input_file": str(input_path),
        "selector_file": str(selector_path),
        "total_samples": total,
        "question_type_counts": dict(question_type_counts),
        "question_type_rates": question_type_rates,
        "r3a_triggered_count": triggered_count,
        "r3a_trigger_rate": pct(triggered_count, total),
        "memory_conflict_count": mc_count,
        "memory_conflict_rate": pct(mc_count, total),
        "mc_r3a_triggered_count": len(mc_triggered),
        "mc_r3a_trigger_rate": pct(len(mc_triggered), mc_count),
        "mc_untriggered_count": len(mc_untriggered),
        "mc_with_suspected_counterevidence_count": len(mc_suspected),
        "mc_untriggered_with_suspected_counterevidence_count": len(mc_untriggered_suspected),
        "mc_r0_omission_with_suspected_counterevidence_count": len(mc_r0_omission_suspected),
        "mc_r0_hallucination_with_suspected_counterevidence_count": len(mc_r0_hallu_suspected),
        "mc_r0_correct_with_suspected_counterevidence_count": len(mc_r0_correct_suspected),
        "r3a_triggered_baseline_label_distribution": dict(triggered_label_dist),
        "r3a_untriggered_suspected_baseline_label_distribution": dict(untriggered_suspected_label_dist),
        "memory_conflict_suspected_candidate_count_distribution": dict(mc_suspected_dist),
        "manual_audit_candidate_rows": len(selected_manual_rows),
        "manual_audit_unique_samples": len({r["idx"] for r in selected_manual_rows}),
        "manual_audit_priority_group_counts": dict(Counter(r["priority_group"] for r in selected_manual_rows)),
        "top_priority_candidate_rows": cap_counts.get("P1_memory_conflict_omission_untriggered_suspected", 0),
        "api_calls": 0,
        "changed_selector_logic": False,
        "changed_prompt": False,
        "changed_retriever": False,
        "changed_memory_store": False,
        "decision": "prepare_manual_audit_candidates",
        "recommended_next_decision": recommendation,
        "caveat": "Suspicious candidates are not true counterevidence and are not R3a should-trigger labels.",
    }
    (outdir / "full_opportunity_census_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = build_report(summary, selected_manual_rows, signal_sums, outdir)
    (outdir / "full_opportunity_census_report.md").write_text(report, encoding="utf-8")
    return 0


def build_report(
    summary: dict[str, Any],
    manual_rows: list[dict[str, Any]],
    signal_sums: Counter[str],
    outdir: Path,
) -> str:
    qt_lines = [
        f"- {qt}: {count} ({summary['question_type_rates'][qt]:.2%})"
        for qt, count in sorted(summary["question_type_counts"].items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    priority_lines = [
        f"- {group}: {count}"
        for group, count in sorted(summary["manual_audit_priority_group_counts"].items(), key=lambda kv: kv[0])
    ]
    recommendation = summary["recommended_next_decision"]
    return f"""# R3a-v2.2 全量离线反证机会普查报告

## 1. 本轮目的
本轮接续 round_0013，对 Mem0 Medium 全量样本做离线反证机会普查。目标是生成后续人工审计候选表，而不是证明 R3a 有效，也不是修改 R3a。

## 2. 输入文件
- 全量 QA: `{summary['input_file']}`
- R3a-v2.2 selector: `{summary['selector_file']}`
- round_0013 人工审计整合输出: `outputs/r3a_v2_2_mc_human_audit_integration/`

## 3. 方法说明
- 离线读取全量 QA 和已检索 `raw_memories`。
- 使用当前 `select_counterevidence_v2` 记录 R3a 正式触发结果。
- 额外实现高召回可疑候选发现器，只用于人工审计候选生成。
- `question_type` 和 `baseline_label` 仅用于事后分组统计和审计优先级，不进入 R3a 正式判断。
- 未发 API，未重新生成回答，未修改 selector、prompt、retriever 或 memory store。

## 4. 全量题型分布
总样本数: {summary['total_samples']}

{chr(10).join(qt_lines)}

## 5. R3a 全量触发情况
- R3a 全量触发数: {summary['r3a_triggered_count']}
- R3a 全量触发率: {summary['r3a_trigger_rate']:.2%}
- R3a 触发样本 baseline_label 分布: `{summary['r3a_triggered_baseline_label_distribution']}`

## 6. Memory Conflict 子集触发情况
- Memory Conflict 总数: {summary['memory_conflict_count']}
- Memory Conflict 占比: {summary['memory_conflict_rate']:.2%}
- Memory Conflict 中 R3a 触发数: {summary['mc_r3a_triggered_count']}
- Memory Conflict 中 R3a 触发率: {summary['mc_r3a_trigger_rate']:.2%}
- Memory Conflict 中未触发数: {summary['mc_untriggered_count']}

## 7. 可疑反证候选发现结果
- Memory Conflict 中存在可疑反证候选的样本数: {summary['mc_with_suspected_counterevidence_count']}
- Memory Conflict 中未触发且存在可疑反证候选的样本数: {summary['mc_untriggered_with_suspected_counterevidence_count']}
- R3a 未触发但有可疑反证候选的样本 baseline_label 分布: `{summary['r3a_untriggered_suspected_baseline_label_distribution']}`
- Memory Conflict 中可疑反证候选数量分布: `{summary['memory_conflict_suspected_candidate_count_distribution']}`

重要说明：可疑反证候选不等于真反证；可疑反证候选不等于 R3a 应该触发；可疑反证候选只用于后续人工审计。

## 8. R0 omission / hallucination 中的可疑修复机会
- Memory Conflict + R0 omission + R3a 未触发 + 可疑反证候选样本数: {summary['mc_r0_omission_with_suspected_counterevidence_count']}
- Memory Conflict + R0 hallucination + R3a 未触发 + 可疑反证候选样本数: {summary['mc_r0_hallucination_with_suspected_counterevidence_count']}
- Memory Conflict + R0 correct + R3a 未触发 + 可疑反证候选样本数: {summary['mc_r0_correct_with_suspected_counterevidence_count']}

## 9. R3a 已触发样本清单摘要
已输出 `r3a_triggered_samples.csv`。这些是当前 R3a-v2.2 正式触发样本，不由高召回发现器决定。

## 10. R3a 未触发但有可疑反证候选的样本摘要
已输出 `r3a_untriggered_suspected_counterevidence.csv`。这些样本只表示“值得人工审计”，不能直接视为漏触发。

## 11. 与 round_0013 人工审计结论的一致性检查
round_0013 的人工审计结论是不修改 R3a。本轮普查不是要推翻该结论，而是扩大范围检查全量 Mem0 Medium 中是否存在未发现的漏触发真反证。如果本轮只发现可疑候选，不能直接说明 R3a 漏判，必须经人工审计后才能判断。

## 12. 人工审计候选表说明
人工审计候选表输出为 `manual_audit_candidates.csv`，共 {summary['manual_audit_candidate_rows']} 行，覆盖 {summary['manual_audit_unique_samples']} 个唯一样本。

优先级分布:

{chr(10).join(priority_lines)}

## 13. 当前不能得出的结论
- 不能说 R3a-v2.2 要修改。
- 不能说 R3a-v2.2 已成功。
- 不能把可疑候选直接当成真反证。
- 不能把可疑候选直接当成 R3a 应该触发。
- 不能把时间更新类候选强行塞给 R3a；其中一部分可能属于 R3b。

## 14. 下一步建议
推荐下一步: `{recommendation}`。

若第一优先级候选较多，应先人工审计 `manual_audit_candidates.csv` 的第一优先级，不要直接改 R3a。人工审计应估计高召回候选发现器的误报率，并判断可疑样本中是否存在真正的“已检索反证但 R3a 未触发”。

## 15. 生成文件列表
- `full_opportunity_census_report.md`
- `full_opportunity_census_summary.json`
- `full_sample_level_census.jsonl`
- `memory_conflict_candidate_samples.csv`
- `manual_audit_candidates.csv`
- `r3a_triggered_samples.csv`
- `r3a_untriggered_suspected_counterevidence.csv`
"""


if __name__ == "__main__":
    raise SystemExit(main())
