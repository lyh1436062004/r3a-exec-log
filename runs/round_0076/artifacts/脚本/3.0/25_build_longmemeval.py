"""LongMemEval cleaned S: one deterministic TF-IDF retrieval, then frozen.

Only this new dataset is allowed to run a retriever. Session/turn answer labels
are copied exclusively to the external analysis records, never raw_memories.
Acquisition failures are recorded. Amendment 01 allows at most three strategies
(including the historical first attempt); exhaustion directs the runner to E.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from e1_memos_oracle_common import ROOT, SEED, read_jsonl, sha256_text, write_json

OUT_DIR = ROOT / "outputs" / "a2_mvp_v1"
DATASET = "xiaowu0162/longmemeval-cleaned"
FILENAME = "longmemeval_s_cleaned.json"
TOP_K = 20
RETRIEVER_VERSION = "python-tfidf-cosine-session-v2-neutral-source-ids"
TOKEN_RE = re.compile(r"[a-z0-9]+")


def stable_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def merge_config(payload: dict[str, Any], out_dir: Path) -> None:
    path = out_dir / "run_config.json"
    config = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    config.setdefault("seed", SEED)
    config["longmemeval"] = payload
    write_json(path, config)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def tfidf_cosine_topk(question: str, documents: list[str], top_k: int = TOP_K) -> list[tuple[int, float]]:
    """Fit per question history, smoothed IDF + raw term frequency + L2 norm.

    Tie breaking is original session order; zero-score sessions still fill k.
    There is no use of gold sessions, task types, or answer-bearing turn flags.
    """
    counts = [Counter(tokenize(text)) for text in documents]
    document_frequency: Counter[str] = Counter()
    for count in counts:
        document_frequency.update(count.keys())
    n = len(counts)
    idf = {term: math.log((1 + n) / (1 + frequency)) + 1
           for term, frequency in document_frequency.items()}
    query = {term: value * idf[term] for term, value in Counter(tokenize(question)).items() if term in idf}
    query_norm = math.sqrt(sum(value * value for value in query.values()))
    scores = []
    for i, count in enumerate(counts):
        norm = math.sqrt(sum((value * idf[term]) ** 2 for term, value in count.items()))
        dot = sum(query.get(term, 0.0) * value * idf[term] for term, value in count.items())
        score = dot / (query_norm * norm) if query_norm and norm else 0.0
        scores.append((i, score))
    return sorted(scores, key=lambda row: (-row[1], row[0]))[:top_k]


def observable_date(value: Any) -> str:
    text = str(value or "").strip()
    for fmt in ("%Y/%m/%d (%a) %H:%M", "%Y/%m/%d (%A) %H:%M", "%Y/%m/%d %H:%M",
                "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        # Preserve the source string rather than inventing an event time.
        return text


def session_text(session: list[dict[str, Any]]) -> str:
    # Whitelist roles/content. has_answer and all other annotation fields are
    # physically unavailable to TF-IDF and to the deployment adapter.
    return "\n".join(f"{str(turn.get('role') or 'unknown')}: {str(turn.get('content') or '')}"
                     for turn in session)


def acquire_cleaned_s(out_dir: Path, *, endpoint: str = "https://huggingface.co",
                      approved_retry: bool = False, datasets_transport: bool = False) -> dict[str, Any]:
    cache_dir = out_dir / "datasets" / "longmemeval_cleaned_s"
    lock_path = cache_dir / "source_lock.json"
    source_path = cache_dir / FILENAME
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if source_path.exists() and file_hash(source_path) == lock.get("sha256"):
            return {**lock, "path": str(source_path)}
        raise RuntimeError("Locked cleaned S source is absent or hash changed; refusing silent redownload")
    failure_path = out_dir / "longmemeval_blocker.json"
    if failure_path.exists() and not approved_retry:
        raise RuntimeError("Prior single LongMemEval attempt failed; stage E required, no repeated network retry")
    # Metadata is small; only the S JSON is fetched, never snapshot_download.
    metadata = requests.get(f"{endpoint}/api/datasets/{DATASET}", timeout=(15, 30))
    metadata.raise_for_status()
    info = metadata.json()
    revision = str(info.get("sha") or "")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("HF did not provide an immutable 40-character revision")
    names = [s["rfilename"] for s in info.get("siblings", [])]
    selected = next((name for name in names if name == FILENAME), None)
    if selected is None:
        selected = next((name for name in names if name.endswith("/" + FILENAME)), None)
    if selected is None:
        raise ValueError(f"cleaned S filename not found; available={names}")
    url = f"{endpoint}/datasets/{DATASET}/resolve/{revision}/{selected}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = cache_dir / (FILENAME + ".partial")
    if datasets_transport:
        from datasets import DownloadConfig, DownloadManager
        manager = DownloadManager(download_config=DownloadConfig(
            cache_dir=str(cache_dir / "transfer"), max_retries=0, token=False,
            disable_tqdm=True, use_etag=False))
        downloaded = manager.download(url)
        shutil.copyfile(downloaded, temporary)
    else:
        response = requests.get(url, timeout=(30, 60), stream=True)
        response.raise_for_status()
        with temporary.open("wb") as stream:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    stream.write(chunk)
    # Validate before promoting. This is the named cleaned S file, not a repo.
    rows = json.loads(temporary.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("cleaned S is not a nonempty JSON sample array")
    temporary.replace(source_path)
    lock = {"dataset": DATASET, "revision": revision, "filename": selected,
            "sha256": file_hash(source_path), "bytes": source_path.stat().st_size, "download_url": url,
            "sample_count": len(rows), "variant": "cleaned S"}
    write_json(lock_path, lock)
    return {**lock, "path": str(source_path)}


def acquire_from_official_git(out_dir: Path) -> dict[str, Any]:
    """Sparse checkout the named S file from the official dataset Git repo."""
    cache_dir = out_dir / "datasets" / "longmemeval_cleaned_s"
    clone_dir = cache_dir / "source_repo_amendment01"
    if clone_dir.exists():
        raise RuntimeError("Prior Git attempt directory exists; refusing an unbudgeted retry/overwrite")
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_LFS_SKIP_SMUDGE": "1"}

    def run(arguments: list[str], cwd: Path | None = None) -> str:
        result = subprocess.run(["git", *arguments], cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=60, check=False)
        if result.returncode:
            raise RuntimeError(f"Official dataset git {arguments[0]} exited {result.returncode}")
        return result.stdout.strip()

    repo_url = f"https://huggingface.co/datasets/{DATASET}"
    run(["clone", "--depth", "1", "--filter=blob:none", "--no-checkout", repo_url, str(clone_dir)])
    revision = run(["rev-parse", "HEAD"], clone_dir)
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Git source revision is not immutable")
    names = run(["ls-tree", "-r", "--name-only", "HEAD"], clone_dir).splitlines()
    selected = next((name for name in names if name == FILENAME or name.endswith("/" + FILENAME)), None)
    if selected is None:
        raise ValueError("Official dataset Git repository has no named cleaned S file")
    run(["sparse-checkout", "set", "--no-cone", "--skip-checks", selected], clone_dir)
    run(["checkout", "HEAD", "--", selected], clone_dir)
    path = (clone_dir / selected).resolve()
    if not path.is_relative_to(clone_dir.resolve()):
        raise ValueError("Git source path escaped dataset cache")
    if path.read_bytes()[:100].startswith(b"version https://git-lfs.github.com/spec/v1"):
        run(["-c", "lfs.transfer.maxretries=0", "lfs", "pull", f"--include={selected}", "--exclude="], clone_dir)
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Git cleaned S is not a nonempty JSON sample array")
    source_path = cache_dir / FILENAME
    shutil.copyfile(path, source_path)
    lock = {"dataset": DATASET, "revision": revision, "filename": selected,
            "sha256": file_hash(source_path), "bytes": source_path.stat().st_size,
            "sample_count": len(rows), "variant": "cleaned S", "download_url": repo_url,
            "acquisition_method": "official_dataset_git_sparse_checkout"}
    write_json(cache_dir / "source_lock.json", lock)
    return {**lock, "path": str(source_path)}


def acquire_amendment01(out_dir: Path) -> dict[str, Any]:
    """At most three strategies total, counting the recorded default-HF failure."""
    lock_path = out_dir / "datasets" / "longmemeval_cleaned_s" / "source_lock.json"
    if lock_path.exists():
        return acquire_cleaned_s(out_dir)
    history_path = out_dir / "analysis" / "longmemeval_acquisition_attempts.json"
    prior_path = out_dir / "longmemeval_blocker.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"max_strategies": 3, "attempts": []}
    if not history["attempts"] and prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        history["attempts"].append({"strategy": 1, "method": "default_HF_prior_metadata_attempt",
                                    "status": "failed", "reason": prior.get("reason"),
                                    "evidence": str(prior_path), "no_duplicate_default_retry": True})
        write_json(history_path, history)
    strategies = (
        lambda: acquire_cleaned_s(out_dir, approved_retry=True, datasets_transport=True),
        lambda: acquire_cleaned_s(out_dir, endpoint="https://hf-mirror.com", approved_retry=True, datasets_transport=True),
        lambda: acquire_from_official_git(out_dir),
    )
    names = ("datasets_default_HF", "datasets_HF_mirror", "official_dataset_git")
    for index in range(len(history["attempts"]), 3):
        event = {"strategy": index + 1, "method": names[index], "status": "in_progress",
                 "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        history["attempts"].append(event)
        write_json(history_path, history)
        print(f"LongMemEval acquisition strategy={index + 1}/3 method={names[index]}", flush=True)
        previous_endpoint = os.environ.get("HF_ENDPOINT")
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" if index == 1 else "https://huggingface.co"
        try:
            source = strategies[index]()
            event.update(status="successful", source_sha256=source["sha256"], revision=source["revision"])
            write_json(history_path, history)
            write_json(prior_path, {"status": "resolved", "dataset": DATASET,
                                   "network_attempts_policy": "amendment01: at most 3 strategies including historical first",
                                   "acquisition_history": str(history_path), "llm_calls": 0})
            return source
        except Exception as error:
            event.update(status="failed", reason=f"{type(error).__name__}: {error}")
            write_json(history_path, history)
        finally:
            if previous_endpoint is None:
                os.environ.pop("HF_ENDPOINT", None)
            else:
                os.environ["HF_ENDPOINT"] = previous_endpoint
    raise RuntimeError("All 3 authorized LongMemEval acquisition strategies unavailable; proceed to mandatory stage E")


def adapt_case(row: dict[str, Any], case_id: str) -> dict[str, Any]:
    histories = row.get("haystack_sessions")
    dates = row.get("haystack_dates")
    session_ids = row.get("haystack_session_ids")
    if not isinstance(histories, list) or not isinstance(dates, list) or not isinstance(session_ids, list):
        raise ValueError("Missing LongMemEval history/session/date lists")
    if not (len(histories) == len(dates) == len(session_ids)):
        raise ValueError("LongMemEval history/session/date length mismatch")
    question = str(row.get("question") or "")
    question_date = str(row.get("question_date") or "")
    deployment_question = question + (f"\nQuestion date: {question_date}" if question_date else "")
    texts = [session_text(session) for session in histories]
    top = tfidf_cosine_topk(deployment_question, texts)
    raw = [{"content": texts[i], "event_time": observable_date(dates[i]),
            "source_session": f"s{i + 1:04d}", "relativity": score,
            "metadata": {"session_date": str(dates[i]), "source_session": f"s{i + 1:04d}"}}
           for i, score in top]
    user_name = "LongMemEvalUser"
    context = f"Memories for user {user_name}:\n\n    " + "\n".join(
        f"[session {memory['source_session']} | {memory['event_time']}]\n{memory['content']}" for memory in raw)
    # Everything below is analysis-only; deployment sees the allowlisted view.
    answer_ids = [str(value) for value in (row.get("answer_session_ids") or [])]
    # Source IDs can themselves encode answer-bearing sessions.  The deployment
    # path receives neutral positional IDs; original IDs remain analysis-only.
    selected_ids = [str(session_ids[i]) for i, _ in top]
    matched = set(answer_ids) & set(selected_ids)
    labels = {str(session_ids[i]): [turn_index for turn_index, turn in enumerate(session)
                                  if turn.get("has_answer") is True]
              for i, session in enumerate(histories)}
    gold_turn_texts = [str(turn.get("content") or "") for session in histories
                       for turn in session if turn.get("has_answer") is True and str(turn.get("content") or "").strip()]
    return {
        "case_id": case_id, "dataset": "longmemeval", "system_kind": "longmemeval",
        "user_name": user_name, "question": deployment_question, "original_question": question,
        "question_date": question_date, "raw_memories": raw, "context_str_full": context,
        "pref_note": "", "serializer_ok": True,
        "gold_answer": row.get("answer"), "gold_evidence": gold_turn_texts,
        "question_type": row.get("question_type"), "original_question_id": row.get("question_id"),
        "answer_session_ids": answer_ids, "analysis_answer_turn_indices": labels,
        "analysis_selected_session_ids": selected_ids,
        "gold_memory_ids": [f"m{i}" for i, original_id in enumerate(selected_ids, 1)
                            if original_id in answer_ids],
        "retrieval_stratum": "all_samples_no_baseline_filter",
        "recall_at_20": len(matched) / len(set(answer_ids)) if answer_ids else None,
        "all_answer_sessions_retrieved": set(answer_ids) <= set(selected_ids) if answer_ids else None,
        "baseline_label": "", "baseline_verdict": "",
    }


def build_longmemeval(out_dir: Path = OUT_DIR, source_path: Path | None = None,
                     source_revision: str | None = None, *, amendment01: bool = False) -> list[dict[str, Any]]:
    print("Budget: LLM calls=0; cleaned S file only; TF-IDF top_k=20 once per sample", flush=True)
    try:
        if source_path is None:
            source = acquire_amendment01(out_dir) if amendment01 else acquire_cleaned_s(out_dir)
        else:
            if not source_revision or not re.fullmatch(r"[a-f0-9]{40}", source_revision):
                raise ValueError("A local cleaned S source requires its pinned HF revision")
            source = {"dataset": DATASET, "revision": source_revision, "filename": source_path.name,
                      "path": str(source_path), "sha256": file_hash(source_path), "variant": "cleaned S"}
        rows = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        if not isinstance(rows, list) or not rows:
            raise ValueError("cleaned S sample array is empty")
    except Exception as error:
        blocker = {"status": "blocked", "fallback": "E", "dataset": DATASET,
                   "variant": "cleaned S", "network_attempts_policy": "amendment01: <=3 strategies; historical default counts as first" if amendment01 else "one; no repeat",
                   "reason": f"{type(error).__name__}: {error}", "llm_calls": 0}
        write_json(out_dir / "longmemeval_blocker.json", blocker)
        merge_config(blocker, out_dir)
        print(json.dumps(blocker, ensure_ascii=False, indent=2), flush=True)
        return []
    retrieval_key = stable_hash({"source": source["sha256"], "version": RETRIEVER_VERSION,
                                 "top_k": TOP_K, "seed": SEED})
    cache_path = out_dir / "datasets" / "longmemeval_cleaned_s" / f"retrieval_{retrieval_key}.jsonl"
    if cache_path.exists():
        pool = read_jsonl(cache_path)
        if len(pool) != len(rows):
            raise RuntimeError("Frozen LongMemEval retrieval cache is incomplete")
    else:
        pool = [adapt_case(row, f"longmemeval:{i:04d}") for i, row in enumerate(rows, 1)]
        write_jsonl(cache_path, pool)
    write_jsonl(out_dir / "pools" / "longmemeval_pool.jsonl", pool)
    recall = [row["recall_at_20"] for row in pool if row["recall_at_20"] is not None]
    stats = {"status": "ready", "source": source, "pool_n": len(pool),
             "pool_definition": "all cleaned S samples, including abstention; no correctness filter",
             "retriever": RETRIEVER_VERSION, "retrieval_cache_key": retrieval_key,
             "top_k": TOP_K, "frozen": True, "llm_calls": 0,
             "mean_session_recall_at_20": sum(recall) / len(recall) if recall else None,
             "recall_eligible_samples": len(recall),
             "all_answer_sessions_retrieved": sum(r["all_answer_sessions_retrieved"] is True for r in pool),
             "without_answer_session_annotation": len(pool) - len(recall),
             "question_type_distribution_analysis_only": dict(Counter(r["question_type"] for r in pool)),
             "pool_sha256": file_hash(out_dir / "pools" / "longmemeval_pool.jsonl"),
             "evaluation_warning": "correct abstention is C, not O; knowledge-update allows correct old+new",
             "prior_work_warning": "reading failure was studied in original LongMemEval section 5.5"}
    write_json(out_dir / "pools" / "longmemeval_pool_summary.json", stats)
    merge_config(stats, out_dir)
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)
    return pool


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--amendment01", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    policy = "at most 3 cleaned S strategies including historical first" if args.amendment01 else "one cleaned S network attempt"
    print(f"Budget: LLM calls=0; {policy}; frozen top20 retrieval", flush=True)
    if not args.yes:
        parser.error("Execution requires --yes after the printed budget")
    build_longmemeval(args.out_dir, args.source, args.revision, amendment01=args.amendment01)


if __name__ == "__main__":
    main()
