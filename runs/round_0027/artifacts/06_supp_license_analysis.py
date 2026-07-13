from __future__ import annotations

"""
E1 补充分析:把 license 效应从"全体 598"口径修正为"真正被授权"口径。

动机:A4 对纯 ASSERT 样本不注入任何文本,其 context 与 A0 逐字节相同,
对翻转贡献≈0。因此在全体 598 上算的 A4 flip=9.2% 严重稀释了真实授权效应。
本脚本按 A4 生成记录里已存的 license_counts,把样本分成 licensed / assert-only
两个子集,分别报 flip_rate、转移矩阵、以及 A3-A2 的授权净增益。

零额外 API 调用:只读已有的 generations/ 和 verdicts/。
"""

import csv
import math
from collections import Counter
from typing import Any

from e1_memos_oracle_common import CONDITIONS, OUT_DIR, load_samples, read_jsonl

LICENSE_KINDS = {"REFUTE", "SELECT", "CONDITION"}


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def exact_mcnemar_p(b: int, c: int) -> float | None:
    total = b + c
    if total == 0:
        return None
    try:
        from scipy.stats import binomtest  # type: ignore

        return float(binomtest(min(b, c), total, 0.5).pvalue)
    except Exception:  # noqa: BLE001
        prob = sum(math.comb(total, i) for i in range(0, min(b, c) + 1)) * (0.5**total)
        return min(1.0, 2 * prob)


def load_verdicts() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for condition in CONDITIONS:
        rows = [r for r in read_jsonl(OUT_DIR / "verdicts" / f"{condition}.jsonl") if r.get("ok")]
        out[condition] = {str(r["case_id"]): str(r["judge_label"]) for r in rows}
    return out


def load_a4_license_counts() -> dict[str, Counter]:
    """case_id -> Counter(license_counts) from the A4 generation record."""
    out: dict[str, Counter] = {}
    for r in read_jsonl(OUT_DIR / "generations" / "A4.jsonl"):
        if r.get("ok"):
            out[str(r["case_id"])] = Counter(r.get("license_counts") or {})
    return out


def is_licensed(counts: Counter) -> bool:
    return any(counts.get(k, 0) > 0 for k in LICENSE_KINDS)


def flip_row(pool: str, case_ids: list[str], verdicts: dict[str, dict[str, str]], cond: str) -> dict[str, Any]:
    labels = [verdicts[cond].get(cid) for cid in case_ids]
    labels = [x for x in labels if x]
    correct = sum(1 for x in labels if x == "correct")
    lo, hi = wilson(correct, len(labels))
    return {
        "pool": pool, "condition": cond, "n": len(labels), "correct": correct,
        "flip_rate": correct / len(labels) if labels else 0.0,
        "wilson_low": lo, "wilson_high": hi,
    }


def mcnemar_row(pool: str, case_ids: list[str], verdicts: dict[str, dict[str, str]], left: str, right: str) -> dict[str, Any]:
    b = c = both = 0
    for cid in case_ids:
        l, r = verdicts[left].get(cid), verdicts[right].get(cid)
        if not l or not r:
            continue
        both += 1
        if l == "correct" and r != "correct":
            b += 1
        elif r == "correct" and l != "correct":
            c += 1
    return {"pool": pool, "comparison": f"{left}_vs_{right}", "n": both, "b": b, "c": c, "p_value": exact_mcnemar_p(b, c)}


