from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
HALUMEM_EVAL = ROOT / "github" / "HaluMem" / "eval"
ENV_PATH = HALUMEM_EVAL / ".env"
OUT_DIR = ROOT / "outputs" / "e1_memos_full_oracle_v2"

MEDIUM_QA = ROOT / "outputs" / "baseline_full" / "memos_medium" / "memos_medium_qa.jsonl"
LONG_QA = ROOT / "outputs" / "baseline_full" / "memos_long" / "memos_long_qa.jsonl"
SEMANTIC_DETAIL = (
    ROOT
    / "outputs"
    / "baseline_wrong_gold_semantic_audit"
    / "semantic_gold_evidence_detail.jsonl"
)

MODEL = "deepseek-chat"
TEMPERATURE = 0
GEN_MAX_TOKENS = 128
JUDGE_MAX_TOKENS = 256
TIMEOUT = 300
RETRIES = 3
SEED = 20260709
CONDITIONS = ["A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"]

EXPECTED_COUNTS = {
    "memos_medium": 989,
    "memos_long": 998,
    "total": 1987,
    "strict_supported": 896,
    "partial_or_supported": 1129,
}

LICENSE_TEMPLATES = {
    "REFUTE": '[证据说明] 该记忆与问题中的某个前提直接矛盾。你被允许且应当依据该记忆指出前提错误，而不是回答"不知道"。',
    "SELECT": "[证据说明] 该记忆是关于此事项的最新有效状态，若与其他记忆冲突，以本条为准。",
    "CONDITION": "[证据说明] 该记忆仅在其所述条件下成立，回答时必须显式说明该条件。",
    # VOUCH 属于 salience 轴（就地指认/背书），不是言语行为授权；仅 A5 臂使用。
    # 放在同一字典里是为了复用固定模板泄漏检查（check_license_leakage）。
    "VOUCH": "[证据说明] 该记忆包含回答当前问题所需的关键信息，请优先依据该记忆作答。",
    "UNIFIED": "[使用授权] 该记忆可以用于回答当前问题。",
}

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
CONDITION_CUE_RE = re.compile(
    r"\b(if|only when|under|unless|as long as|depends on|provided that|in case of)\b",
    re.IGNORECASE,
)

sys.path.insert(0, str(HALUMEM_EVAL))
from prompts import PROMPT_MEMOS  # type: ignore  # noqa: E402


