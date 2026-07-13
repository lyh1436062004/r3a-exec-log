from __future__ import annotations

"""
00_verify_serializer.py — E1' 的前置门禁(纯离线,零 API 调用)。

做三件事:
1. 逐字节验证:用复刻的 baseline 序列化器(baseline_memory_text + serialize_baseline_context)
   对每条样本重建 context,必须与存档的 context_str_full 完全一致
   (允许的唯一余量:末尾的 pref_note 行,恢复后仍须逐字节吻合)。
   任何一条不吻合都会列出 diff,此时禁止进入生成阶段。
2. 计算可见性分层:strict_supported 样本中 gold 记忆是否真的进了 LLM 上下文,
   得到 visible_supported(预期 763)与 serialization_loss(预期 133)。
3. 写出 visibility.jsonl,供 load_samples 合并、干预臂构造与分析使用。

用法:
    python 01_select_memos_full.py    # 先在 v2 目录重建样本池
    python 00_verify_serializer.py    # 本脚本;必须全绿才能跑 02
"""

import json
from collections import Counter
from typing import Any

from e1_memos_oracle_common import (
    OUT_DIR,
    baseline_memory_text,
    read_jsonl,
    serialize_baseline_context,
)

EXPECTED_VISIBLE_SUPPORTED = 763
EXPECTED_SERIALIZATION_LOSS = 133


def first_diff(a: str, b: str) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def main() -> None:
    samples = read_jsonl(OUT_DIR / "samples_memos_full.jsonl")
    if not samples:
        raise RuntimeError(f"no samples at {OUT_DIR}/samples_memos_full.jsonl; run 01_select first")

    out_rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    stratum_counter: Counter[str] = Counter()
    note_count = 0

    for sample in samples:
        case_id = str(sample["case_id"])
        raw_memories = list(sample.get("raw_memories") or [])
        stored = str(sample.get("context_str_full") or "")
        user_name = str(sample.get("user_name") or "")

        visible_ids: list[str] = []
        lines: list[str] = []
        for idx, item in enumerate(raw_memories, 1):
            text = baseline_memory_text(item)
            if text:
                visible_ids.append(f"m{idx}")
                lines.append(text)

        rebuilt = serialize_baseline_context(user_name, lines)

        serializer_ok = False
        pref_note = ""
        if stored == rebuilt:
            serializer_ok = True
        elif stored.startswith(rebuilt + "\n"):
            # baseline 在记忆行之后追加了 pref_note(作为最后一行/块)
            pref_note = stored[len(rebuilt) + 1 :]
            # 恢复后必须能逐字节还原
            if serialize_baseline_context(user_name, lines + [pref_note]) == stored:
                serializer_ok = True
                note_count += 1

        if not serializer_ok:
            pos = first_diff(stored, rebuilt)
            mismatches.append(
                {
                    "case_id": case_id,
                    "first_diff_at": pos,
                    "stored_len": len(stored),
                    "rebuilt_len": len(rebuilt),
                    "stored_around_diff": stored[max(0, pos - 80) : pos + 80],
                    "rebuilt_around_diff": rebuilt[max(0, pos - 80) : pos + 80],
                }
            )

        visible_set = set(visible_ids)
        gold_visible = [m for m in sample.get("gold_memory_ids") or [] if m in visible_set]
        partial_visible = [m for m in sample.get("partial_memory_ids") or [] if m in visible_set]

        base_stratum = str(sample.get("retrieval_stratum") or "")
        if base_stratum == "strict_supported":
            visible_stratum = "visible_supported" if gold_visible else "serialization_loss"
        else:
            visible_stratum = base_stratum
        stratum_counter[visible_stratum] += 1

        out_rows.append(
            {
                "case_id": case_id,
                "serializer_ok": serializer_ok,
                "visible_memory_ids": visible_ids,
                "n_raw": len(raw_memories),
                "n_visible": len(visible_ids),
                "gold_visible_ids": gold_visible,
                "partial_visible_ids": partial_visible,
                "pref_note": pref_note,
                "visible_stratum": visible_stratum,
            }
        )

    with (OUT_DIR / "visibility.jsonl").open("w", encoding="utf-8") as f:
        for row in out_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    ok = sum(1 for r in out_rows if r["serializer_ok"])
    print("=" * 64)
    print(f"samples                : {len(out_rows)}")
    print(f"serializer byte-exact  : {ok}/{len(out_rows)}")
    print(f"with pref_note         : {note_count}")
    print(f"stratum counts         : {dict(stratum_counter)}")
    print(f"  expected visible_supported={EXPECTED_VISIBLE_SUPPORTED}, "
          f"serialization_loss={EXPECTED_SERIALIZATION_LOSS}")
    print("=" * 64)

    if mismatches:
        dump = OUT_DIR / "serializer_mismatches.jsonl"
        with dump.open("w", encoding="utf-8") as f:
            for row in mismatches:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"\n[FAIL] {len(mismatches)} 条样本重建不吻合,样例:")
        for row in mismatches[:3]:
            print(f"  case={row['case_id']} diff@{row['first_diff_at']}")
            print(f"    stored : ...{row['stored_around_diff']!r}...")
            print(f"    rebuilt: ...{row['rebuilt_around_diff']!r}...")
        raise SystemExit(
            "serializer 复刻未通过,禁止进入 02_generate;"
            f" 详见 {dump}"
        )

    got_vis = stratum_counter.get("visible_supported", 0)
    got_loss = stratum_counter.get("serialization_loss", 0)
    if (got_vis, got_loss) != (EXPECTED_VISIBLE_SUPPORTED, EXPECTED_SERIALIZATION_LOSS):
        print(
            f"\n[WARN] 分层计数与你手工核查的 763/133 不一致: "
            f"visible_supported={got_vis}, serialization_loss={got_loss}。"
            "\n先核对口径(支撑判定缓存版本、visible 判定规则)再继续。"
        )
    else:
        print("\n[OK] 全部通过,可以进入 02_generate(先 A0,验证复现率,再跑干预臂)。")


if __name__ == "__main__":
    main()