def transitions(pool: str, case_ids: list[str], verdicts: dict[str, dict[str, str]], cond: str) -> list[dict[str, Any]]:
    counts: Counter = Counter()
    for cid in case_ids:
        a0, x = verdicts["A0"].get(cid), verdicts[cond].get(cid)
        if a0 and x:
            counts[(a0, x)] += 1
    tot: Counter = Counter()
    for (src, _), n in counts.items():
        tot[src] += n
    rows = []
    for src in ["hallucination", "omission", "correct"]:
        for dst in ["correct", "hallucination", "omission"]:
            n = counts[(src, dst)]
            rows.append({"pool": pool, "condition": cond, "from_label": src, "to_label": dst,
                         "count": n, "rate_within_from": n / tot[src] if tot[src] else 0.0})
    return rows


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main() -> None:
    samples = load_samples()
    by_case = {str(r["case_id"]): r for r in samples}
    verdicts = load_verdicts()
    a4_counts = load_a4_license_counts()

    stable_wrong = [cid for cid in by_case if verdicts["A0"].get(cid) and verdicts["A0"][cid] != "correct"]
    strict = [cid for cid in stable_wrong if by_case[cid].get("retrieval_stratum") == "strict_supported"]

    licensed = [cid for cid in strict if is_licensed(a4_counts.get(cid, Counter()))]
    assert_only = [cid for cid in strict if not is_licensed(a4_counts.get(cid, Counter()))]

    # 授权类型分布(licensed 子集里各种 license 各多少条)
    kind_dist: Counter = Counter()
    for cid in licensed:
        for k in LICENSE_KINDS:
            if a4_counts.get(cid, Counter()).get(k, 0) > 0:
                kind_dist[k] += 1

    print("=" * 60)
    print(f"strict stable-wrong total : {len(strict)}")
    print(f"  licensed (REFUTE/SELECT/CONDITION any) : {len(licensed)}")
    print(f"  assert-only                            : {len(assert_only)}")
    print(f"  license kind distribution (may overlap): {dict(kind_dist)}")
    print("=" * 60)

    flip_rows = []
    for pool_name, ids in [("strict_all", strict), ("strict_licensed", licensed), ("strict_assert_only", assert_only)]:
        for cond in ["A0", "A1", "A2", "A3", "A4"]:
            flip_rows.append(flip_row(pool_name, ids, verdicts, cond))
    write_csv(OUT_DIR / "supp_flip_by_license.csv", flip_rows,
              ["pool", "condition", "n", "correct", "flip_rate", "wilson_low", "wilson_high"])

    # A4 vs A0 (纯授权效应) 和 A3 vs A2 (授权在过滤之上的净增益),都只在 licensed 上
    mc_rows = [
        mcnemar_row("strict_licensed", licensed, verdicts, "A4", "A0"),
        mcnemar_row("strict_licensed", licensed, verdicts, "A3", "A2"),
        mcnemar_row("strict_assert_only", assert_only, verdicts, "A4", "A0"),  # 应当 b=c=0 附近,做健全性检查
    ]
    write_csv(OUT_DIR / "supp_mcnemar_by_license.csv", mc_rows,
              ["pool", "comparison", "n", "b", "c", "p_value"])

    trans_rows = []
    for cond in ["A2", "A3", "A4"]:
        trans_rows += transitions("strict_licensed", licensed, verdicts, cond)
    write_csv(OUT_DIR / "supp_transitions_licensed.csv", trans_rows,
              ["pool", "condition", "from_label", "to_label", "count", "rate_within_from"])

    print("\n--- flip rates ---")
    for r in flip_rows:
        print(f"{r['pool']:20s} {r['condition']} n={r['n']:4d} flip={r['flip_rate']:.2%} "
              f"CI[{r['wilson_low']:.2%},{r['wilson_high']:.2%}]")
    print("\n--- mcnemar ---")
    for r in mc_rows:
        print(f"{r['pool']:20s} {r['comparison']:10s} n={r['n']:4d} b={r['b']} c={r['c']} p={r['p_value']}")
    print("\n[assert_only 的 A4_vs_A0 若 b,c 均≈0 => 证明 ASSERT 确为 no-op;若不为0 => temp=0 仍有非确定性,是 replay 噪声来源]")

    # 健全性:assert_only 子集上 A4 与 A0 判定是否一致
    flips = sum(1 for cid in assert_only if verdicts["A4"].get(cid) != verdicts["A0"].get(cid))
    print(f"\nassert_only 子集中 A4 判定 != A0 判定 的样本数: {flips}/{len(assert_only)} "
          f"(理想=0;>0 即为纯噪声/非确定性)")


if __name__ == "__main__":
    main()