def load_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    if not os.getenv("OPENAI_API_KEY") and os.getenv("DEEPSEEK_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["DEEPSEEK_API_KEY"]
    os.environ.setdefault("OPENAI_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))


def make_client() -> OpenAI:
    load_env()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any], lock: Lock | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    if lock:
        with lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def evidence_texts(record: dict[str, Any]) -> list[str]:
    value = record.get("evidence")
    if value is None:
        value = record.get("gold_evidence")
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def memory_text(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return str(item).strip()

    for key in ("memory", "memory_value", "content", "text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    preference = item.get("preference")
    reasoning = item.get("reasoning")
    if isinstance(preference, str) and preference.strip():
        if isinstance(reasoning, str) and reasoning.strip():
            return f"Preference: {preference.strip()}\nReasoning: {reasoning.strip()}"
        return f"Preference: {preference.strip()}"
    if isinstance(reasoning, str) and reasoning.strip():
        # Some MemOS preference objects carry an empty preference but retain the
        # extraction rationale. Preserve that textual payload without exposing metadata.
        return f"Reasoning: {reasoning.strip()}"

    value = item.get("memory_key")
    if isinstance(value, str) and value.strip():
        return value.strip()

    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        return memory_text(metadata)
    return ""


def baseline_memory_text(item: Any) -> str:
    """逐字节复刻 run_baseline_full.py::memory_text。

    与本文件的 memory_text 的关键差异（正是 A0 复现失真的根源）：
    1. 无 preference/reasoning 分支 —— 纯偏好记忆返回 ""，被 baseline 丢弃；
    2. 键序为 (memory, memory_value, memory_key, content, text)，memory_key 在 content 之前；
    3. 返回原始 value，不做 strip。
    任何对本函数的修改都必须重跑 00_verify_serializer.py 并保持 1987/1987 逐字节通过。
    """
    if isinstance(item, str):
        return item
    if not isinstance(item, dict):
        return ""
    for key in ("memory", "memory_value", "memory_key", "content", "text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        return baseline_memory_text(metadata)
    return ""


def serialize_baseline_context(user_name: str, lines: list[str]) -> str:
    """逐字节复刻 run_baseline_full.py::MemOSBackend.search 的 context 拼接。"""
    return f"Memories for user {user_name}:\n\n    " + "\n".join(lines)


def raw_id_to_index(memory_id: str) -> int | None:
    if not isinstance(memory_id, str) or not memory_id.startswith("m"):
        return None
    suffix = memory_id[1:]
    if not suffix.isdigit():
        return None
    index = int(suffix) - 1
    return index if index >= 0 else None


def ids_for_raw(raw_memories: list[Any]) -> list[str]:
    return [f"m{idx}" for idx in range(1, len(raw_memories) + 1)]


def unique_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def label_to_license(question_type: str, sample: dict[str, Any], memory: dict[str, Any]) -> str:
    text = f"{sample.get('question', '')}\n{memory_text(memory)}"
    if CONDITION_CUE_RE.search(text):
        return "CONDITION"
    if question_type == "Memory Conflict":
        return "REFUTE"
    if question_type == "Dynamic Update":
        return "SELECT"
    return "ASSERT"


def license_text(license_name: str) -> str:
    return LICENSE_TEMPLATES.get(license_name, "")


def token_list(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def has_long_evidence_ngram(label: str, evidence: str, n: int = 8) -> bool:
    label_tokens = token_list(label)
    evidence_tokens = token_list(evidence)
    if len(evidence_tokens) < n or len(label_tokens) < n:
        return False
    label_ngrams = {tuple(label_tokens[i : i + n]) for i in range(0, len(label_tokens) - n + 1)}
    return any(tuple(evidence_tokens[i : i + n]) in label_ngrams for i in range(0, len(evidence_tokens) - n + 1))


def check_license_leakage(sample: dict[str, Any], annotations: list[str]) -> list[str]:
    errors: list[str] = []
    fixed = set(LICENSE_TEMPLATES.values())
    gold_answer = str(sample.get("gold_answer") or "").strip()
    norm_gold = "".join(gold_answer.lower().split())
    for label in annotations:
        if label not in fixed:
            errors.append("license_text_not_fixed_template")
        if gold_answer and gold_answer in label:
            errors.append("gold_answer_exact_in_license")
        if norm_gold and norm_gold in "".join(label.lower().split()):
            errors.append("gold_answer_normalized_in_license")
        for evidence in sample.get("gold_evidence") or []:
            if has_long_evidence_ngram(label, str(evidence)):
                errors.append("gold_evidence_8gram_in_license")
    return sorted(set(errors))


def extract_note_block(context: str) -> str:
    marker = "\n# Note:"
    if marker not in context:
        return ""
    return context[context.index(marker) :].strip()


def build_memory_sequence(sample: dict[str, Any], condition: str) -> list[tuple[str, Any, str]]:
    """干预臂的记忆宇宙 = baseline 实际序列化进 context_str_full 的可见记忆。

    依赖 00_verify_serializer.py 产出的 visibility 字段(由 load_samples 合并进 sample):
    visible_memory_ids / gold_visible_ids。A0 不走本函数(逐字节重放)。
    """
    raw_memories = list(sample.get("raw_memories") or [])
    visible_ids = sample.get("visible_memory_ids")
    if visible_ids is None:
        raise RuntimeError(
            f"sample {sample.get('case_id')} missing visibility fields; "
            "run 00_verify_serializer.py first"
        )
    if not sample.get("serializer_ok"):
        raise RuntimeError(f"sample {sample.get('case_id')} failed serializer verification")
    visible_set = set(visible_ids)
    all_ids = ids_for_raw(raw_memories)
    if condition in {"A6", "A7"}:
        gold_ids = [mid for mid in sample.get("gold_memory_ids") or [] if mid in set(all_ids)]
    else:
        gold_ids = [mid for mid in sample.get("gold_visible_ids") or [] if mid in visible_set]

    if condition == "A1":
        order = unique_ordered(gold_ids + [mid for mid in visible_ids if mid not in gold_ids])
    elif condition == "A2":
        order = gold_ids
    elif condition == "A3":
        order = gold_ids
    elif condition == "A4":
        order = list(visible_ids)
    elif condition == "A5":
        order = list(visible_ids)
    elif condition in {"A6", "A7"}:
        # Unified admission arms intentionally operate on the complete retriever payload.
        order = all_ids
    else:
        raise ValueError(f"Unknown condition: {condition}")

    rows: list[tuple[str, Any, str]] = []
    for memory_id in order:
        index = raw_id_to_index(memory_id)
        if index is None or index >= len(raw_memories):
            continue
        memory = raw_memories[index]
        license_name = "ASSERT"
        if condition in {"A3", "A4", "A5"} and memory_id in gold_ids:
            license_name = label_to_license(str(sample.get("question_type") or ""), sample, memory)
            # A5 = A4 + 就地背书：普通事实型 gold（ASSERT，即无授权文本）升级为 VOUCH，
            # 使全部 gold 记忆都携带显式标注；A5-A4 差值即“纯指认”对普通事实的效应。
            if condition == "A5" and license_name == "ASSERT":
                license_name = "VOUCH"
        elif condition == "A7" and memory_id in gold_ids:
            # One constant authorization for every oracle-supported raw memory.
            license_name = "UNIFIED"
        rows.append((memory_id, memory, license_name))
    return rows


def build_context(sample: dict[str, Any], condition: str) -> tuple[str, dict[str, Any]]:
    # A0 = 逐字节重放 baseline 真正看到的上下文，禁止任何重拼。
    if condition == "A0":
        context = str(sample.get("context_str_full") or "")
        if not context:
            raise RuntimeError(f"sample {sample.get('case_id')} has empty context_str_full")
        meta = {
            "n_context_memories": len(sample.get("visible_memory_ids") or []),
            "license_counts": {},
            "context_hash": sha256_text(context),
            "leakage_errors": [],
            "verbatim_replay": True,
        }
        return context, meta

    rows = build_memory_sequence(sample, condition)
    annotations: list[str] = []
    license_counter: Counter[str] = Counter()
    lines: list[str] = []

    admitted_memory_ids: list[str] = []
    gold_raw_ids = set(sample.get("gold_memory_ids") or [])
    for memory_id, memory, license_name in rows:
        # 干预臂的文本抽取必须与 baseline 序列化完全一致(baseline_memory_text)，
        # 否则臂间对比会混入"重拼差异"这个混杂变量。
        text = memory_text(memory) if condition in {"A6", "A7"} else baseline_memory_text(memory)
        if not text:
            continue
        admitted_memory_ids.append(memory_id)
        license_counter[license_name] += 1
        label = license_text(license_name)
        # 防 silent no-op：license 名与是否注入文本锁死。
        # ASSERT 是唯一合法的无文本类型；其余类型必须有模板,否则立即报错,
        # 避免再出现"内部记成已处理、实际未注入任何文字"的静默缺口。
        assert (license_name == "ASSERT") == (label == ""), (
            f"license/text mismatch: {license_name!r} -> {label!r}"
        )
        if label:
            annotations.append(label)
            lines.append(f"{label}\n{text}")
        else:
            lines.append(text)

    leakage = check_license_leakage(sample, annotations)
    if leakage:
        return "", {"leakage_errors": leakage, "license_counts": dict(license_counter)}

    # pref_note 是 baseline 序列化时追加在记忆块末尾的一行(由 00_verify 从
    # context_str_full 精确恢复)。过滤臂(A2/A3)按 oracle 语义剔除；其余保留。
    note = str(sample.get("pref_note") or "")
    if note and condition in {"A1", "A4", "A5", "A6", "A7"}:
        lines.append(note)

    user_name = sample.get("user_name") or sample.get("uuid") or "unknown_user"
    context = serialize_baseline_context(str(user_name), lines)

    meta = {
        "n_context_memories": len(admitted_memory_ids),
        "n_raw_memories": len(sample.get("raw_memories") or []),
        "n_admitted_memories": len(admitted_memory_ids),
        "n_dropped_memories": len(sample.get("raw_memories") or []) - len(admitted_memory_ids),
        "admitted_memory_ids": admitted_memory_ids,
        "gold_admitted_ids": [mid for mid in admitted_memory_ids if mid in gold_raw_ids],
        "license_counts": dict(license_counter),
        "context_hash": sha256_text(context),
        "leakage_errors": [],
        "verbatim_replay": False,
    }
    return context, meta


def build_answer_prompt(context: str, question: str) -> str:
    return PROMPT_MEMOS.format(context=context, question=question)


def build_gold_only_judge_prompt(record: dict[str, str]) -> str:
    return f"""
You are judging a memory QA answer.

Use the gold answer as the reference. Classify the model answer into exactly one label:
- correct: semantically matches the gold answer.
- omission: says unknown/insufficient/no answer when the gold answer is known, or fails to answer the asked fact.
- hallucination: gives a concrete answer that contradicts or is unsupported by the gold answer.

Return only JSON with keys: label, rationale.

Question:
{record["question"]}

Gold answer:
{record["gold_answer"]}

Model answer:
{record["model_answer"]}
""".strip()


def parse_json_object(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    return json.loads(text)


def retry_call(label: str, fn, retries: int = RETRIES, sleep_base: float = 2.0) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                time.sleep(min(sleep_base * attempt, 30.0))
    raise RuntimeError(f"{label} failed after {retries} retries: {last_error}")


def call_chat(client: OpenAI, prompt: str) -> tuple[str, dict[str, Any]]:
    started = time.time()

    def _call() -> Any:
        return client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_tokens=GEN_MAX_TOKENS,
            timeout=TIMEOUT,
        )

    response = retry_call("generation", _call)
    usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
    return response.choices[0].message.content or "", {
        "latency_ms": round((time.time() - started) * 1000, 2),
        "usage": usage,
    }


def call_judge(client: OpenAI, question: str, gold_answer: str, model_answer: str) -> tuple[dict[str, str], dict[str, Any]]:
    prompt = build_gold_only_judge_prompt(
        {"question": question, "gold_answer": gold_answer, "model_answer": model_answer}
    )
    started = time.time()

    def _call(max_tokens: int) -> Any:
        return client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
            timeout=TIMEOUT,
        )

    response = retry_call("judge", lambda: _call(JUDGE_MAX_TOKENS))
    used_max_tokens = JUDGE_MAX_TOKENS
    try:
        parsed = parse_json_object(response.choices[0].message.content or "{}")
    except json.JSONDecodeError:
        # A small number of otherwise valid verdicts exhaust the rationale budget
        # and return truncated JSON. Retry only those cases with a larger cap.
        used_max_tokens = JUDGE_MAX_TOKENS * 2
        response = retry_call("judge-json-repair", lambda: _call(used_max_tokens))
        parsed = parse_json_object(response.choices[0].message.content or "{}")
    label = str(parsed.get("label", "")).strip().lower()
    if label == "incorrect":
        empty_markers = ("unknown", "not enough", "insufficient", "cannot answer", "not provided", "no answer")
        answer_l = str(model_answer or "").strip().lower()
        label = "omission" if not answer_l or any(marker in answer_l for marker in empty_markers) else "hallucination"
    if label not in {"correct", "hallucination", "omission"}:
        raise ValueError(f"Bad judge label: {label}")
    usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
    return {"label": label, "rationale": str(parsed.get("rationale", ""))}, {
        "latency_ms": round((time.time() - started) * 1000, 2),
        "usage": usage,
        "judge_prompt_hash": sha256_text(prompt),
        "judge_max_tokens": used_max_tokens,
    }


def load_samples() -> list[dict[str, Any]]:
    samples = read_jsonl(OUT_DIR / "samples_memos_full.jsonl")
    vis_path = OUT_DIR / "visibility.jsonl"
    if vis_path.exists():
        vis = {str(row["case_id"]): row for row in read_jsonl(vis_path)}
        for sample in samples:
            v = vis.get(str(sample.get("case_id")))
            if v:
                sample["visible_memory_ids"] = v.get("visible_memory_ids") or []
                sample["gold_visible_ids"] = v.get("gold_visible_ids") or []
                sample["partial_visible_ids"] = v.get("partial_visible_ids") or []
                sample["pref_note"] = v.get("pref_note") or ""
                sample["visible_stratum"] = v.get("visible_stratum") or ""
                sample["serializer_ok"] = bool(v.get("serializer_ok"))
    return samples


def sample_by_case(samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in samples}


def completed_by_cache(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("ok") and row.get("cache_key"):
            rows[str(row["cache_key"])] = row
    return rows


def completed_by_case_condition(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("ok"):
            rows[(str(row.get("case_id")), str(row.get("condition")))] = row
    return rows


def deterministic_sample(rows: list[Any], n: int, seed: int = SEED) -> list[Any]:
    rng = random.Random(seed)
    rows = list(rows)
    rng.shuffle(rows)
    return rows[: min(n, len(rows))]


def prompt_hashes() -> dict[str, str]:
    return {
        "answer_prompt_hash": sha256_text(PROMPT_MEMOS),
        "judge_prompt_template_hash": sha256_text(
            build_gold_only_judge_prompt({"question": "{question}", "gold_answer": "{gold_answer}", "model_answer": "{model_answer}"})
        ),
        "license_templates_hash": sha256_text(json.dumps(LICENSE_TEMPLATES, ensure_ascii=False, sort_keys=True)),
    }
